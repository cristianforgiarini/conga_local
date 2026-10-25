"""Lectura y dibujado del archivo de mapa de la Conga 8290 (formato versión 2).

Verificado con un archivo real: mapa de 144 x 209 celdas, 7 habitaciones y la ruta de
la última limpieza guardada en el mismo archivo (9231 puntos).
"""
import numpy as np
from PIL import Image, ImageDraw

from .decoders.common import decode_header
from .decoders.v2 import decode_route_v2, decode_v2, to_array_v2

DEFAULT_BG = (0, 0, 0)
DEFAULT_WALL = (255, 0, 0)
DEFAULT_PATH = (0, 80, 255)
PALETTE = [
    (235, 165, 220),
    (255, 220, 100),
    (100, 200, 100),
    (250, 0, 200),
    (120, 140, 220),
    (255, 128, 0),
    (100, 220, 180),
    (160, 90, 220),
]


class MapFormatError(Exception):
    """El archivo no tiene el formato de mapa esperado."""


def parse_map(raw: bytes) -> dict:
    """Lee un archivo de mapa: cabecera, habitaciones, rejilla y ruta (si la trae)."""
    header = decode_header(raw.hex()[:48])
    if header.get("version") != [2]:
        raise MapFormatError("Versión de mapa no soportada: %s" % header.get("version"))
    grid = decode_v2(raw.hex(), header)  # también rellena header["roominfo"]
    route = None
    try:
        route = decode_route_v2(raw, 24 + header["compressafterlenght"])
    except Exception:
        route = None  # sin ruta: se muestra solo el mapa
    return {"header": header, "grid": grid, "route": route}


def _room_color(room_id: int) -> tuple:
    return PALETTE[room_id % len(PALETTE)]


def _draw_route(img: Image.Image, parsed: dict, scale: int, path_color: tuple) -> None:
    route = parsed["route"]
    if not route or route["count"] == 0:
        return
    header = parsed["header"]
    ox = header.get("originx", 0) / 10.0
    oy = header.get("originy", 0) / 10.0
    px = (ox + route["x"]) * scale
    py = (oy + route["y"]) * scale
    kinds = route["kind"]
    draw = ImageDraw.Draw(img, "RGBA")

    def tramos(desplazamiento: bool):
        seg = []
        for i in range(len(px)):
            if (kinds[i] == 2) == desplazamiento:
                seg.append((float(px[i]), float(py[i])))
            else:
                if len(seg) >= 2:
                    yield seg
                seg = []
        if len(seg) >= 2:
            yield seg

    # desplazamientos (sin limpiar) finos y translúcidos; la limpieza en color pleno
    for seg in tramos(True):
        draw.line(seg, fill=path_color + (90,), width=max(1, scale // 2))
    for seg in tramos(False):
        draw.line(seg, fill=path_color, width=max(3, scale))

    if header.get("pileX") is not None and header.get("pileY") is not None:
        dx, dy = header["pileX"] / 10.0 * scale, header["pileY"] / 10.0 * scale
        r = max(8, 5 * scale)
        draw.ellipse([dx - r, dy - r, dx + r, dy + r], fill=(0, 255, 0), outline=(255, 255, 255), width=2)

    # último punto de la ruta: donde terminó la limpieza
    rx, ry = float(px[-1]), float(py[-1])
    r = max(6, 4 * scale)
    draw.ellipse([rx - r, ry - r, rx + r, ry + r], fill=(0, 0, 255), outline=(255, 255, 255), width=2)


def render_map(parsed: dict, bg=DEFAULT_BG, wall=DEFAULT_WALL, path=DEFAULT_PATH,
               room_colors: dict | None = None, scale: int | None = None) -> Image.Image:
    """Imagen RGB del mapa con habitaciones, paredes, ruta, base y posición final."""
    header = parsed["header"]
    width, height = header["width"], header["height"]
    rooms = header.get("roominfo", [])
    room_colors = room_colors or {}

    # diccionario nuevo en cada llamada: to_array_v2 lo rellena si viene vacío
    colors = {"bg_color": list(bg), "wall_color": list(wall)}
    for room in rooms:
        rid = room["ID"]
        colors["room_color_%d" % rid] = list(room_colors.get(rid, _room_color(rid)))

    arr = to_array_v2(parsed["grid"], width, height, rooms, colors)
    img = Image.fromarray(arr.astype(np.uint8), "RGB")
    scale = scale or max(1, round(1000 / width))
    img = img.resize((width * scale, height * scale), Image.NEAREST)
    _draw_route(img, parsed, scale, tuple(path))
    return img
