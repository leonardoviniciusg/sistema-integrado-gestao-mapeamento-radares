# Sistema Integrado de Gestão e Mapeamento de Radares

Sistema em Python para extração, padronização cadastral, geocodificação em múltiplas camadas oficiais e consolidação operacional de medidores de velocidade (radares de trânsito) monitorados pelo Inmetro/IPEM na Região Metropolitana do Vale do Paraíba e Litoral Norte (SP).

---

## 🚀 Visão Geral e Funcionalidades

- **Extração Automatizada (RBMLQ / PSIE - Inmetro):** Download e processamento das bases oficiais de instrumentos de medição, faixas monitoradas e histórico metrológico de verificações.
- **Padronização e Canonização Textual de Endereços:** Normalização por expressões regulares para rodovias, cruzamentos e vias urbanas (expansão de tipos de logradouro, títulos de vias, correção ortográfica e preservação de números prediais de referência).
- **Pipeline de Geocodificação Híbrido em Múltiplas Camadas (Sem Duplicidades):**
  - **DER/SP (Estadual):** Mapeamento por número de série e marco quilométrico (KM) oficial na malha rodoviária estadual (`SP-xxx`, `SPA-xxx`, `SPI-xxx`).
  - **DNIT (Federal - PNCV):** Cruzamento direto com a base oficial de radares do Plano Nacional de Controle de Velocidade.
  - **ANTT (Concessões Federais):** Mapeamento georreferenciado de rodovias concedidas sob supervisão federal (ex: BR-116/Dutra e BR-101/Rio-Santos via CCR RioSP).
  - **VGEO / SGPLAN (DNIT):** Consulta automatizada ao serviço oficial de espacialização geodésica em trecho vetorial para rodovias federais.
  - **Google Maps Geocoding API:** Busca refinada com fallback para endereços urbanos (Rooftop, Interpolated) e cruzamentos físicos validados.
- **Cache Local e Otimização de Custos:** Estrutura persistente de cache geográfico em disco (`.csv`), evitando requisições redundantes a APIs pagas.
- **Exportação Multiformato e Nuvem:** Geração de planilha analítica formatada com tabelas e metadados (`.xlsx`), pronta para importação direta no **Google My Maps** ou sincronização em diretório local/nuvem (OneDrive).

---

## 📁 Estrutura do Projeto

```
.
├── config.py                 # Configurações de diretórios, URLs oficiais e municípios-alvo
├── main.py                   # Orquestrador do fluxo ETL (Extração, Tratamento e Geocodificação)
├── requirements.txt          # Dependências do projeto
├── .env.example              # Modelo de variáveis de ambiente
├── .gitignore                # Regras de exclusão do Git
├── README.md                 # Documentação técnica do sistema
├── data/
│   ├── raw/                  # Arquivos brutos baixados (PSIE JSON, DER/SP CSV, DNIT XLSX, ANTT CSV)
│   ├── geocoded/             # Caches locais (coordenadas_cache.csv, radares_dnit_sp.csv, vgeo_cache.csv)
│   └── processed/            # Planilha final consolidada (medidores_processados.xlsx)
└── services/
    ├── address_service.py    # Padronização, limpeza e classificação de vias e logradouros
    ├── rbmlq_service.py      # Extração da API RBMLQ/PSIE e formatação estruturada do Excel
    ├── highway_service.py    # Integração multibase de rodovias (DER/SP, DNIT, ANTT e VGEO)
    └── geocode_service.py    # Orquestrador de geocodificação, validação de limites municipais e Google Maps
```

---

## 🏛️ Fontes de Dados e Camadas de Geocodificação

A coluna `metodo_geocodificacao` gerada na planilha final classifica a origem do ponto geográfico em ordem estrita de precedência:

