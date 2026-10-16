from pathlib import Path

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
GEOCODED_DIR = DATA_DIR / "geocoded"

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