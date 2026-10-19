import math
import os
import time
import unicodedata
from pathlib import Path
import googlemaps
import pandas as pd

from config import GEOCODED_DIR, RAW_DIR
from services.highway_service import HighwayService
from services.snapping_service import SnappingService

NOMES_RODOVIAS = {
    "BR-101": "Rodovia Governador Mário Covas BR-101",
    "BR-116": "Rodovia Presidente Dutra BR-116",
    "BR-459": "Rodovia BR-459",
    "BR-488": "Rodovia BR-488",
    "SP-036": "Rodovia José Augusto Freire SP-036",
    "SP-042": "Rodovia Vereador Júlio da Silva SP-042",
    "SP-046": "Rodovia Oswaldo Barbosa Guisardi SP-046",
    "SP-050": "Rodovia Monteiro Lobato SP-050",
    "SP-052": "Rodovia Doutor Avelino Júnior SP-052",
    "SP-055": "Rodovia Doutor Manuel Hipólito Rego SP-055",
    "SP-056": "Rodovia Prefeito Joaquim Simão SP-056",
    "SP-058": "Rodovia Deputado Nesralla Rubez SP-058",
    "SP-062": "Rodovia Vito Ardito SP-062",
    "SP-065": "Rodovia Dom Pedro I SP-065",
    "SP-066": "Rodovia Henrique Eroles SP-066",
    "SP-068": "Rodovia dos Tropeiros SP-068",
    "SP-070": "Rodovia Governador Carvalho Pinto SP-070",
    "SP-077": "Rodovia Nilo Máximo SP-077",
    "SP-088": "Rodovia Professor Alfredo Rolim de Moura SP-088",
    "SP-099": "Rodovia dos Tamoios SP-099",
    "SP-121": "Rodovia Major Gabriel Ortiz Monteiro SP-121",
    "SP-123": "Rodovia Floriano Rodrigues Pinheiro SP-123",
    "SP-125": "Rodovia Oswaldo Cruz SP-125",
    "SP-132": "Rodovia Caio Gomes Figueiredo SP-132",
    "SP-153": "Rodovia João Martins Corrêa SP-153",
    "SP-171": "Rodovia Paulo Virgínio SP-171",
    "SP-183": "Rodovia Comandante João Ribeiro de Barros SP-183",
    "SPI-097/055": "Rodovia Caraguatatuba-São Sebastião SPI-097/055",
    "SPI-172/060": "Rodovia de Acesso SPI-172/060",
    "SPA-017/123": "Rodovia de Acesso SPA-017/123",
    "SPA-021/060": "Rodovia de Acesso SPA-021/060",
    "SPA-085/060": "Rodovia de Acesso SPA-085/060",
    "SPA-092/060": "Rodovia de Acesso Doutor Caio Gomes Figueiredo SPA-092/060",
    "SPA-099/060": "Rodovia de Acesso SPA-099/060",
}

