from datetime import datetime
import math
from pathlib import Path
import re
import unicodedata
import numpy as np
import pandas as pd
import requests
import urllib3

from config import GEOCODED_DIR, RAW_DIR

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Base oficial de radares do DNIT em SP (PNCV 07/2026) embutida para garantia de disponibilidade
RADARES_DNIT_SP_OFICIAL = [
    ("BR-459", 16.61, "PIQUETE", -22.624243, -45.161684),
    ("BR-459", 26.30, "LORENA", -22.696500, -45.121300),
    ("BR-459", 29.35, "LORENA", -22.719959, -45.106805),
    ("BR-459", 29.85, "LORENA", -22.724121, -45.104064),
    ("BR-459", 30.70, "LORENA", -22.730523, -45.100116),
    ("BR-459", 31.65, "LORENA", -22.734203, -45.097879),
    ("BR-488", 1.13, "APARECIDA", -22.849104, -45.231637),
    ("BR-488", 1.30, "APARECIDA", -22.848078, -45.231636),
    ("BR-488", 1.46, "APARECIDA", -22.847013, -45.232336),
    ("BR-488", 1.59, "APARECIDA", -22.847129, -45.233223),
    ("BR-488", 2.47, "APARECIDA", -22.852415, -45.239011),
    ("BR-488", 3.02, "APARECIDA", -22.854836, -45.243089),
    ("BR-488", 3.07, "APARECIDA", -22.855132, -45.243455),
    ("BR-488", 3.67, "APARECIDA", -22.857820, -45.247863),
    ("BR-488", 3.82, "APARECIDA", -22.858321, -45.249257),
    ("BR-488", 4.43, "APARECIDA", -22.860427, -45.253881),
    ("BR-488", 4.48, "APARECIDA", -22.860796, -45.254090),
    ("BR-488", 4.84, "APARECIDA", -22.863434, -45.255713),
    ("BR-488", 4.97, "APARECIDA", -22.864610, -45.255205),
    ("BR-488", 5.25, "APARECIDA", -22.868349, -45.256527),
]

# Marcos de alta precisão no eixo da via para os casos sem coordenada válida no DER/DNIT/ANTT/VGEO
MARCOS_RODOVIAS_SP = {
    "BR-116": [
        (22.310, -22.585081, -44.879807),
        (27.590, -22.621919, -44.909544),
        (28.062, -22.624533, -44.912904),
        (38.492, -22.671890, -44.995530),
        (54.000, -22.757284, -45.114169),
        (60.305, -22.792350, -45.163017),
        (65.402, -22.821874, -45.196989),
        (68.396, -22.835630, -45.220051),
        (69.367, -22.843230, -45.224667),
        (92.195, -22.952550, -45.405246),
        (94.295, -22.961480, -45.423261),
        (102.000, -22.992650, -45.490120),
        (106.100, -23.013016, -45.523252),
        (108.320, -23.025326, -45.540608),
        (116.270, -23.054420, -45.610510),
        (116.290, -23.054514, -45.610683),
        (130.470, -23.122859, -45.727756),
        (143.490, -23.176420, -45.841580),
        (146.880, -23.193150, -45.869820),
        (148.750, -23.203690, -45.882728),
        (163.400, -23.287517, -45.993596),
        (176.350, -23.356840, -46.038120),
    ],
    "BR-101": [
        (35.331, -23.392756, -45.009061),
        (46.600, -23.425878, -45.077354),
        (48.631, -23.440116, -45.087368),
        (50.500, -23.452695, -45.074811),
    ],
    "SPI-097/055": [
        (4.500, -23.635850, -45.432100),
        (6.078, -23.643120, -45.441850),
        (13.023, -23.666824, -45.465088),
        (13.620, -23.671417, -45.468028),
    ],
    "BR-488": [
        (1.590, -22.847129, -45.233223),
        (2.270, -22.851180, -45.237540),
        (2.470, -22.852415, -45.239011),
    ],
    "BR-459": [
        (16.610, -22.624243, -45.161684),
        (17.030, -22.627680, -45.158950),
        (20.150, -22.652140, -45.144280),
        (26.300, -22.696500, -45.121300),
    ],
}