| Método | Origem | Nível de Precisão |
| :--- | :--- | :---: |
| `DER_SP_SERIE` | Base Oficial DER/SP (casamento por Número de Série) | Máxima (Ponto do Laudo) |
| `DER_SP_RODOVIA_KM` | Base Oficial DER/SP (casamento por Rodovia + KM exato) | Alta (Marco DER) |
| `DNIT_RODOVIA_KM` | Base PNCV do DNIT (casamento por Rodovia Federal + KM) | Alta (Marco DNIT) |
| `ANTT_RODOVIA_KM` | Base de Concessões da ANTT (CCR RioSP na BR-116 / BR-101) | Alta (Pórtico da Concessão) |
| `DNIT_VGEO_OFICIAL` | API GeoServer/SGPLAN do DNIT (espacialização linear de eixo) | Alta (Eixo da Rodovia) |
| `DER_SP_PROJETO` | Projeto Executivo Georreferenciado do DER-SP | Alta (Eixo da Pista) |
| `GOOGLE_ROOFTOP` | Google Maps Geocoding API (número predial exato) | Alta (Fachada do Imóvel) |
| `GOOGLE_INTERPOLATED`| Google Maps Geocoding API (interpolação na extensão da via) | Média-Alta |
| `GOOGLE_INTERSECTION`| Google Maps Geocoding API (cruzamento/esquina validada) | Média-Alta |
| `GOOGLE_APPROXIMATE` | Google Maps Geocoding API (via sem número predial) | Média |
| `GOOGLE_CACHE` | Cache local reaproveitado sem custo adicional de API | Depende da busca inicial |

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+**
- **Pandas / NumPy:** Manipulação vetorial e processamento de dados estruturados.
- **OpenPyXL:** Geração e estilização de planilhas Excel tabuladas.
- **Requests & Urllib3:** Consumo de APIs REST (Inmetro, DNIT CKAN, ANTT CKAN, VGEO).
- **Google Maps Services (Python):** Geocodificação urbana e tratamento de interseções.
- **Python-dotenv:** Gerenciamento seguro de configurações de ambiente.

---

## ⚙️ Instalação e Execução

### 1. Clonar o repositório

```bash
git clone https://github.com/leonardoviniciusg/sistema-integrado-gestao-mapeamento-radares.git
cd sistema-integrado-gestao-mapeamento-radares
```

### 2. Criar e ativar o ambiente virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto com base no `.env.example`:

```env
GOOGLE_MAPS_API_KEY=sua_chave_aqui
```

### 5. Executar o pipeline

```bash
python main.py
```

O sistema executará a extração do PSIE/Inmetro, o download/leitura das bases do DER, DNIT e ANTT, a padronização cadastral dos endereços e a validação geográfica, gerando o arquivo consolidado em `data/processed/medidores_processados.xlsx`.
## Painel Django na rede local

O painel utiliza Django 5.2 e Waitress (compatível com Windows), mantendo a porta 5000.
Na raiz do projeto, com seu ambiente virtual ativado:

```powershell
python -m pip install -r requirements.txt
python dashboard_v1/app.py
```

Mantenha esse terminal e o computador servidor ligados. Nas outras máquinas da mesma rede,
abra `http://172.27.152.41:5000` (IP Wi-Fi identificado durante a configuração).
O servidor escuta em `0.0.0.0`, que significa todas as interfaces; esse endereço não é o URL do navegador.
Se o IP mudar, consulte `ipconfig` e use o IPv4 do adaptador conectado. Para manter o endereço,
configure uma reserva DHCP no roteador com o responsável pela rede.

As variáveis opcionais no `.env` são:

```env
HOST=0.0.0.0
PORT=5000
DJANGO_ALLOWED_HOSTS=172.27.152.41
SERVER_THREADS=32
# Opcional: uma chave secreta aleatória persistente
# DJANGO_SECRET_KEY=...
```

O nome e os IPv4 da máquina são autorizados automaticamente. Adicione nomes DNS ou IPs
adicionais em `DJANGO_ALLOWED_HOSTS`, separados por vírgula. O modo debug fica desligado
e os POSTs do painel usam proteção CSRF.

Caso o Firewall do Windows bloqueie o acesso, execute no PowerShell como administrador:

```powershell
New-NetFirewallRule -DisplayName "PSIE Django 5000 (rede local)" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000 -Profile Private,Domain -RemoteAddress LocalSubnet
```

O painel compartilha dados e comandos de atualização com quem tem acesso à rede; ele não
possui login. A rede precisa permitir comunicação entre os dispositivos.
Use um único processo de servidor: o estado da atualização e os logs são compartilhados entre
as threads desse processo. Cada aba aberta mantém uma conexão de logs; para muitos usuários,
ajuste `SERVER_THREADS` (padrão 32) deixando threads livres para as APIs.

Para verificar a configuração ou desenvolver:

```powershell
python manage.py check
python manage.py runserver 0.0.0.0:5000 --noreload
```

Referências: [Django CSRF](https://docs.djangoproject.com/en/dev/howto/csrf/)
e [Waitress](https://docs.pylonsproject.org/projects/waitress/en/latest/api.html).
