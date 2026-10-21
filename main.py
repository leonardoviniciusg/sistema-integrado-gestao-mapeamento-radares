import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from config import (
    MUNICIPIOS_ALVO,
    PROCESSED_DIR,
    RAW_DIR,
    GEOCODED_DIR,
    RBMLQ_URL,
    ONEDRIVE_EXCEL,
)
from services.address_service import AddressService
from services.rbmlq_service import RBMLQService
from services.geocode_service import GeocodeService

CAMINHO_EXCEL = PROCESSED_DIR / "medidores_processados.xlsx"
COLUNAS_TRATADAS = [
    "tipo_local", "logradouro_limpo", "numero_limpo",
    "rodovia_nome", "km_num", "local_maps", "UF",
    "latitude", "longitude", "metodo_geocodificacao"
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

    # 3. Padronização de endereços (sempre reavalia via Regex e invalida lat/lon se local_maps mudou)
    print(f"Padronizando endereços para {len(df_inst)} registros...")
    enderecos_alterados = 0
    for idx in df_inst.index:
        local_raw = df_inst.at[idx, "LocalVerificacao"]
        muni = df_inst.at[idx, "Municipio"]
        local_maps_antigo = str(df_inst.at[idx, "local_maps"] or "")
        
        res = AddressService.processar_endereco(local_raw, muni, uf="SP")
        novo_local_maps = str(res["local_maps"] or "")
        
        if local_maps_antigo and local_maps_antigo != novo_local_maps:
            df_inst.at[idx, "latitude"] = None
            df_inst.at[idx, "longitude"] = None
            df_inst.at[idx, "metodo_geocodificacao"] = None
            enderecos_alterados += 1

        for col, val in res.items():
            df_inst.at[idx, col] = val

    if enderecos_alterados > 0:
        print(f"{enderecos_alterados} registros tiveram 'local_maps' aprimorado e terão coordenadas atualizadas.")

    # 4. Geocodificação (DER/SP + DNIT SP + Marcos KM + Google Maps API + Cache local)
    print("Iniciando verificação de Latitude e Longitude...")
    maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not maps_key:
        raise ValueError("GOOGLE_MAPS_API_KEY não encontrada nas variáveis de ambiente.")
    
    geocode_service = GeocodeService(api_key=maps_key, cache_dir=GEOCODED_DIR, raw_dir=RAW_DIR)
    df_inst = geocode_service.processar_dataframe(df_inst)

    print("\nResumo por Método de Geocodificação:")
    print(df_inst["metodo_geocodificacao"].value_counts(dropna=False).to_string())

    # 5. Salvar base completa nas abas do Excel (Local e Nuvem fixa)
    print(f"\nSalvando planilha local em {CAMINHO_EXCEL}...")
    service_rbmlq.salvar_excel(df_inst, df_faixas, df_hist, out_path=CAMINHO_EXCEL)

    if ONEDRIVE_EXCEL is None:
        print("Cópia no OneDrive desativada. Configure ONEDRIVE_DIR no .env para habilitar.")
        print("Processo concluído com sucesso!")
        return

    try:
        ONEDRIVE_EXCEL.parent.mkdir(parents=True, exist_ok=True)
        print(f"Sincronizando com a nuvem em {ONEDRIVE_EXCEL}...")
        service_rbmlq.salvar_excel(df_inst, df_faixas, df_hist, out_path=ONEDRIVE_EXCEL)
        print("Arquivo sincronizado com o OneDrive com sucesso!")
    except Exception as e:
        print(f"Aviso: Não foi possível salvar no OneDrive ({e}). Verifique se o arquivo não está aberto no Excel.")

    print("Processo concluído com sucesso!")

if __name__ == "__main__":
    main()
