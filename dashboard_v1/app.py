import os
import sys
import subprocess
import threading
import queue
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, Response, send_file

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

app = Flask(__name__, template_folder='templates')
EXCEL_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'medidores_processados.xlsx')

process_lock = threading.Lock()
is_running = False
log_subscribers = []

def stream_process_output(proc):
    global is_running
    for line in iter(proc.stdout.readline, ''):
        if line:
            for q in list(log_subscribers):
                q.put(line)
    proc.stdout.close()
    proc.wait()
    with process_lock:
        is_running = False
    for q in list(log_subscribers):
        q.put("[PROCESSO FINALIZADO]\n")

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

        # Totais gerais
        total_instrumentos = int(len(df_inst))
        aprovados = int((df_inst['UltimoResultado'] == 'Aprovado').sum())
        outros = total_instrumentos - aprovados

        # Métodos de identificação
        metodos = df_inst['metodo_geocodificacao'].value_counts().to_dict()

        # Distribuição de Faixas por Equipamento
        faixas_dist = df_inst['Faixas'].value_counts().sort_index().to_dict()
        faixas_dict = {f"{int(k)} Faixa{'s' if k > 1 else ''}": int(v) for k, v in faixas_dist.items()}

        # Análise de Validade Metrológica
        hoje = datetime.now()
        dates_val = pd.to_datetime(df_inst['DataValidade'], format='%d/%m/%Y', errors='coerce')
        
        vencidos = int((dates_val < hoje).sum())
        vencer_30d = int(((dates_val >= hoje) & (dates_val <= hoje + timedelta(days=30))).sum())
        vencer_90d = int(((dates_val > hoje + timedelta(days=30)) & (dates_val <= hoje + timedelta(days=90))).sum())
        vigentes = int((dates_val > hoje + timedelta(days=90)).sum())
        sem_data = int(df_inst['DataValidade'].isna().sum())

        validades = {
            'Vencidos': vencidos,
            'A Vencer (30d)': vencer_30d,
            'A Vencer (90d)': vencer_90d,
            'Vigentes (>90d)': vigentes,
            'Sem Data': sem_data
        }

        # Empresas
        empresas = df_inst['Proprietario.Nome'].fillna('NÃO INFORMADO').value_counts().to_dict()

        # Extração de Anos de Última Verificação
        dates_verif = pd.to_datetime(df_inst['DataUltimaVerificacao'], format='%d/%m/%Y', errors='coerce')
        anos_disponiveis = sorted([int(a) for a in dates_verif.dt.year.dropna().unique()], reverse=True)

        # Radares georreferenciados
        radares = []
        for idx, row in df_inst.iterrows():
            lat, lng = row.get('latitude'), row.get('longitude')
            if pd.notna(lat) and pd.notna(lng):
                dt_v = dates_verif.iloc[idx]
                ano_v = int(dt_v.year) if pd.notna(dt_v) else None
                radares.append({
                    'nome': f"{row.get('Municipio', '')} - {row.get('LocalVerificacao', '')}",
                    'serie': str(row.get('NumeroSerie', '')),
                    'empresa': str(row.get('Proprietario.Nome', 'NÃO INFORMADO')),
                    'faixas': int(row.get('Faixas', 1)),
                    'validade': str(row.get('DataValidade', 'N/A')),
                    'ultima_verificacao': str(row.get('DataUltimaVerificacao', 'N/A')),
                    'ano_verificacao': ano_v,
                    'metodo': str(row.get('metodo_geocodificacao', 'N/A')),
                    'status': str(row.get('UltimoResultado', 'Indefinido')),
                    'lat': float(lat),
                    'lng': float(lng)
                })

        return jsonify({
            'controle': controle_dict,
            'total': total_instrumentos,
            'operando': aprovados,
            'manutencao': outros,
            'validades': validades,
            'faixas': faixas_dict,
            'metodos': metodos,
            'empresas': empresas,
            'anos': anos_disponiveis,
            'radares': radares,
            'is_running': is_running
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/executar', methods=['POST'])
def run_main():
    global is_running
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
        t = threading.Thread(target=stream_process_output, args=(proc,))
        t.daemon = True
        t.start()

    return jsonify({'status': 'iniciado', 'mensagem': 'Execução do main.py iniciada.'})

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

@app.route('/api/relatorio/<tipo>')
def baixar_relatorio(tipo):
    if not os.path.exists(EXCEL_PATH):
        return jsonify({'erro': 'Base não encontrada'}), 404

    df_inst = pd.read_excel(EXCEL_PATH, sheet_name='Instrumentos')
    hoje = datetime.now()
    dates = pd.to_datetime(df_inst['DataValidade'], format='%d/%m/%Y', errors='coerce')

    if tipo == 'vencidos':
        df_export = df_inst[dates < hoje]
        nome = 'relatorio_radares_vencidos.csv'
    elif tipo == 'a_vencer':
        df_export = df_inst[(dates >= hoje) & (dates <= hoje + timedelta(days=90))]
        nome = 'relatorio_radares_a_vencer_90d.csv'
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