CENTROS_MUNICIPIOS_IBGE = {
    "APARECIDA": (-22.8469, -45.2297),
    "ARAPEI": (-22.6736, -44.4475),
    "ARAPEÍ": (-22.6736, -44.4475),
    "AREIAS": (-22.5800, -44.6972),
    "BANANAL": (-22.6836, -44.3233),
    "BIRITIBA-MIRIM": (-23.5728, -46.0386),
    "CACAPAVA": (-23.1008, -45.7069),
    "CAÇAPAVA": (-23.1008, -45.7069),
    "CACHOEIRA PAULISTA": (-22.6650, -45.0094),
    "CAMPOS DO JORDAO": (-22.7394, -45.5914),
    "CAMPOS DO JORDÃO": (-22.7394, -45.5914),
    "CANAS": (-22.7036, -45.0553),
    "CARAGUATATUBA": (-23.6203, -45.4131),
    "CRUZEIRO": (-22.5761, -44.9614),
    "CUNHA": (-23.0744, -44.9597),
    "GUARAREMA": (-23.4150, -46.0367),
    "GUARATINGUETA": (-22.8164, -45.1925),
    "GUARATINGUETÁ": (-22.8164, -45.1925),
    "IGARATA": (-23.2044, -46.1561),
    "IGARATÁ": (-23.2044, -46.1561),
    "JACAREI": (-23.3053, -45.9658),
    "JACAREÍ": (-23.3053, -45.9658),
    "JAMBEIRO": (-23.2536, -45.6897),
    "LAGOINHA": (-23.0906, -45.1903),
    "LAVRINHAS": (-22.5706, -44.9019),
    "LORENA": (-22.7308, -45.1247),
    "MONTEIRO LOBATO": (-22.9567, -45.8397),
    "NATIVIDADE DA SERRA": (-23.3756, -45.4419),
    "NAZARE PAULISTA": (-23.1811, -46.3950),
    "NAZARÉ PAULISTA": (-23.1811, -46.3950),
    "PARAIBUNA": (-23.3861, -45.6622),
    "PINDAMONHANGABA": (-22.9239, -45.4617),
    "PIQUETE": (-22.6136, -45.1761),
    "POTIM": (-22.8428, -45.2514),
    "QUELUZ": (-22.5372, -44.7744),
    "REDENCAO DA SERRA": (-23.2667, -45.5369),
    "REDENÇÃO DA SERRA": (-23.2667, -45.5369),
    "ROSEIRA": (-22.8978, -45.3050),
    "SALESOPOLIS": (-23.5322, -45.8464),
    "SALESÓPOLIS": (-23.5322, -45.8464),
    "SANTA BRANCA": (-23.3967, -45.8839),
    "SANTO ANTONIO DO PINHAL": (-22.8269, -45.6625),
    "SANTO ANTÔNIO DO PINHAL": (-22.8269, -45.6625),
    "SAO BENTO DO SAPUCAI": (-22.6889, -45.7308),
    "SÃO BENTO DO SAPUCAÍ": (-22.6889, -45.7308),
    "SAO JOSE DO BARREIRO": (-22.6450, -44.5778),
    "SÃO JOSÉ DO BARREIRO": (-22.6450, -44.5778),
    "SAO JOSE DOS CAMPOS": (-23.1791, -45.8872),
    "SÃO JOSÉ DOS CAMPOS": (-23.1791, -45.8872),
    "SAO LUIZ DO PARAITINGA": (-23.2217, -45.3100),
    "SÃO LUIZ DO PARAITINGA": (-23.2217, -45.3100),
    "SILVEIRAS": (-22.6642, -44.8528),
    "TAUBATE": (-23.0264, -45.5553),
    "TAUBATÉ": (-23.0264, -45.5553),
    "TREMEMBE": (-22.9583, -45.5494),
    "TREMEMBÉ": (-22.9583, -45.5494),
    "UBATUBA": (-23.4339, -45.0711),
}


