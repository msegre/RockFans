"""Light platform for Tuya Ceiling Fan."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_NAME,
    DPS_LIGHT_ON,
    DPS_BRIGHTNESS,
    DPS_COLOR_TEMP,
    DPS_LIGHT_MODE,
    LIGHT_MODE_WHITE,
)
from .coordinator import TuyaFanCoordinator

_LOGGER = logging.getLogger(__name__)

# Tuya brightness 0–1000 ↔ HA brightness 0–255
_TUYA_BRIGHT_MAX = 1000
_HA_BRIGHT_MAX   = 255

# Tuya color temp 0 (warm) – 1000 (cool)
# HA uses Kelvin; we map Tuya 0–1000 to 2700–6500 K
_KELVIN_WARM = 2700
_KELVIN_COOL = 6500


def _tuya_to_ha_brightness(tuya_val: int) -> int:
    return round(tuya_val / _TUYA_BRIGHT_MAX * _HA_BRIGHT_MAX)


def _ha_to_tuya_brightness(ha_val: int) -> int:
    return round(ha_val / _HA_BRIGHT_MAX * _TUYA_BRIGHT_MAX)


def _tuya_to_kelvin(tuya_val: int) -> int:
    """Tuya 0 = warmest (2700 K), 1000 = coolest (6500 K)."""
    frac = tuya_val / _TUYA_BRIGHT_MAX
    return round(_KELVIN_WARM + frac * (_KELVIN_COOL - _KELVIN_WARM))


def _kelvin_to_tuya(kelvin: int) -> int:
    frac = (kelvin - _KELVIN_WARM) / (_KELVIN_COOL - _KELVIN_WARM)
    return round(max(0.0, min(1.0, frac)) * _TUYA_BRIGHT_MAX)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TuyaFanCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TuyaCeilingFanLight(coordinator, entry)])


class TuyaCeilingFanLight(CoordinatorEntity[TuyaFanCoordinator], LightEntity):
    """Representation of the light kit on a Tuya ceiling fan."""

    _attr_has_entity_name = True
    _attr_name = "Light"
    _attr_color_mode = ColorMode.COLOR_TEMP
    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}
    _attr_min_color_temp_kelvin = _KELVIN_WARM
    _attr_max_color_temp_kelvin = _KELVIN_COOL

    def __init__(self, coordinator: TuyaFanCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_light"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data[CONF_NAME],
            manufacturer="Tuya",
            model="Ceiling Fan",
        )

    @property
    def is_on(self) -> bool | None:
        dps = self.coordinator.data
        if dps is None:
            return None
        return bool(dps.get(DPS_LIGHT_ON))

    @property
    def brightness(self) -> int | None:
        dps = self.coordinator.data
        if dps is None:
            return None
        tuya_bright = dps.get(DPS_BRIGHTNESS)
        if tuya_bright is not None:
            return _tuya_to_ha_brightness(int(tuya_bright))
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        dps = self.coordinator.data
        if dps is None:
            return None
        tuya_temp = dps.get(DPS_COLOR_TEMP)
        if tuya_temp is not None:
            return _tuya_to_kelvin(int(tuya_temp))
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        dps: dict = {
            DPS_LIGHT_ON:   True,
            DPS_LIGHT_MODE: LIGHT_MODE_WHITE,
        }
        if ATTR_BRIGHTNESS in kwargs:
            dps[DPS_BRIGHTNESS] = _ha_to_tuya_brightness(kwargs[ATTR_BRIGHTNESS])
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            dps[DPS_COLOR_TEMP] = _kelvin_to_tuya(kwargs[ATTR_COLOR_TEMP_KELVIN])
        await self.coordinator.async_set_dps(dps)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_dps({DPS_LIGHT_ON: False})
