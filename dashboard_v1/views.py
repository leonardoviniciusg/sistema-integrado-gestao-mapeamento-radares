import os
import sys
import subprocess
import threading
import queue
import shutil
import pandas as pd
from datetime import datetime, timedelta
import json
from io import BytesIO
from django.http import JsonResponse, StreamingHttpResponse, FileResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie

def jsonify(data, status=200):
    return JsonResponse(data, status=status)

def send_file(path, as_attachment=True, download_name=None):
    return FileResponse(open(path, 'rb'), as_attachment=as_attachment, filename=download_name)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)


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
    proc.wait()
    with process_lock:
        is_running = False
        ultimo_status_msg = "Base atualizada com sucesso."
    for q in list(log_subscribers):
        q.put("[PROCESSO FINALIZADO]\n")

@ensure_csrf_cookie
@require_GET
def index(request):
    return render(request, 'index.html')

@require_GET
def get_dados(request):
    if not os.path.exists(EXCEL_PATH):
        return jsonify({'erro': 'Arquivo Excel não encontrado'}, status=404)

    try:
        df_ctrl = pd.read_excel(EXCEL_PATH, sheet_name='Controle')
        df_inst = pd.read_excel(EXCEL_PATH, sheet_name='Instrumentos')
        controle_dict = dict(zip(df_ctrl['Parametro'], df_ctrl['Valor']))

        dates_verif = pd.to_datetime(df_inst['DataUltimaVerificacao'], format='%d/%m/%Y', errors='coerce')
        anos_disponiveis = sorted([int(a) for a in dates_verif.dt.year.dropna().unique()], reverse=True)

        # Totais da Base Geral (Fixos)
        hoje = datetime.now()
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
            if pd.notna(lat) and pd.notna(lng):
                dt_v = dates_verif.iloc[idx]
                ano_v = int(dt_v.year) if pd.notna(dt_v) else None
                radares.append({
                    'serie': str(row.get('NumeroSerie', '')),
                    'empresa': str(row.get('Proprietario.Nome', 'NÃO INFORMADO')),
                    'municipio': str(row.get('Municipio', '')),
                    'local': str(row.get('LocalVerificacao', '')),
                    'tipo_local': str(row.get('tipo_local', 'N/A')),
                    'faixas': int(row.get('Faixas', 1)),
                    'resultado': str(row.get('UltimoResultado', 'Indefinido')),
                    'ultima_verificacao': str(row.get('DataUltimaVerificacao', 'N/A')),
                    'ano_verificacao': ano_v,
                    'validade': str(row.get('DataValidade', 'N/A')),
                    'metodo': str(row.get('metodo_geocodificacao', 'N/A')),
                    'lat': float(lat),
                    'lng': float(lng)
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
        return jsonify({'erro': str(e)}, status=500)

@require_POST
def run_main(request):
    global is_running, ultimo_status_msg
    with process_lock:
        if is_running:
            return jsonify({'status': 'busy', 'mensagem': 'Pipeline já em execução.'}, status=400)
        
        main_path = os.path.join(BASE_DIR, 'main.py')
        if not os.path.exists(main_path):
            return jsonify({'status': 'erro', 'mensagem': 'main.py não encontrado.'}, status=404)

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

@require_POST
def limpar_cache(request):
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
        return jsonify({'status': 'erro', 'mensagem': str(e)}, status=500)

@require_GET
def stream_logs(request):
    q = queue.Queue()
    log_subscribers.append(q)

    def event_stream():
        try:
            while True:
                try:
                    line = q.get(timeout=15)
                except queue.Empty:
                    yield ': keepalive\n\n'
                    continue
                yield f"data: {line}\n\n"
        finally:
            log_subscribers.remove(q)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response

@require_http_methods(['GET', 'POST'])
def exportar_relatorio(request, tipo):
    if not os.path.exists(EXCEL_PATH):
        return jsonify({'erro': 'Base não encontrada'}, status=404)

    # Se for exportação dos dados filtrados da tabela atual enviados via POST
    if tipo == 'tabela_filtrada' and request.method == 'POST':
        try:
            payload = json.loads(request.body)
            itens = payload.get('itens', [])
            if not isinstance(itens, list):
                raise ValueError('itens deve ser uma lista')
        except (ValueError, AttributeError):
            return jsonify({'erro': 'JSON inválido'}, status=400)
        df_export = pd.DataFrame(itens)
        nome = f"radares_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return export_csv(df_export, nome)

    df_inst = pd.read_excel(EXCEL_PATH, sheet_name='Instrumentos')
    hoje = datetime.now()
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

    return export_csv(df_export, nome)



def export_csv(dataframe, filename):
    content = dataframe.to_csv(index=False, sep=';').encode('utf-8-sig')
    return FileResponse(BytesIO(content), as_attachment=True, filename=filename,
                        content_type='text/csv; charset=utf-8')