class HighwayService:
    DNIT_CKAN_API = "https://servicos.dnit.gov.br/dadosabertos/api/3/action/package_show?id=controle-de-velocidade"
    ANTT_CKAN_API = "https://dados.antt.gov.br/api/3/action/package_show?id=radar"
    DNIT_VGEO_API = "https://servicos.dnit.gov.br/sgplan/apigeo/rotas/espacializarlinha"

    def __init__(self, raw_dir: Path = RAW_DIR, geocoded_dir: Path = GEOCODED_DIR, centros_municipios: dict | None = None):
        self.raw_dir = Path(raw_dir)
        self.geocoded_dir = Path(geocoded_dir)
        self.centros_municipios = centros_municipios or {}
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.geocoded_dir.mkdir(parents=True, exist_ok=True)

        self.df_der = self._carregar_base_der()
        self.df_dnit_sp = self._carregar_base_dnit_sp()
        self.df_antt_sp = self._carregar_base_antt_sp()

        # Cache persistente do VGEO
        self.vgeo_cache_path = self.geocoded_dir / "vgeo_cache.csv"
        self.df_vgeo_cache = self._carregar_vgeo_cache()

    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        t = unicodedata.normalize("NFKD", str(texto or ""))
        return "".join(c for c in t if not unicodedata.combining(c)).strip().upper()

    @staticmethod
    def _normalizar_serie(s: str) -> str:
        s_clean = str(s or "").strip().upper()
        s_base = s_clean.split("/")[0].strip()
        s_sem_zero = s_base.lstrip("0")
        return s_sem_zero if s_sem_zero else s_base

    @staticmethod
    def _padronizar_rodovia(val: str) -> str:
        v = str(val or "").upper().strip()
        m_spa = re.search(r"\b(SPA|SPI|SPD)\s*[-/]?\s*(\d{1,3})\s*[/\s]\s*(\d{1,3})\b", v)
        if m_spa:
            return f"{m_spa.group(1)}-{int(m_spa.group(2)):03d}/{int(m_spa.group(3)):03d}"
        m_sp = re.search(r"^(SP|BR)\s*[-/]?\s*(\d{1,3})$", v)
        if m_sp:
            return f"{m_sp.group(1)}-{int(m_sp.group(2)):03d}"
        return v

    def _distancia_centro_muni(self, lat: float, lon: float, municipio: str) -> float:
        chave = self._normalizar_texto(municipio)
        if chave in self.centros_municipios:
            c_lat, c_lon = self.centros_municipios[chave]
            return math.hypot((lat - c_lat) * 111.0, (lon - c_lon) * 102.0)
        return 0.0

    def _carregar_vgeo_cache(self) -> pd.DataFrame:
        if self.vgeo_cache_path.exists():
            try:
                return pd.read_csv(self.vgeo_cache_path)
            except Exception:
                pass
        return pd.DataFrame(columns=["rodovia", "km", "uf", "latitude", "longitude"])

    def _salvar_vgeo_cache(self):
        try:
            self.df_vgeo_cache.drop_duplicates(subset=["rodovia", "km", "uf"], keep="last").to_csv(self.vgeo_cache_path, index=False)
        except Exception:
            pass

    def _consultar_vgeo_dnit(self, rodovia: str, km_val: float, uf: str = "SP") -> tuple[float | None, float | None]:
        br_num = str(rodovia).replace("BR-", "").replace("BR", "").strip()
        km_arred = round(float(km_val), 3)

        if not self.df_vgeo_cache.empty:
            match = self.df_vgeo_cache[
                (self.df_vgeo_cache["rodovia"] == f"BR-{int(br_num):03d}")
                & (self.df_vgeo_cache["km"].round(3) == km_arred)
                & (self.df_vgeo_cache["uf"] == uf.upper())
            ]
            if not match.empty:
                r = match.iloc[0]
                return float(r["latitude"]), float(r["longitude"])

        hoje_str = datetime.now().strftime("%Y-%m-%d")
        kmi = km_arred
        kmf = round(kmi + 0.01, 3)

        params = {
            "br": br_num,
            "tipo": "B",
            "uf": uf.upper(),
            "cd_tipo": "null",
            "data": hoje_str,
            "kmi": f"{kmi:.3f}".rstrip("0").rstrip("."),
            "kmf": f"{kmf:.3f}".rstrip("0").rstrip("."),
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://servicos.dnit.gov.br/vgeo/",
            "Accept": "application/json, text/plain, */*",
        }

        try:
            resp = requests.get(self.DNIT_VGEO_API, params=params, headers=headers, verify=False, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]

                geom = data.get("geometry", {})
                coords = geom.get("coordinates", [])
                if coords:
                    primeiro_ponto = coords[0]
                    while isinstance(primeiro_ponto[0], list):
                        primeiro_ponto = primeiro_ponto[0]

                    lon = float(primeiro_ponto[0])
                    lat = float(primeiro_ponto[1])

                    novo_reg = pd.DataFrame([{
                        "rodovia": f"BR-{int(br_num):03d}",
                        "km": km_arred,
                        "uf": uf.upper(),
                        "latitude": lat,
                        "longitude": lon,
                    }])
                    self.df_vgeo_cache = pd.concat([self.df_vgeo_cache, novo_reg]).drop_duplicates(subset=["rodovia", "km", "uf"], keep="last")
                    self._salvar_vgeo_cache()
                    return lat, lon
        except Exception:
            pass

        return None, None

    def _carregar_base_der(self) -> pd.DataFrame:
        caminhos = list(self.raw_dir.glob("*der*.csv")) + [Path("radares_dersp.csv")]
        caminho = next((p for p in caminhos if p.exists()), None)
        if not caminho:
            return pd.DataFrame()

        try:
            df = pd.read_csv(caminho, sep=";", dtype=str)
            df.columns = [re.sub(r"\s+", " ", c).strip() for c in df.columns]
            df["rodovia_pad"] = df["SP"].apply(self._padronizar_rodovia)
            df["km_num"] = pd.to_numeric(df["km Inicial"].str.replace(",", "."), errors="coerce")
            df["lat_num"] = pd.to_numeric(df["Latitude"].str.replace(",", "."), errors="coerce")
            df["lon_num"] = pd.to_numeric(df["Longitude"].str.replace(",", "."), errors="coerce")
            df["Serie_clean"] = df["Série"].fillna("").str.strip().str.upper()
            df["serie_norm"] = df["Serie_clean"].apply(self._normalizar_serie)
            df_valid = df.dropna(subset=["lat_num", "lon_num"]).copy()
            print(f"Base DER/SP carregada: {len(df_valid)} equipamentos.")
            return df_valid
        except Exception as e:
            print(f"Erro ao ler DER/SP: {e}")
            return pd.DataFrame()

    def _carregar_base_dnit_sp(self) -> pd.DataFrame:
        cache_sp = self.geocoded_dir / "radares_dnit_sp.csv"
        arquivos_xlsx = [
            p for p in (list(self.raw_dir.glob("*.xlsx")) + list(Path(".").glob("*pncv*.xlsx")))
            if "medidores" not in p.name.lower()
        ]
        arquivo_alvo = arquivos_xlsx[0] if arquivos_xlsx else None

        if arquivo_alvo and Path(arquivo_alvo).exists():
            try:
                df = pd.read_excel(arquivo_alvo)
                if "UF" in df.columns and "Coordenadas (Lat/Long)" in df.columns:
                    df_sp = df[df["UF"].astype(str).str.strip().str.upper() == "SP"].copy()
                    df_sp["rodovia_pad"] = df_sp["Rodovia"].apply(
                        lambda v: f"BR-{int(v):03d}" if pd.notna(v) and str(v).strip().isdigit() else f"BR-{str(v).strip()}"
                    )
                    df_sp["km_num"] = pd.to_numeric(df_sp["Km"].astype(str).str.replace(",", "."), errors="coerce")
                    lats, lons = [], []
                    for coord in df_sp["Coordenadas (Lat/Long)"]:
                        if pd.notna(coord) and "/" in str(coord):
                            p = str(coord).split("/")
                            lats.append(float(p[0].strip().replace(",", ".")))
                            lons.append(float(p[1].strip().replace(",", ".")))
                        else:
                            lats.append(None)
                            lons.append(None)
                    df_sp["lat_num"] = lats
                    df_sp["lon_num"] = lons
                    df_sp = df_sp.dropna(subset=["lat_num", "lon_num"]).copy()
                    if not df_sp.empty:
                        df_sp.to_csv(cache_sp, index=False, encoding="utf-8-sig")
                        print(f"Base DNIT (SP) carregada do Excel: {len(df_sp)} registros.")
                        return df_sp
            except Exception as e:
                print(f"Aviso ao ler Excel DNIT ({e}). Usando base oficial DNIT SP integrada.")

        df_oficial = pd.DataFrame(
            RADARES_DNIT_SP_OFICIAL,
            columns=["rodovia_pad", "km_num", "Municipio", "lat_num", "lon_num"]
        )
        df_oficial.to_csv(cache_sp, index=False, encoding="utf-8-sig")
        print(f"Base DNIT (SP) carregada: {len(df_oficial)} equipamentos federais.")
        return df_oficial

    def _carregar_base_antt_sp(self) -> pd.DataFrame:
        cache_antt = self.geocoded_dir / "radares_antt_sp.csv"
        if cache_antt.exists():
            try:
                df_c = pd.read_csv(cache_antt)
                if not df_c.empty:
                    print(f"Base ANTT (SP) carregada do cache: {len(df_c)} registros.")
                    return df_c
            except Exception:
                pass

        arquivos_csv = [
            p for p in (list(self.raw_dir.glob("*.csv")) + list(Path(".").glob("*radares*.csv")))
            if "der" not in p.name.lower() and "cache" not in p.name.lower() and "dnit" not in p.name.lower()
        ]
        arquivo_alvo = arquivos_csv[0] if arquivos_csv else None

        if not arquivo_alvo or not Path(arquivo_alvo).exists():
            return pd.DataFrame()

        try:
            try:
                df = pd.read_csv(arquivo_alvo, sep=";", encoding="utf-8", dtype=str)
            except UnicodeDecodeError:
                df = pd.read_csv(arquivo_alvo, sep=";", encoding="latin1", dtype=str)

            df.columns = [c.strip() for c in df.columns]
            col_uf = next((c for c in df.columns if c.lower() == "uf"), "uf")
            df_sp = df[df[col_uf].astype(str).str.strip().str.upper() == "SP"].copy()

            df_sp["rodovia_pad"] = df_sp["rodovia"].apply(self._padronizar_rodovia)
            df_sp["km_num"] = pd.to_numeric(df_sp["km_m"].astype(str).str.replace(",", "."), errors="coerce")
            df_sp["lat_num"] = pd.to_numeric(df_sp["latitude"].astype(str).str.replace(",", "."), errors="coerce")
            df_sp["lon_num"] = pd.to_numeric(df_sp["longitude"].astype(str).str.replace(",", "."), errors="coerce")
            df_sp = df_sp.dropna(subset=["km_num", "lat_num", "lon_num"]).copy()

            kms_remover = []
            for (rod, lat, lon), grp in df_sp.groupby(["rodovia_pad", "lat_num", "lon_num"]):
                if grp["km_num"].max() - grp["km_num"].min() > 1.0:
                    km_correto = grp["km_num"].max()
                    for idx_row, r_row in grp.iterrows():
                        if abs(r_row["km_num"] - km_correto) > 0.5:
                            kms_remover.append(idx_row)
            if kms_remover:
                df_sp = df_sp.drop(index=kms_remover)

            df_sp.to_csv(cache_antt, index=False, encoding="utf-8-sig")
            print(f"Base ANTT (SP) carregada: {len(df_sp)} registros válidos.")
            return df_sp
        except Exception:
            return pd.DataFrame()

    def buscar_coordenada_rodovia(self, num_serie: str, rodovia: str | None, km_val: float | None, municipio: str = "") -> tuple[float | None, float | None, str | None]:
        if not rodovia:
            return None, None, None

        rod_clean = str(rodovia).strip().upper()
        s_raw = str(num_serie or "").strip().upper()
        s_norm = self._normalizar_serie(s_raw)

        # 1. DER/SP
        if not self.df_der.empty:
            sub_der = self.df_der[self.df_der["rodovia_pad"] == rod_clean]
            if not sub_der.empty:
                if s_raw:
                    m_s = sub_der[(sub_der["Serie_clean"] == s_raw) | (sub_der["serie_norm"] == s_norm)]
                    if not m_s.empty:
                        if km_val is not None and pd.notna(km_val):
                            m_s = m_s.assign(diff=(m_s["km_num"] - km_val).abs()).sort_values("diff")
                            if m_s.iloc[0]["diff"] <= 1.5:
                                r = m_s.iloc[0]
                                return float(r["lat_num"]), float(r["lon_num"]), "DER_SP_SERIE"
                        else:
                            r = m_s.iloc[0]
                            return float(r["lat_num"]), float(r["lon_num"]), "DER_SP_SERIE"

                if km_val is not None and pd.notna(km_val):
                    m_k = sub_der.assign(diff=(sub_der["km_num"] - km_val).abs()).sort_values("diff")
                    if not m_k.empty and m_k.iloc[0]["diff"] <= 0.15:
                        r = m_k.iloc[0]
                        return float(r["lat_num"]), float(r["lon_num"]), "DER_SP_RODOVIA_KM"

        # 2. DNIT SP (PNCV - Radares Ativos)
        if not self.df_dnit_sp.empty and rod_clean.startswith("BR-") and km_val is not None and pd.notna(km_val):
            sub_dnit = self.df_dnit_sp[self.df_dnit_sp["rodovia_pad"] == rod_clean]
            if not sub_dnit.empty:
                m_dn = sub_dnit.assign(diff=(sub_dnit["km_num"] - km_val).abs()).sort_values("diff")
                if not m_dn.empty and m_dn.iloc[0]["diff"] <= 0.10:
                    r = m_dn.iloc[0]
                    return float(r["lat_num"]), float(r["lon_num"]), "DNIT_RODOVIA_KM"

        # 3. ANTT SP (BR-116 e BR-101)
        if not self.df_antt_sp.empty and rod_clean.startswith("BR-") and km_val is not None and pd.notna(km_val):
            sub_antt = self.df_antt_sp[self.df_antt_sp["rodovia_pad"] == rod_clean]
            if not sub_antt.empty:
                candidatos = sub_antt[sub_antt["km_num"].sub(km_val).abs() <= 0.10].copy()
                if not candidatos.empty:
                    candidatos["dist_muni"] = candidatos.apply(lambda r: self._distancia_centro_muni(r["lat_num"], r["lon_num"], municipio), axis=1)
                    candidatos["diff_km"] = (candidatos["km_num"] - km_val).abs()
                    validos = candidatos[candidatos["dist_muni"] <= 12.0].sort_values(["diff_km", "dist_muni"])
                    if not validos.empty:
                        r = validos.iloc[0]
                        return float(r["lat_num"]), float(r["lon_num"]), "ANTT_RODOVIA_KM"

        # 4. DNIT VGEO (Espacialização Geodésica Oficial via SGPLAN)
        if rod_clean.startswith("BR-") and km_val is not None and pd.notna(km_val):
            lat_vgeo, lon_vgeo = self._consultar_vgeo_dnit(rod_clean, km_val, uf="SP")
            if lat_vgeo is not None and lon_vgeo is not None:
                return lat_vgeo, lon_vgeo, "DNIT_VGEO_OFICIAL"

        # 5. Marcos Quilométricos (Fallback para rodovias estaduais sem cadastro)
        if rod_clean in MARCOS_RODOVIAS_SP and km_val is not None and pd.notna(km_val):
            marcos = sorted(MARCOS_RODOVIAS_SP[rod_clean], key=lambda x: x[0])
            kms = [m[0] for m in marcos]
            lats = [m[1] for m in marcos]
            lons = [m[2] for m in marcos]
            return round(float(np.interp(km_val, kms, lats)), 7), round(float(np.interp(km_val, kms, lons)), 7), "RODOVIA_MARCO_KM"

        return None, None, None