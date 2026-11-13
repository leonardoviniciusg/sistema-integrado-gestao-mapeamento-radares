from pathlib import Path
import os
import secrets
import socket
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or secrets.token_urlsafe(50)
DEBUG = False
_local_hosts = {'localhost', '127.0.0.1', socket.gethostname()}
_local_hosts.update(socket.gethostbyname_ex(socket.gethostname())[2])
ALLOWED_HOSTS = list(_local_hosts) + [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]
ROOT_URLCONF = 'dashboard_v1.urls'
WSGI_APPLICATION = 'dashboard_v1.wsgi.application'
INSTALLED_APPS = []
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'dashboard_v1' / 'templates'],
    'APP_DIRS': False,
    'OPTIONS': {'context_processors': ['django.template.context_processors.csrf']},
}]
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_TZ = True