class GeocodeService:
    def __init__(self, api_key: str | None = None, cache_dir: Path = GEOCODED_DIR, raw_dir: Path = RAW_DIR):
        chave = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        if not chave:
            raise ValueError("GOOGLE_MAPS_API_KEY não encontrada nas variáveis de ambiente.")
        self.gmaps = googlemaps.Client(key=chave)

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.cache_dir / "coordenadas_cache.csv"
        self.cache_df = self._carregar_cache()

        self.highway_service = HighwayService(
            raw_dir=raw_dir,
            geocoded_dir=cache_dir,
            centros_municipios=CENTROS_MUNICIPIOS_IBGE
        )
        self.snapping_service = SnappingService(api_key=chave, cache_dir=cache_dir)

    def _carregar_cache(self) -> pd.DataFrame:
        cols = ["NumeroSerie", "latitude", "longitude", "tipo_local", "local_maps", "metodo_geocodificacao"]
        if self.cache_path.exists():
            try:
                df_c = pd.read_csv(self.cache_path, dtype={"NumeroSerie": str})
                if "metodo_geocodificacao" not in df_c.columns:
                    df_c["metodo_geocodificacao"] = None
                print(f"Cache de coordenadas carregado: {len(df_c)} registros disponíveis.")
                return df_c
            except Exception as e:
                print(f"Erro ao carregar cache ({e}). Criando nova base de cache...")
        return pd.DataFrame(columns=cols)

    def _salvar_cache(self):
        try:
            self.cache_df.drop_duplicates(subset=["NumeroSerie"], keep="last").to_csv(self.cache_path, index=False)
        except Exception as e:
            print(f"Erro ao salvar arquivo de cache: {e}")

    @staticmethod
    def _normalizar_chave_muni(municipio: str) -> str:
        texto = unicodedata.normalize("NFKD", str(municipio or ""))
        return "".join(c for c in texto if not unicodedata.combining(c)).strip().upper()

    @staticmethod
    def _distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        dlat = (lat2 - lat1) * 111.0
        dlon = (lon2 - lon1) * 102.0
        return math.hypot(dlat, dlon)

    def _obter_centro_municipio(self, municipio: str) -> tuple[float | None, float | None]:
        chave = self._normalizar_chave_muni(municipio)
        return CENTROS_MUNICIPIOS_IBGE.get(chave, (None, None))

    def _obter_bounds_municipio(self, municipio: str, delta: float = 0.18) -> dict | None:
        c_lat, c_lon = self._obter_centro_municipio(municipio)
        if c_lat is None or c_lon is None:
            return None
        return {
            "southwest": {"lat": c_lat - delta, "lng": c_lon - delta},
            "northeast": {"lat": c_lat + delta, "lng": c_lon + delta},
        }

    def _coordenada_eh_valida(self, lat: float | None, lon: float | None, municipio: str, max_dist_km: float = 38.0) -> bool:
        if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
            return False
        centro_lat, centro_lon = self._obter_centro_municipio(municipio)
        if centro_lat is not None and centro_lon is not None:
            if self._distancia_km(float(lat), float(lon), centro_lat, centro_lon) > max_dist_km:
                return False
        return True

    @staticmethod
    def _classificar_retorno_google(candidato: dict, tipo_local: str) -> str:
        types = set(candidato.get("types", []))
        loc_type = candidato.get("geometry", {}).get("location_type", "")
        if "intersection" in types:
            return "GOOGLE_INTERSECTION"
        if loc_type == "ROOFTOP":
            return "GOOGLE_ROOFTOP"
        if loc_type == "RANGE_INTERPOLATED":
            return "GOOGLE_INTERPOLATED"
        return "GOOGLE_APPROXIMATE"

    def _buscar_coordenada_urbana(self, query: str, municipio: str, tipo_local: str = "Urbano") -> tuple[float | None, float | None, str]:
        bounds = self._obter_bounds_municipio(municipio, delta=0.15)
        queries_tentar = [query]

        if tipo_local == "Cruzamento" and " & " in query:
            queries_tentar.append(query.replace(" & ", " esquina com "))
            queries_tentar.append(query.replace(" & ", " com "))

        melhor_fallback = None

        for q in queries_tentar:
            try:
                for comp in [
                    {"locality": municipio, "administrative_area": "SP", "country": "BR"},
                    {"administrative_area": "SP", "country": "BR"},
                ]:
                    res = self.gmaps.geocode(q, components=comp, bounds=bounds, region="br")
                    if not res:
                        continue
                    for cand in res:
                        cand_types = set(cand.get("types", []))
                        if cand_types.intersection({"locality", "administrative_area_level_2", "political"}) and not cand_types.intersection({"route", "street_address", "intersection", "premise", "subpremise"}):
                            continue

                        loc = cand["geometry"]["location"]
                        if self._coordenada_eh_valida(loc["lat"], loc["lng"], municipio, max_dist_km=25.0):
                            metodo = self._classificar_retorno_google(cand, tipo_local)
                            if tipo_local == "Cruzamento" and metodo == "GOOGLE_INTERSECTION":
                                return loc["lat"], loc["lng"], metodo
                            if tipo_local != "Cruzamento" and metodo in ("GOOGLE_ROOFTOP", "GOOGLE_INTERPOLATED"):
                                return loc["lat"], loc["lng"], metodo
                            if melhor_fallback is None:
                                melhor_fallback = (loc["lat"], loc["lng"], metodo)
            except Exception as e:
                print(f"Erro ao geocodificar urbano '{q}': {e}")

        if melhor_fallback:
            return melhor_fallback

        c_lat, c_lon = self._obter_centro_municipio(municipio)
        return c_lat, c_lon, "MUNICIPIO_IBGE_FALLBACK"

    def _buscar_coordenada_rodovia(self, num_serie: str, rodovia: str, km_num: float | None, municipio: str) -> tuple[float | None, float | None, str]:
        lat_hw, lon_hw, metodo_hw = self.highway_service.buscar_coordenada_rodovia(num_serie, rodovia, km_num, municipio)
        if lat_hw is not None and lon_hw is not None:
            if self._coordenada_eh_valida(lat_hw, lon_hw, municipio, max_dist_km=42.0):
                return lat_hw, lon_hw, metodo_hw

        nome_expandido = NOMES_RODOVIAS.get(rodovia, rodovia)
        km_str = f"{km_num:.3f}".rstrip("0").rstrip(".").replace(".", ",") if km_num is not None else ""
        bounds = self._obter_bounds_municipio(municipio, delta=0.22)

        tentativas = []
        if km_str:
            tentativas.append(f"{nome_expandido}, KM {km_str}, {municipio} - SP")
            tentativas.append(f"{rodovia}, KM {km_str}, {municipio} - SP")
        tentativas.append(f"{nome_expandido}, {municipio} - SP")

        for query in tentativas:
            try:
                res = self.gmaps.geocode(
                    query,
                    components={"administrative_area": "SP", "country": "BR"},
                    bounds=bounds,
                    region="br"
                )
                if res:
                    for candidato in res:
                        loc = candidato["geometry"]["location"]
                        if self._coordenada_eh_valida(loc["lat"], loc["lng"], municipio, max_dist_km=35.0):
                            metodo = self._classificar_retorno_google(candidato, "Rodovia")
                            return loc["lat"], loc["lng"], metodo
            except Exception as e:
                print(f"Erro ao geocodificar rodovia '{query}': {e}")

        c_lat, c_lon = self._obter_centro_municipio(municipio)
        return c_lat, c_lon, "MUNICIPIO_IBGE_FALLBACK"

    def processar_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df_geo = df.copy()

        for col in ["latitude", "longitude", "metodo_geocodificacao"]:
            if col not in df_geo.columns:
                df_geo[col] = None

        # 1. Atualização automática de rodovias (DER, DNIT, ANTT, VGEO e Projeto DER)
        atualizados_rod = 0
        for idx, row in df_geo[df_geo["tipo_local"] == "Rodovia"].iterrows():
            num_serie = str(row.get("NumeroSerie") or "")
            rodovia = str(row.get("rodovia_nome") or "")
            km_num = row.get("km_num")
            km_val = float(km_num) if pd.notna(km_num) else None
            muni = str(row.get("Municipio") or "")

            lat_hw, lon_hw, metodo_hw = self.highway_service.buscar_coordenada_rodovia(num_serie, rodovia, km_val, muni)
            if lat_hw is not None and lon_hw is not None:
                if self._coordenada_eh_valida(lat_hw, lon_hw, muni, max_dist_km=42.0):
                    df_geo.at[idx, "latitude"] = lat_hw
                    df_geo.at[idx, "longitude"] = lon_hw
                    df_geo.at[idx, "metodo_geocodificacao"] = metodo_hw
                    atualizados_rod += 1

        if atualizados_rod > 0:
            print(f"{atualizados_rod} instrumentos de rodovias atualizados via bases oficiais!")

        # 2. Cache local (preserva métodos oficiais e reaproveita coordenadas válidas)
        metodos_oficiais = (
            "DER_SP_SERIE", "DER_SP_RODOVIA_KM", "DNIT_RODOVIA_KM",
            "ANTT_RODOVIA_KM", "DNIT_VGEO_OFICIAL", "DER_SP_PROJETO"
        )
        if not self.cache_df.empty:
            cache_map = self.cache_df.drop_duplicates(subset=["NumeroSerie"], keep="last").set_index("NumeroSerie").to_dict(orient="index")
            recuperados_cache = 0
            for idx, row in df_geo.iterrows():
                if pd.notna(row.get("metodo_geocodificacao")) and str(row.get("metodo_geocodificacao")) in metodos_oficiais:
                    continue

                num_serie = str(row.get("NumeroSerie"))
                local_atual = str(row.get("local_maps") or "")
                muni = str(row.get("Municipio") or "")

                if num_serie in cache_map:
                    reg_c = cache_map[num_serie]
                    lat_c, lon_c = reg_c.get("latitude"), reg_c.get("longitude")
                    local_c = str(reg_c.get("local_maps") or "")
                    metodo_c = reg_c.get("metodo_geocodificacao") or "GOOGLE_CACHE"

                    if local_c and local_c != local_atual:
                        df_geo.at[idx, "latitude"] = None
                        df_geo.at[idx, "longitude"] = None
                        df_geo.at[idx, "metodo_geocodificacao"] = None
                    elif pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
                        if self._coordenada_eh_valida(lat_c, lon_c, muni, max_dist_km=38.0):
                            df_geo.at[idx, "latitude"] = lat_c
                            df_geo.at[idx, "longitude"] = lon_c
                            df_geo.at[idx, "metodo_geocodificacao"] = metodo_c
                            recuperados_cache += 1

            if recuperados_cache > 0:
                print(f"{recuperados_cache} coordenadas preenchidas a partir do cache local.")

        # 3. Limpeza de colisões urbanas/cruzamentos antigos herdados da planilha anterior
        valid_coords = df_geo.dropna(subset=["latitude", "longitude"])
        colisoes_reprocessar = 0
        for (lat, lon), grupo in valid_coords.groupby(["latitude", "longitude"]):
            locais_distintos = grupo["local_maps"].dropna().astype(str).unique()
            if len(locais_distintos) > 1:
                for idx in grupo.index:
                    metodo_atual = str(df_geo.at[idx, "metodo_geocodificacao"] or "")
                    if metodo_atual in ("", "None", "GOOGLE_CACHE"):
                        df_geo.at[idx, "latitude"] = None
                        df_geo.at[idx, "longitude"] = None
                        df_geo.at[idx, "metodo_geocodificacao"] = None
                        colisoes_reprocessar += 1

        if colisoes_reprocessar > 0:
            print(f"{colisoes_reprocessar} registros urbanos/cruzamentos com coordenadas colididas marcados para reconsulta refinada na API.")

        # 4. Validação de raio municipal
        invalidos = 0
        for idx, row in df_geo.iterrows():
            lat, lon = row.get("latitude"), row.get("longitude")
            muni = str(row.get("Municipio") or "")
            if pd.notna(lat) and pd.notna(lon):
                if not self._coordenada_eh_valida(float(lat), float(lon), muni, max_dist_km=42.0):
                    df_geo.at[idx, "latitude"] = None
                    df_geo.at[idx, "longitude"] = None
                    df_geo.at[idx, "metodo_geocodificacao"] = None
                    invalidos += 1

        if invalidos > 0:
            print(f"Detectadas {invalidos} coordenadas fora do município. Marcadas para reprocessamento...")

        filtro_pendentes = df_geo["latitude"].isna() | df_geo["longitude"].isna()
        total_pendentes = filtro_pendentes.sum()

        for idx, row in df_geo[~filtro_pendentes].iterrows():
            if pd.isna(row.get("metodo_geocodificacao")) or not str(row.get("metodo_geocodificacao")).strip():
                df_geo.at[idx, "metodo_geocodificacao"] = "GOOGLE_CACHE"

        # 5. Geocodificação de pendentes na API do Google
        if total_pendentes > 0:
            print(f"Total de registros para geocodificar na API do Google: {total_pendentes}")
            contador = 0
            for idx, row in df_geo[filtro_pendentes].iterrows():
                contador += 1
                tipo = str(row.get("tipo_local") or "Urbano")
                municipio = str(row.get("Municipio") or "")
                num_serie = str(row.get("NumeroSerie") or "")

                if tipo == "Rodovia":
                    rodovia = str(row.get("rodovia_nome") or "")
                    km_num = row.get("km_num")
                    km_val = float(km_num) if pd.notna(km_num) else None
                    print(f"Buscando ({contador}/{total_pendentes}) [Rodovia]: {rodovia} KM {km_val} - {municipio}")
                    lat, lon, metodo = self._buscar_coordenada_rodovia(num_serie, rodovia, km_val, municipio)
                else:
                    query = str(row.get("local_maps") or "")
                    print(f"Buscando ({contador}/{total_pendentes}) [{tipo}]: {query}")
                    lat, lon, metodo = self._buscar_coordenada_urbana(query, municipio, tipo_local=tipo)

                if lat and lon:
                    df_geo.at[idx, "latitude"] = lat
                    df_geo.at[idx, "longitude"] = lon
                    df_geo.at[idx, "metodo_geocodificacao"] = metodo
                    print(f"  -> Sucesso [{metodo}]: Lat {lat:.6f}, Lon {lon:.6f}")
                else:
                    print("  -> Não encontrado.")

                time.sleep(0.15)

        # 6. Alinhamento Global no Eixo da Via (Snapping to Road)
        # Executa em todos os radares urbanos com número de porta (novos ou vindos do cache)
        print("Executando alinhamento no eixo da via (Snapping to Road)...")
        snapped_count = 0
        for idx, row in df_geo.iterrows():
            tipo = str(row.get("tipo_local") or "")
            metodo = str(row.get("metodo_geocodificacao") or "")
            lat = row.get("latitude")
            lon = row.get("longitude")

            # Snapping exclusivo para endereços urbanos com número predial
            deve_ajustar = (
                tipo == "Urbano"
                and pd.notna(lat) and pd.notna(lon)
                and not metodo.endswith("_SNAPPED")
                and (
                    metodo in ("GOOGLE_ROOFTOP", "GOOGLE_INTERPOLATED")
                    or (metodo == "GOOGLE_CACHE" and str(row.get("numero_limpo")) != "S/N")
                )
            )

            if deve_ajustar:
                lat_rua, lon_rua, ajustou = self.snapping_service.ajustar_para_eixo_rua(
                    float(lat), float(lon), max_dist_metros=40.0
                )
                if ajustou:
                    df_geo.at[idx, "latitude"] = lat_rua
                    df_geo.at[idx, "longitude"] = lon_rua
                    df_geo.at[idx, "metodo_geocodificacao"] = f"{metodo}_SNAPPED"
                    snapped_count += 1

        if snapped_count > 0:
            print(f"{snapped_count} radares urbanos foram projetados com precisão no eixo do asfalto!")
        else:
            print("Todos os radares urbanos elegíveis já estão alinhados ao asfalto.")

        # 7. Salva cache unificado
        cols_salvar = ["NumeroSerie", "latitude", "longitude", "tipo_local", "local_maps", "metodo_geocodificacao"]
        novos_dados = df_geo[cols_salvar].dropna(subset=["latitude", "longitude"])
        self.cache_df = pd.concat([self.cache_df, novos_dados]).drop_duplicates(subset=["NumeroSerie"], keep="last")
        self._salvar_cache()
        print(f"Cache de coordenadas atualizado e salvo em {self.cache_path}.")

        return df_geo