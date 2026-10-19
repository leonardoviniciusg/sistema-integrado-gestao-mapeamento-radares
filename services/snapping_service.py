import math
import os
from pathlib import Path
import googlemaps
import pandas as pd
import requests
import urllib3

from config import GEOCODED_DIR

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SnappingService:
    # Endpoint público do Open Source Routing Machine (OSRM)
    OSRM_NEAREST_URL = "http://router.project-osrm.org/nearest/v1/driving/{lon},{lat}"

    def __init__(self, api_key: str | None = None, cache_dir: Path = GEOCODED_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "snapping_cache.csv"
        self.cache_df = self._carregar_cache()

        # Google Maps Client para fallback
        chave = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        self.gmaps = googlemaps.Client(key=chave) if chave else None

    def _carregar_cache(self) -> pd.DataFrame:
        if self.cache_file.exists():
            try:
                return pd.read_csv(self.cache_file)
            except Exception:
                pass
        return pd.DataFrame(columns=["orig_lat", "orig_lon", "snap_lat", "snap_lon", "dist_metros", "origem"])

    def _salvar_cache(self):
        try:
            self.cache_df.drop_duplicates(subset=["orig_lat", "orig_lon"], keep="last").to_csv(self.cache_file, index=False)
        except Exception:
            pass

    @staticmethod
    def _distancia_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        dlat = (lat2 - lat1) * 111139.0
        dlon = (lon2 - lon1) * 102000.0
        return math.hypot(dlat, dlon)

    def _snap_osrm(self, lat: float, lon: float) -> tuple[float | None, float | None, float | None]:
        url = self.OSRM_NEAREST_URL.format(lon=lon, lat=lat)
        headers = {"User-Agent": "Projeto_PSIE_Radares/1.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and data.get("waypoints"):
                    wp = data["waypoints"][0]
                    snap_lon, snap_lat = wp["location"]
                    dist = float(wp.get("distance", self._distancia_metros(lat, lon, snap_lat, snap_lon)))
                    return float(snap_lat), float(snap_lon), dist
        except Exception:
            pass
        return None, None, None

    def _snap_google_roads(self, lat: float, lon: float) -> tuple[float | None, float | None, float | None]:
        if not self.gmaps:
            return None, None, None
        try:
            res = self.gmaps.snap_to_roads(path=[(lat, lon)])
            if res:
                loc = res[0].get("location", {})
                s_lat = float(loc["latitude"])
                s_lon = float(loc["longitude"])
                dist = self._distancia_metros(lat, lon, s_lat, s_lon)
                return s_lat, s_lon, dist
        except Exception:
            pass
        return None, None, None

    def ajustar_para_eixo_rua(self, lat: float | None, lon: float | None, max_dist_metros: float = 40.0) -> tuple[float, float, bool]:
        """
        Recebe a coordenada de um endereço (fachada/lote) e projeta para o meio da pista.
        Retorna: (nova_lat, nova_lon, ajustou_booleano)
        """
        if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
            return lat, lon, False

        lat_f = round(float(lat), 7)
        lon_f = round(float(lon), 7)

        # 1. Verifica cache local
        if not self.cache_df.empty:
            m = self.cache_df[
                (self.cache_df["orig_lat"].round(6) == round(lat_f, 6)) &
                (self.cache_df["orig_lon"].round(6) == round(lon_f, 6))
            ]
            if not m.empty:
                r = m.iloc[0]
                return float(r["snap_lat"]), float(r["snap_lon"]), True

        # 2. Tenta OSRM (OpenStreetMap - gratuito)
        s_lat, s_lon, dist = self._snap_osrm(lat_f, lon_f)
        origem = "OSRM"

        # 3. Fallback: Google Roads API
        if s_lat is None:
            s_lat, s_lon, dist = self._snap_google_roads(lat_f, lon_f)
            origem = "GOOGLE_ROADS"

        # 4. Validação de distância de segurança (evita pular para via errada)
        if s_lat is not None and s_lon is not None and dist is not None and dist <= max_dist_metros:
            novo_reg = pd.DataFrame([{
                "orig_lat": lat_f,
                "orig_lon": lon_f,
                "snap_lat": round(s_lat, 7),
                "snap_lon": round(s_lon, 7),
                "dist_metros": round(dist, 1),
                "origem": origem
            }])
            self.cache_df = pd.concat([self.cache_df, novo_reg]).drop_duplicates(subset=["orig_lat", "orig_lon"], keep="last")
            self._salvar_cache()
            return round(s_lat, 7), round(s_lon, 7), True

        # Se ultrapassar a distância segura ou falhar, mantém a coordenada original
        return lat_f, lon_f, False