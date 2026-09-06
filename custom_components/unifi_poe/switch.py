"""Switch-Plattform für UniFi PoE Ports."""

from __future__ import annotations

from typing import Any

from aiounifi.interfaces.api_handlers import ItemEvent
from aiounifi.models.port import Port

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OFF_POE_MODE
from .coordinator import UnifiPoeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Switch-Entities für alle PoE-fähigen Ports anlegen."""
    coordinator: UnifiPoeCoordinator = entry.runtime_data
    known_obj_ids: set[str] = set()

    @callback
    def _add_new_ports(*_: Any) -> None:
        new_entities = []
        for obj_id, port in coordinator.controller.ports.items():
            if obj_id in known_obj_ids:
                continue
            if not port.port_poe:
                # Port unterstützt/verwendet kein PoE -> keinen Schalter anlegen.
                continue
            known_obj_ids.add(obj_id)
            new_entities.append(UnifiPoePortSwitch(coordinator, obj_id))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_ports()

    # Neu erkannte Switches/Ports (z.B. nach Adoption eines neuen UniFi-Switches)
    # später ebenfalls automatisch als Entity anlegen.
    entry.async_on_unload(
        coordinator.controller.ports.subscribe(
            lambda event, obj_id: _add_new_ports(), (ItemEvent.ADDED,)
        )
    )


class UnifiPoePortSwitch(CoordinatorEntity[UnifiPoeCoordinator], SwitchEntity):
    """Schalter für den PoE-Zustand eines einzelnen UniFi-Switch-Ports."""

    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_entity_category = None

    def __init__(self, coordinator: UnifiPoeCoordinator, obj_id: str) -> None:
        """Switch-Entity initialisieren."""
        super().__init__(coordinator)
        self._obj_id = obj_id
        self._device_mac, _, port_idx = obj_id.rpartition("_")
        self._port_idx = int(port_idx)

        self._attr_unique_id = f"{obj_id}_poe"

        device = coordinator.controller.devices[self._device_mac]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_mac)},
            name=device.name,
            manufacturer="Ubiquiti",
            model=device.model,
            connections={("mac", self._device_mac)},
        )

    @property
    def _port(self) -> Port | None:
        """Aktuelles Portobjekt vom Coordinator holen."""
        return self.coordinator.get_port(self._obj_id)

    @property
    def available(self) -> bool:
        """Nur verfügbar, solange der Port (noch) existiert."""
        return super().available and self._port is not None

    @property
    def name(self) -> str | None:
        """Name des Schalters = Port-Label aus dem UniFi Network-Controller."""
        if (port := self._port) is not None:
            return port.name
        return f"Port {self._port_idx}"

    @property
    def is_on(self) -> bool:
        """True, wenn PoE für diesen Port aktuell aktiv ist."""
        if (port := self._port) is None:
            return False
        return bool(port.poe_mode) and port.poe_mode != OFF_POE_MODE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Zusätzliche Attribute für Diagnose/Automationen."""
        port = self._port
        return {
            "port_idx": self._port_idx,
            "poe_mode": port.poe_mode if port else None,
            "poe_class": port.poe_class if port else None,
            "poe_power_w": port.poe_power if port else None,
            "switch_name": self.coordinator.controller.devices[self._device_mac].name,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """PoE für diesen Port einschalten."""
        mode = self.coordinator.resolve_on_mode(self._obj_id)
        await self.coordinator.async_set_poe_mode(
            self._obj_id, self._device_mac, self._port_idx, mode
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """PoE für diesen Port ausschalten."""
        await self.coordinator.async_set_poe_mode(
            self._obj_id, self._device_mac, self._port_idx, OFF_POE_MODE
        )
