"""Mapa de la aspiradora: imagen con la ruta de la última limpieza.

Es la única parte que usa la nube de Tuya (descarga del archivo del mapa). Se
actualiza cada hora; el resto de entidades siguen siendo locales.
"""
import logging
from datetime import timedelta
from io import BytesIO

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import CONF_DEVICE_ID, CONF_MAP_CLIENT_ID, CONF_MAP_SECRET, CONF_MAP_SERVER, DOMAIN
from .mapa.map_core import parse_map, render_map
from .mapa.tuya_api import TuyaMapClient

_LOGGER = logging.getLogger(__name__)
REFRESH_INTERVAL = timedelta(hours=1)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([CongaMapImage(hass, entry)])


class CongaMapImage(ImageEntity):
    _attr_has_entity_name = True
    _attr_name = "Mapa"
    _attr_content_type = "image/png"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass)
        self._attr_unique_id = f"{entry.entry_id}_mapa"
        self._png: bytes | None = None
        self._client = TuyaMapClient(
            entry.data.get(CONF_MAP_SERVER, "https://openapi.tuyaeu.com"),
            entry.data[CONF_MAP_CLIENT_ID],
            entry.data[CONF_MAP_SECRET],
            entry.data[CONF_DEVICE_ID],
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_time_interval(self.hass, self._scheduled_refresh, REFRESH_INTERVAL)
        )
        self.hass.async_create_background_task(self._refresh(), f"{DOMAIN}_mapa_inicial")

    async def _scheduled_refresh(self, _now) -> None:
        await self._refresh()

    def _build_png(self) -> bytes:
        """Trabajo bloqueante (red, decodificado y dibujado): se ejecuta fuera del bucle."""
        raw = self._client.fetch_latest_map()
        image = render_map(parse_map(raw))
        buffer = BytesIO()
        image.save(buffer, "PNG")
        return buffer.getvalue()

    async def _refresh(self) -> None:
        try:
            png = await self.hass.async_add_executor_job(self._build_png)
        except Exception as err:  # la imagen anterior se mantiene si falla
            _LOGGER.warning("No se pudo actualizar el mapa: %s", err)
            return
        self._png = png
        self._attr_image_last_updated = dt_util.utcnow()
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        return self._png
