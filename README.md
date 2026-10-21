# Sistema Integrado de Gestão e Mapeamento de Radares

Sistema em Python para extrair dados do PSIE/RBMLQ (Inmetro), padronizar endereços, geocodificar medidores de velocidade e acompanhar instrumentos e validade de laudos em um painel operacional local.

O recorte territorial é definido em `config.py`: municípios do Vale do Paraíba, Litoral Norte e municípios próximos de São Paulo.

## Funcionalidades atuais

- Extração da base de medidores da RBMLQ, com instrumentos, faixas monitoradas e histórico de verificações.
- Padronização de endereços urbanos, cruzamentos, rodovias e marcos quilométricos.
- Atualização incremental por número de série: preserva campos tratados da planilha anterior e invalida coordenadas quando o endereço padronizado muda.
- Geocodificação com bases DER-SP, DNIT e ANTT, espacialização VGEO/SGPLAN e Google Maps.
- Reaproveitamento de coordenadas em caches CSV e validação por distância ao centro municipal. Essa validação é uma aproximação por raio, não uma conferência contra o polígono do município.
- Alinhamento de coordenadas urbanas elegíveis ao eixo da via, via OSRM e fallback Google Roads, com limite de deslocamento de 40 metros.
- Planilha Excel formatada com abas `Controle`, `Instrumentos`, `Faixas` e `Historico`.
- Cópia opcional da planilha para uma pasta local sincronizada pelo OneDrive.
- Dashboard Flask com mapa Leaflet, tabela, filtros combinados, indicadores, relatórios e atualização da base com logs em tempo real.

## Estrutura

```text
.
├── main.py                       # Orquestra extração, tratamento e geocodificação
├── config.py                     # Diretórios, fonte e municípios-alvo
├── requirements.txt              # Dependências Python
├── .env.example                  # Modelo de configuração
├── services/
│   ├── rbmlq_service.py          # Extração, estruturação e exportação Excel
│   ├── address_service.py        # Padronização de endereços
│   ├── highway_service.py        # Bases rodoviárias e consulta VGEO
│   ├── geocode_service.py        # Geocodificação, validação e cache
│   ├── snapping_service.py       # Ajuste ao eixo da via
│   └── vgeo_service.py           # Serviço auxiliar de consulta VGEO
├── dashboard_v1/
│   ├── app.py                    # Servidor Flask e APIs
│   └── templates/index.html      # Interface do painel
├── tests/                        # Testes de regressão
└── data/
    ├── raw/                      # Dados brutos e bases rodoviárias
    ├── geocoded/                 # Caches de coordenadas e snapping
    └── processed/                # Planilha consolidada e análises locais
```

## Instalação e configuração

