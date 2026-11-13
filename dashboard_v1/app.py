"""Inicia o painel Django na rede local com um único processo Waitress."""
import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dashboard_v1.wsgi import application

if __name__ == '__main__':
    from waitress import serve
    port = int(os.getenv('PORT', '5000'))
    print(f'Painel local: http://localhost:{port}', flush=True)
    for ip in sorted(set(socket.gethostbyname_ex(socket.gethostname())[2])):
        print(f'Acesso pela rede: http://{ip}:{port}', flush=True)
    serve(application, host=os.getenv('HOST', '0.0.0.0'), port=port,
          threads=int(os.getenv('SERVER_THREADS', '32')))
