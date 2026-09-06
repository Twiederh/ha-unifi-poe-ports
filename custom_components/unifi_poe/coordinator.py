"""DataUpdateCoordinator for the UniFi PoE Ports integration."""

from __future__ import annotations

from datetime import timedelta
import logging
import ssl

import aiohttp
from aiounifi.controller import Controller
from aiounifi.errors import AiounifiException, LoginRequired, RequestError, Unauthorized
from aiounifi.models.configuration import Configuration
from aiounifi.models.device import DeviceSetPoePortModeRequest
from aiounifi.models.port import Port

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_SITE,
    CONF_VERIFY_SSL,
    DEFAULT_ON_POE_MODE,
    OFF_POE_MODE,
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class UnifiPoeCoordinator(DataUpdateCoordinator[None]):
    """Fragt regelmäßig den UniFi-Controller nach dem PoE-Zustand aller Ports ab."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Coordinator einrichten."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry

        session = async_get_clientsession(hass, verify_ssl=False)
        ssl_context: ssl.SSLContext | bool = False
        if entry.data.get(CONF_VERIFY_SSL, False):
            ssl_context = ssl.create_default_context()

        config = Configuration(
            session,
            entry.data[CONF_HOST],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            port=entry.data[CONF_PORT],
            site=entry.data.get(CONF_SITE, "default"),
            ssl_context=ssl_context,
        )
        self.controller = Controller(config)

        # Merkt sich je Port den letzten aktiven (nicht "off") PoE-Modus,
        # damit ein Switch beim Einschalten den richtigen Modus wiederherstellt.
        self.last_active_poe_mode: dict[str, str] = {}

    async def async_setup(self) -> None:
        """Login und ersten Datenabruf durchführen.

        Ruft bewusst nicht Controller.initialize() auf: diese Komfortmethode
        ist je nach aiounifi-Version nicht (mehr) vorhanden. Stattdessen wird
        - genau wie in der offiziellen Home-Assistant-UniFi-Integration -
        nur login() plus ein gezielter devices.update() verwendet; das reicht,
        um über die interne Ports-Subscription auch alle Port-Daten zu laden.
        """
        try:
            await self.controller.login()
            await self.controller.devices.update()
        except (Unauthorized, LoginRequired) as err:
            raise ConfigEntryAuthFailed("Anmeldung am UniFi-Controller fehlgeschlagen") from err
        except (RequestError, aiohttp.ClientError, TimeoutError) as err:
            raise ConfigEntryNotReady(f"UniFi-Controller nicht erreichbar: {err}") from err
        except AiounifiException as err:
            raise ConfigEntryNotReady(f"Fehler beim Verbinden mit UniFi-Controller: {err}") from err

        self._remember_active_modes()

    async def _async_update_data(self) -> None:
        """Aktuelle Geräte-/Portdaten vom Controller holen."""
        try:
            await self.controller.devices.update()
        except (Unauthorized, LoginRequired) as err:
            raise ConfigEntryAuthFailed("Anmeldung am UniFi-Controller verloren") from err
        except (RequestError, aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"UniFi-Controller nicht erreichbar: {err}") from err
        except AiounifiException as err:
            raise UpdateFailed(f"Fehler beim Abrufen der UniFi-Daten: {err}") from err

        self._remember_active_modes()

    def _remember_active_modes(self) -> None:
        """Aktuell aktive PoE-Modi für spätere "Einschalten"-Befehle merken."""
        for obj_id, port in self.controller.ports.items():
            mode = port.poe_mode
            if mode and mode != OFF_POE_MODE:
                self.last_active_poe_mode[obj_id] = mode

    def get_port(self, obj_id: str) -> Port | None:
        """Portobjekt anhand seiner ID (mac_portidx) liefern."""
        return self.controller.ports.get(obj_id)

    async def async_set_poe_mode(self, obj_id: str, device_mac: str, port_idx: int, mode: str) -> None:
        """PoE-Modus für einen Port setzen."""
        device = self.controller.devices[device_mac]
        await self.controller.request(
            DeviceSetPoePortModeRequest.create(device, port_idx=port_idx, mode=mode)
        )
        if mode != OFF_POE_MODE:
            self.last_active_poe_mode[obj_id] = mode
        await self.async_request_refresh()

    def resolve_on_mode(self, obj_id: str) -> str:
        """Modus bestimmen, der beim Einschalten eines Ports verwendet wird."""
        return self.last_active_poe_mode.get(obj_id, DEFAULT_ON_POE_MODE)