Use Python 3.10 ou superior, com versão compatível com as dependências fixadas em `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Preencha o `.env` na raiz:

```dotenv
GOOGLE_MAPS_API_KEY=sua_chave_aqui
# Opcional: caminho da pasta local sincronizada pelo OneDrive.
ONEDRIVE_DIR=
```

A chave Google Maps é exigida pelo fluxo atual de `main.py`. O alinhamento pode usar Google Roads quando o OSRM não retorna um ponto. As APIs Google devem estar habilitadas conforme o uso e podem gerar custos; os caches reduzem consultas repetidas.

Para habilitar a cópia no OneDrive, defina `ONEDRIVE_DIR` com o caminho completo da pasta de destino. Deixe vazio para salvar somente a planilha local. O programa grava nessa pasta; a sincronização com a nuvem depende do cliente OneDrive. Uma falha nessa cópia gera um aviso e preserva o resultado local.

## Executar o processamento

Na raiz do projeto, com o ambiente virtual ativado:

```powershell
python main.py
```

O fluxo baixa a base PSIE, seleciona os municípios configurados, recupera campos tratados da planilha anterior, padroniza endereços, atualiza coordenadas e grava `data/processed/medidores_processados.xlsx`.

A extração e as consultas de geocodificação dependem de acesso à internet. Os caches e a planilha são arquivos locais persistentes.

## Executar o dashboard

```powershell
python dashboard_v1/app.py
```

Abra [o painel local](http://127.0.0.1:5000). Gere a planilha com `python main.py` antes do primeiro uso. O painel lê as abas `Controle` e `Instrumentos`; não usa banco de dados separado.

### Consultas e indicadores

- Indicadores gerais: instrumentos, faixas, laudos vencidos, a vencer em 90 dias e vigentes além desse prazo.
- Indicadores da seleção: os mesmos totais recalculados pelos filtros.
- Busca por série, endereço, município ou empresa.
- Filtros por proprietário, município, ano mínimo da última verificação, validade, resultado, tipo de local e método de geocodificação.
- Mapa com cores por empresa, detalhes do instrumento e acesso ao Google Street View.
- Tabela com todos os registros da seleção, inclusive os que não possuem coordenadas. Esses registros aparecem como “Sem coordenadas” e não geram marcadores ou links de Street View.
- Contagem separada de pontos plotados e registros sem coordenadas.

As datas de validade são comparadas por dia: um laudo com vencimento hoje entra em “a vencer”. O limite de 90 dias é inclusivo. Registros sem data válida entram no total, mas não nos três indicadores de validade. Datas e horários seguem o relógio local do computador que executa o servidor.

### Atualização, logs e exportação

O botão **Atualizar Base** executa `main.py` com o mesmo interpretador Python do painel. O servidor impede uma segunda atualização simultânea nessa instância e transmite a saída por Server-Sent Events. A conclusão distingue sucesso de falha pelo código de saída do processo.

Relatórios disponíveis:

- CSV dos laudos vencidos.
- CSV dos laudos a vencer em até 90 dias.
- Download do Excel completo.
- CSV da tabela filtrada, incluindo instrumentos sem coordenadas.

Os CSVs usam separador `;` e UTF-8 com BOM para facilitar a abertura no Excel. São gravados em `dashboard_v1/`. O botão de limpeza de cache remove diretórios `__pycache__` e `.cache`; os caches geográficos CSV em `data/geocoded/` permanecem disponíveis.

O servidor fornecido executa em modo de desenvolvimento (`debug=True`), no endereço local e porta 5000. Não há autenticação implementada. Uma implantação compartilhada exige configuração própria de servidor e controle de acesso.

## Métodos e limites da geocodificação

A coluna `metodo_geocodificacao` registra a origem das coordenadas:

| Método | Origem |
| --- | --- |
| `DER_SP_SERIE` | Correspondência por número de série na base DER-SP |
| `DER_SP_RODOVIA_KM` | Correspondência por rodovia e quilômetro no DER-SP |
| `DNIT_RODOVIA_KM` | Base de radares do DNIT |
| `ANTT_RODOVIA_KM` | Base de concessões da ANTT |
| `DNIT_VGEO_OFICIAL` | Espacialização no eixo rodoviário pelo VGEO/SGPLAN |
| `DER_SP_PROJETO` | Referências de projeto rodoviário presentes no código |
| `GOOGLE_ROOFTOP` | Coordenada de imóvel retornada pelo Google |
| `GOOGLE_INTERPOLATED` | Coordenada interpolada pelo Google |
| `GOOGLE_INTERSECTION` | Resultado de cruzamento |
| `GOOGLE_APPROXIMATE` | Resultado aproximado |
| `GOOGLE_CACHE` | Coordenada reaproveitada sem método original disponível |
| `MUNICIPIO_IBGE_FALLBACK` | Centro municipal usado quando as buscas não resolvem o endereço |
| Sufixo `_SNAPPED` | Coordenada urbana ajustada ao eixo da via |

Os métodos oficiais são priorizados e preservados no reaproveitamento do cache. Coordenadas aproximadas e centros municipais não comprovam a posição física exata do radar. Use o filtro de método para avaliar a qualidade dos pontos antes de uma atividade de campo.

## Testes

Com as dependências instaladas, execute na raiz:

```powershell
python -m unittest discover -s tests -v
```

Os testes de regressão cobrem a configuração opcional do OneDrive, a indicação de sucesso/falha do processamento, a inclusão de registros sem coordenadas e a classificação de validade na data de vencimento. Usam dados simulados e não acionam APIs nem atualizam a planilha operacional.

Para verificar também o comportamento do mapa e da tabela com DOM e Leaflet simulados, use Node.js, sem instalar pacotes npm:

```powershell
node tests/test_dashboard_frontend.cjs
```

## Tecnologias

Python, Pandas, OpenPyXL, Requests, Google Maps Services e python-dotenv no processamento; Flask e Jinja2 no servidor; HTML, CSS, JavaScript e Leaflet no painel. Os recursos externos do mapa e bibliotecas carregadas por CDN dependem de conectividade.
