"""Decodificador para mapas con cabecera de versión 2 (Cecotec Conga 8290).

Verificado con un mapa real de la Conga 8290: cabecera de 24 bytes, bloque LZ4
de longitud comprimida indicada en la cabecera, cuadrícula width*height y, a
continuación, la tabla de habitaciones (mismo formato que v1).

Codificación de celdas observada en ese mapa:
  0xE0                -> sin explorar / fondo
  0xF1                -> pared u obstáculo
  (ID << 3) | 7       -> celda de la habitación con ese ID (0x0F = ID 1, ...)
Cualquier otro valor (p. ej. 0xE7) se pinta como "desconocido".
"""
import logging
import numpy as np

from .pylz4 import uncompress
from .const import default_colors
from .v1 import decode_roomArr

_LOGGER = logging.getLogger(__name__)

UNKNOWN_COLOR = (20, 20, 20)
_BG = 0xE0
_WALL = 0xF1


def decode_v2(data: str, header: dict):
    """data: archivo completo en hexadecimal. Rellena header['roominfo']."""
    area = header["width"] * header["height"]
    compressed_len = header["compressafterlenght"]
    compressed = bytes.fromhex(data[48 : 48 + compressed_len * 2])
    if len(compressed) != compressed_len:
        raise ValueError(
            "v2 map truncated: expected %d compressed bytes, got %d"
            % (compressed_len, len(compressed))
        )

    raw = uncompress(compressed)
    if len(raw) != header["totalcount"]:
        _LOGGER.warning(
            "v2 map: decompressed size %d differs from header (%d)",
            len(raw), header["totalcount"],
        )
    if len(raw) < area:
        raise ValueError("v2 map too small for %dx%d" % (header["width"], header["height"]))

    try:
        header["roominfo"] = decode_roomArr(raw[area:])
    except Exception as err:  # tabla de habitaciones ausente o con otro formato
        _LOGGER.debug("No rooms in v2 map: %s", err)
        header["roominfo"] = []

    return raw[:area]


def to_array_v2(
    pixellist: list, width: int, height: int, rooms: list, colors: dict
) -> np.ndarray:
    if colors == {}:
        colors["bg_color"] = default_colors.v1.get("bg_color")
        colors["wall_color"] = default_colors.v1.get("wall_color")
        for i in rooms:
            colors["room_color_" + str(i["ID"])] = default_colors.v1.get("room_color")

    bg = colors.get("bg_color", default_colors.v1["bg_color"])
    wall = colors.get("wall_color", default_colors.v1["wall_color"])
    room_default = default_colors.v1["room_color"]

    lut = np.full((256, 3), UNKNOWN_COLOR, dtype=np.uint8)
    lut[_BG] = bg
    lut[_WALL] = wall
    for room in rooms:
        value = (room["ID"] << 3) | 7
        if value < 256:
            lut[value] = colors.get("room_color_" + str(room["ID"]), room_default)

    grid = np.frombuffer(bytes(pixellist), dtype=np.uint8).reshape(height, width)
    return lut[grid]


ROUTE_HEADER_LEN = 13


def decode_route_v2(raw: bytes, layout_len: int):
    """Ruta de la limpieza guardada a continuación del mapa en el mismo archivo.

    Formato verificado con un archivo real de la Conga 8290 (mismo que usa la
    librería de Tuya @ray-js/robot-protocol): tras el mapa (layout_len bytes) va
    una cabecera de 13 bytes (versión, id de ruta, flag de inicio, tipo, número de
    puntos [4 bytes], dirección [2], longitud comprimida [2]) y los puntos como
    pares de enteros de 16 bits big endian. Si la longitud comprimida es mayor
    que 0, los puntos van comprimidos con LZ4.

    El último bit de cada coordenada es el tipo de punto:
      x0 y0 -> normal, x1 y0 -> carga, x0 y1 -> desplazamiento, x1 y1 -> mopa.
    Coordenadas en celdas respecto al origen del mapa:
      columna = originx/10 + x ; fila = originy/10 + y   (y ya viene con el signo invertido)
    """
    if len(raw) < layout_len + ROUTE_HEADER_LEN:
        return None
    h = raw[layout_len : layout_len + ROUTE_HEADER_LEN]
    count = int.from_bytes(h[5:9], "big")
    direction = int.from_bytes(h[9:11], "big")
    comp_len = int.from_bytes(h[11:13], "big")
    if count == 0 or count > 2_000_000:
        return None
    body = raw[layout_len + ROUTE_HEADER_LEN :]
    if comp_len > 0:
        data = bytes(uncompress(body[:comp_len]))
    else:
        data = body[: count * 4]
    if len(data) < count * 4:
        raise ValueError("route truncated: %d points expected, %d bytes" % (count, len(data)))

    arr = np.frombuffer(data[: count * 4], dtype=">u2").reshape(count, 2).astype(np.int64)
    tipo_x = arr[:, 0] & 1
    tipo_y = arr[:, 1] & 1
    ux = arr[:, 0] & ~1
    uy = arr[:, 1] & ~1
    # misma conversion a entero con signo que la libreria de Tuya (resta 65535)
    sx = np.where(ux > 32767, ux - 65535, ux)
    sy = np.where(uy > 32767, uy - 65535, uy)
    xs = sx / 10.0
    ys = -(sy / 10.0)
    kinds = np.where(tipo_x == 0, np.where(tipo_y == 0, 0, 2), np.where(tipo_y == 0, 1, 3))
    # 0 normal, 1 carga, 2 desplazamiento, 3 mopa
    return {"count": count, "direction": direction, "x": xs, "y": ys, "kind": kinds}
