import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from config import MUNICIPIOS_ALVO, PROCESSED_DIR, RAW_DIR, RBMLQ_URL
from services.address_service import AddressService
from services.rbmlq_service import RBMLQService
from services.geocode_service import GeocodeService

CAMINHO_EXCEL = PROCESSED_DIR / "medidores_processados.xlsx"
COLUNAS_TRATADAS = [
    "tipo_local", "logradouro_limpo", "numero_limpo",
    "rodovia_nome", "km_num", "local_maps", "UF",
    "latitude", "longitude"
]

def main():
    print("1. Baixando dados atualizados do PSIE / RBMLQ...")
    service_rbmlq = RBMLQService(url=RBMLQ_URL, municipios=MUNICIPIOS_ALVO)
    raw_file = RAW_DIR / "medidores_bruto.json"
    itens = service_rbmlq.baixar_dados(save_raw_path=raw_file)

    df_inst_novo, df_faixas, df_hist = service_rbmlq.processar_e_estruturar(itens)

    # 2. Merge incremental com a base existente
    if CAMINHO_EXCEL.exists():
        print("Lendo base existente para checagem incremental...")
        df_inst_antigo = pd.read_excel(CAMINHO_EXCEL, sheet_name="Instrumentos")
        colunas_preservar = ["NumeroSerie"] + [c for c in COLUNAS_TRATADAS if c in df_inst_antigo.columns]
        
        df_inst = pd.merge(
            df_inst_novo.drop(columns=[c for c in COLUNAS_TRATADAS if c in df_inst_novo.columns], errors="ignore"),
            df_inst_antigo[colunas_preservar].drop_duplicates(subset=["NumeroSerie"]),
            on="NumeroSerie",
            how="left"
        )
    else:
        df_inst = df_inst_novo

    for col in COLUNAS_TRATADAS:
        if col not in df_inst.columns:
            df_inst[col] = None

    # 3. Padronização de endereços (Regex local instantâneo)
    mascara_pendentes = df_inst["logradouro_limpo"].isna() | (df_inst["logradouro_limpo"] == "")
    total_pendentes = mascara_pendentes.sum()
    
    if total_pendentes > 0:
        print(f"Padronizando endereços para {total_pendentes} novos registros...")
        for idx in df_inst[mascara_pendentes].index:
            local_raw = df_inst.at[idx, "LocalVerificacao"]
            muni = df_inst.at[idx, "Municipio"]
            res = AddressService.processar_endereco(local_raw, muni, uf="SP")
            for col, val in res.items():
                df_inst.at[idx, col] = val

    # 4. Geocodificação (Google Maps API)
    print("Iniciando geocodificação de Latitude e Longitude...")
    maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not maps_key:
        raise ValueError("GOOGLE_MAPS_API_KEY não encontrada nas variáveis de ambiente.")
    
    geocode_service = GeocodeService(api_key=maps_key)
    df_inst = geocode_service.processar_dataframe(df_inst)

    # 5. Salvar base completa nas abas do Excel
    print(f"Salvando planilha final em {CAMINHO_EXCEL}...")
    service_rbmlq.salvar_excel(df_inst, df_faixas, df_hist, out_path=CAMINHO_EXCEL)
    print("Processo concluído com sucesso! Endereços e coordenadas atualizados.")

if __name__ == "__main__":
    main()