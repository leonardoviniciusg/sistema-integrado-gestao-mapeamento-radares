from datetime import datetime
from pathlib import Path
import pandas as pd
import requests
import urllib3

from config import GEOCODED_DIR

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class VGeoService:
    BASE_URL = "https://servicos.dnit.gov.br/sgplan/apigeo/rotas/espacializarlinha"

    def __init__(self, cache_dir: Path = GEOCODED_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "vgeo_cache.csv"
        self.cache_df = self._carregar_cache()

    def _carregar_cache(self) -> pd.DataFrame:
        if self.cache_file.exists():
            try:
                return pd.read_csv(self.cache_file)
            except Exception:
                pass
        return pd.DataFrame(columns=["rodovia", "km", "uf", "latitude", "longitude"])

    def _salvar_cache(self):
        try:
            self.cache_df.drop_duplicates(subset=["rodovia", "km", "uf"], keep="last").to_csv(self.cache_file, index=False)
        except Exception:
            pass

    def obter_coordenada_km(self, rodovia: str, km_val: float, uf: str = "SP", tipo: str = "B") -> tuple[float | None, float | None]:
        if km_val is None:
            return None, None

        br_num = str(rodovia).replace("BR-", "").replace("BR", "").strip()
        km_arredondado = round(float(km_val), 3)

        # 1. Checa cache local primeiro
        if not self.cache_df.empty:
            match = self.cache_df[
                (self.cache_df["rodovia"] == f"BR-{int(br_num):03d}")
                & (self.cache_df["km"] == km_arredondado)
                & (self.cache_df["uf"] == uf.upper())
            ]
            if not match.empty:
                r = match.iloc[0]
                return float(r["latitude"]), float(r["longitude"])

        # 2. Requisição à API do VGEO
        hoje_str = datetime.now().strftime("%Y-%m-%d")
        kmi = km_arredondado
        kmf = round(kmi + 0.01, 3)  # Janela de 10 metros para espacializar o ponto

        params = {
            "br": br_num,
            "tipo": tipo,
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
            resp = requests.get(self.BASE_URL, params=params, headers=headers, verify=False, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]

                geom = data.get("geometry", {})
                coords = geom.get("coordinates", [])

                # Se for MultiLineString, coords é lista de linhas [[[lon, lat], ...]]
                # Se for LineString, coords é lista de pontos [[lon, lat], ...]
                if coords:
                    primeiro_ponto = coords[0]
                    while isinstance(primeiro_ponto[0], list):
                        primeiro_ponto = primeiro_ponto[0]

                    lon = float(primeiro_ponto[0])
                    lat = float(primeiro_ponto[1])

                    # Salva no cache local
                    novo_reg = pd.DataFrame([{
                        "rodovia": f"BR-{int(br_num):03d}",
                        "km": km_arredondado,
                        "uf": uf.upper(),
                        "latitude": lat,
                        "longitude": lon,
                    }])
                    self.cache_df = pd.concat([self.cache_df, novo_reg]).drop_duplicates(subset=["rodovia", "km", "uf"], keep="last")
                    self._salvar_cache()

                    return lat, lon
        except Exception as e:
            print(f"Aviso VGEO para BR-{br_num} KM {km_val}: {e}")

        return None, None