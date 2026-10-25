"""Cliente mínimo de la API de Tuya para el historial de mapas de la aspiradora (solo lectura)."""
import hashlib
import hmac
import time

import requests

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
TIMEOUT = 10
DOWNLOAD_TIMEOUT = 30


class TuyaError(Exception):
    """La API de Tuya ha devuelto un error."""


def sign(client_id: str, secret: str, method: str, path: str, t: str, token: str = "") -> str:
    """Firma HMAC-SHA256 de las peticiones de Tuya (la misma que ya funciona en la integración actual)."""
    string_to_sign = method + "\n" + EMPTY_SHA256 + "\n\n" + path
    msg = client_id + token + t + string_to_sign
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest().upper()


class TuyaMapClient:
    def __init__(self, server: str, client_id: str, secret: str, device_id: str) -> None:
        self.server = server.rstrip("/")
        self.client_id = client_id
        self.secret = secret
        self.device_id = device_id

    def _request(self, path: str, token: str = "") -> dict:
        t = str(int(time.time() * 1000))
        headers = {
            "sign_method": "HMAC-SHA256",
            "client_id": self.client_id,
            "t": t,
            "sign": sign(self.client_id, self.secret, "GET", path, t, token),
        }
        if token:
            headers["access_token"] = token
        data = requests.get(self.server + path, headers=headers, timeout=TIMEOUT).json()
        if not data.get("success"):
            raise TuyaError(data.get("msg") or str(data))
        return data["result"]

    def token(self) -> str:
        return self._request("/v1.0/token?grant_type=1")["access_token"]

    def latest_map_id(self, token: str) -> int:
        """Id del mapa más reciente del historial (lista 'pic'), por campo 'time'."""
        path = (
            "/v1.0/users/sweepers/file/%s/list?file_type=pic&page_no=1&page_size=20"
            % self.device_id
        )
        datas = self._request(path, token).get("datas") or []
        if not datas:
            raise TuyaError("El historial no tiene mapas para este dispositivo")
        return max(datas, key=lambda d: d.get("time", 0))["id"]

    def download_url(self, token: str, file_id: int) -> str:
        path = "/v1.0/users/sweepers/file/%s/download?id=%s" % (self.device_id, file_id)
        return self._request(path, token)["app_map"]

    def fetch_latest_map(self) -> bytes:
        """Descarga el archivo del mapa más reciente (mapa y ruta de esa limpieza)."""
        token = self.token()
        url = self.download_url(token, self.latest_map_id(token))
        response = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
        response.raise_for_status()
        return response.content
