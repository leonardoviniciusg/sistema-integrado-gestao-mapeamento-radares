from pathlib import Path

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
GEOCODED_DIR = DATA_DIR / "geocoded"
# Caminho da pasta corporativa na nuvem (OneDrive - PRODESP)
ONEDRIVE_DIR = Path(r"C:\Users\Leonardo\OneDrive - PRODESP\IPEM - RSJCA - Documentos\Planilhas Radares - Fonte PSIE")
ONEDRIVE_EXCEL = ONEDRIVE_DIR / "medidores_processados.xlsx"

# Cria os diretórios se não existirem
for pasta in [RAW_DIR, PROCESSED_DIR, GEOCODED_DIR]:
    pasta.mkdir(parents=True, exist_ok=True)

# URL RBMLQ
RBMLQ_URL = "https://servicos.rbmlq.gov.br/dados-abertos/SP/medidores.json"

# Municípios de interesse
MUNICIPIOS_ALVO = [
    "APARECIDA", "ARAPEÍ", "AREIAS", "BANANAL", "BIRITIBA-MIRIM",
    "CAÇAPAVA", "CACHOEIRA PAULISTA", "CAMPOS DO JORDÃO", "CANAS",
    "CARAGUATATUBA", "CRUZEIRO", "CUNHA", "GUARAREMA", "GUARATINGUETÁ",
    "IGARATÁ", "JACAREÍ", "JAMBEIRO", "LAGOINHA", "LAVRINHAS", "LORENA",
    "MONTEIRO LOBATO", "NATIVIDADE DA SERRA", "NAZARÉ PAULISTA", "PARAIBUNA",
    "PINDAMONHANGABA", "PIQUETE", "POTIM", "QUELUZ", "REDENÇÃO DA SERRA",
    "ROSEIRA", "SALESÓPOLIS", "SANTA BRANCA", "SANTO ANTÔNIO DO PINHAL",
    "SÃO BENTO DO SAPUCAÍ", "SÃO JOSÉ DO BARREIRO", "SÃO JOSÉ DOS CAMPOS",
    "SÃO LUIZ DO PARAITINGA", "SILVEIRAS", "TAUBATÉ", "TREMEMBÉ", "UBATUBA"
]

# Caminhos do arquivo fixo e do arquivo versionado com data/hora
ONEDRIVE_DIR = Path(r"C:\Users\Leonardo\OneDrive - PRODESP\IPEM - RSJCA - Documentos\Planilhas Radares - Fonte PSIE")
ONEDRIVE_EXCEL_FIXO = ONEDRIVE_DIR / "medidores_processados.xlsx"