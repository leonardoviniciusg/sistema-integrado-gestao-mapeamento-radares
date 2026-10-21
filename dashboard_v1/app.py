import os
import sys
import subprocess
import threading
import queue
import shutil
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, Response, send_file, request

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

app = Flask(__name__, template_folder='templates')
EXCEL_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'medidores_processados.xlsx')

process_lock = threading.Lock()
is_running = False
ultimo_status_msg = "Pronto para operação"
log_subscribers = []

def stream_process_output(proc):
    global is_running, ultimo_status_msg
    for line in iter(proc.stdout.readline, ''):
        if line:
            ultimo_status_msg = line.strip()
            for q in list(log_subscribers):
                q.put(line)
    proc.stdout.close()
    returncode = proc.wait()
    with process_lock:
        is_running = False
        ultimo_status_msg = (
            "Base atualizada com sucesso." if returncode == 0
            else f"Falha na atualização da base (código {returncode}). Consulte os logs."
        )
    for q in list(log_subscribers):
        q.put(ultimo_status_msg + "\n")
        q.put("[PROCESSO FINALIZADO]\n" if returncode == 0 else "[PROCESSO FALHOU]\n")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dados')
def get_dados():
    if not os.path.exists(EXCEL_PATH):
        return jsonify({'erro': 'Arquivo Excel não encontrado'}), 404

    try:
        df_ctrl = pd.read_excel(EXCEL_PATH, sheet_name='Controle')
        df_inst = pd.read_excel(EXCEL_PATH, sheet_name='Instrumentos')
        controle_dict = dict(zip(df_ctrl['Parametro'], df_ctrl['Valor']))

        dates_verif = pd.to_datetime(df_inst['DataUltimaVerificacao'], format='%d/%m/%Y', errors='coerce')
        anos_disponiveis = sorted([int(a) for a in dates_verif.dt.year.dropna().unique()], reverse=True)

        # Totais da Base Geral (Fixos)
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        dates_val = pd.to_datetime(df_inst['DataValidade'], format='%d/%m/%Y', errors='coerce')
        total_base = int(len(df_inst))
        vencidos_base = int((dates_val < hoje).sum())
        vencer_base = int(((dates_val >= hoje) & (dates_val <= hoje + timedelta(days=90))).sum())
        vigentes_base = int((dates_val > hoje + timedelta(days=90)).sum())
        faixas_base = int(df_inst['Faixas'].sum()) if 'Faixas' in df_inst.columns else total_base

        kpis_base = {
            'total': total_base,
            'vencidos': vencidos_base,
            'a_vencer': vencer_base,
            'vigentes': vigentes_base,
            'faixas': faixas_base
        }

        # Listas para seletores de filtros
        empresas = df_inst['Proprietario.Nome'].fillna('NÃO INFORMADO').value_counts().to_dict()
        municipios = sorted([str(m) for m in df_inst['Municipio'].dropna().unique()])
        tipos_local = sorted([str(t) for t in df_inst['tipo_local'].dropna().unique()])
        resultados = sorted([str(r) for r in df_inst['UltimoResultado'].dropna().unique()])
        metodos = sorted([str(m) for m in df_inst['metodo_geocodificacao'].dropna().unique()])

        # Itens estruturados para o frontend
        radares = []
        for idx, row in df_inst.iterrows():
            lat, lng = row.get('latitude'), row.get('longitude')
            tem_coordenadas = pd.notna(lat) and pd.notna(lng)
            dt_v = dates_verif.iloc[idx]
            ano_v = int(dt_v.year) if pd.notna(dt_v) else None
            radares.append({
                'serie': str(row.get('NumeroSerie', '')),
                'empresa': str(row.get('Proprietario.Nome', 'NÃO INFORMADO')),
                'municipio': str(row.get('Municipio', '')),
                'local': str(row.get('LocalVerificacao', '')),
                'tipo_local': str(row.get('tipo_local', 'N/A')),
                'faixas': int(row['Faixas']) if pd.notna(row.get('Faixas')) else 0,
                'resultado': str(row.get('UltimoResultado', 'Indefinido')),
                'ultima_verificacao': str(row.get('DataUltimaVerificacao', 'N/A')),
                'ano_verificacao': ano_v,
                'validade': str(row.get('DataValidade', 'N/A')),
                'metodo': str(row.get('metodo_geocodificacao', 'N/A')),
                'lat': float(lat) if tem_coordenadas else None,
                'lng': float(lng) if tem_coordenadas else None
            })

        return jsonify({
            'controle': controle_dict,
            'kpis_base': kpis_base,
            'empresas': empresas,
            'municipios': municipios,
            'tipos_local': tipos_local,
            'resultados': resultados,
            'metodos': metodos,
            'anos': anos_disponiveis,
            'radares': radares,
            'is_running': is_running,
            'ultimo_status': ultimo_status_msg
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/executar', methods=['POST'])
def run_main():
    global is_running, ultimo_status_msg
    with process_lock:
        if is_running:
            return jsonify({'status': 'busy', 'mensagem': 'Pipeline já em execução.'}), 400
        
        main_path = os.path.join(BASE_DIR, 'main.py')
        if not os.path.exists(main_path):
            return jsonify({'status': 'erro', 'mensagem': 'main.py não encontrado.'}), 404

        proc = subprocess.Popen(
            [sys.executable, '-u', main_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
            text=True,
            bufsize=1
        )
        is_running = True
        ultimo_status_msg = "Atualizando base (main.py)..."
        t = threading.Thread(target=stream_process_output, args=(proc,))
        t.daemon = True
        t.start()

    return jsonify({'status': 'iniciado', 'mensagem': 'Execução de atualização iniciada.'})

@app.route('/api/limpar-cache', methods=['POST'])
def limpar_cache():
    global ultimo_status_msg
    try:
        pastas_cache = ['__pycache__', '.cache']
        removidos = 0
        for root, dirs, files in os.walk(BASE_DIR):
            for d in list(dirs):
                if d in pastas_cache:
                    shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                    removidos += 1
        ultimo_status_msg = f"Cache limpo ({removidos} diretórios removidos)."
        return jsonify({'status': 'sucesso', 'mensagem': ultimo_status_msg})
    except Exception as e:
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

@app.route('/api/logs/stream')
def stream_logs():
    q = queue.Queue()
    log_subscribers.append(q)

    def event_stream():
        try:
            while True:
                line = q.get()
                yield f"data: {line}\n\n"
        except GeneratorExit:
            log_subscribers.remove(q)

    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/api/relatorio/<tipo>', methods=['GET', 'POST'])
def exportar_relatorio(tipo):
    if not os.path.exists(EXCEL_PATH):
        return jsonify({'erro': 'Base não encontrada'}), 404

    # Se for exportação dos dados filtrados da tabela atual enviados via POST
    if tipo == 'tabela_filtrada' and request.method == 'POST':
        itens = request.json.get('itens', [])
        df_export = pd.DataFrame(itens)
        nome = f"radares_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        caminho = os.path.join(os.path.dirname(__file__), nome)
        df_export.to_csv(caminho, index=False, sep=';', encoding='utf-8-sig')
        return send_file(caminho, as_attachment=True, download_name=nome)

    df_inst = pd.read_excel(EXCEL_PATH, sheet_name='Instrumentos')
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    dates = pd.to_datetime(df_inst['DataValidade'], format='%d/%m/%Y', errors='coerce')

    if tipo == 'vencidos':
        df_export = df_inst[dates < hoje]
        nome = 'laudos_vencidos.csv'
    elif tipo == 'a_vencer':
        df_export = df_inst[(dates >= hoje) & (dates <= hoje + timedelta(days=90))]
        nome = 'laudos_a_vencer_90d.csv'
    elif tipo == 'completo':
        return send_file(EXCEL_PATH, as_attachment=True, download_name='medidores_processados.xlsx')
    else:
        df_export = df_inst
        nome = 'relatorio_geral_radares.csv'

    caminho_temp = os.path.join(os.path.dirname(__file__), nome)
    df_export.to_csv(caminho_temp, index=False, sep=';', encoding='utf-8-sig')
    return send_file(caminho_temp, as_attachment=True, download_name=nome)

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
