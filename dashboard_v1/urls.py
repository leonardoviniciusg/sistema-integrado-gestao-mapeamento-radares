from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('api/dados', views.get_dados),
    path('api/executar', views.run_main),
    path('api/limpar-cache', views.limpar_cache),
    path('api/logs/stream', views.stream_logs),
    path('api/relatorio/<str:tipo>', views.exportar_relatorio),
]
