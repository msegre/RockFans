"""Fan platform for Tuya Ceiling Fan."""
from __future__ import annotations

import logging
import math
from typing import Any, Optional

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_NAME,
    DPS_FAN_ON,
    DPS_FAN_SPEED,
    DPS_FAN_SPEED_NUM,
    DPS_FAN_DIRECTION,
    FAN_SPEED_COUNT,
    FAN_DIRECTION_FORWARD,
    FAN_DIRECTION_REVERSE,
)
from .coordinator import TuyaFanCoordinator

_LOGGER = logging.getLogger(__name__)

# HA percentage → level_N mapping
# percentage_step = 100 / FAN_SPEED_COUNT = ~16.67
SPEED_PERCENTAGE_STEP = 100 / FAN_SPEED_COUNT


def _pct_to_level(percentage: int) -> int:
    """Convert HA percentage (1–100) to Tuya level (1–6)."""
    level = math.ceil(percentage / SPEED_PERCENTAGE_STEP)
    return max(1, min(FAN_SPEED_COUNT, level))


def _level_to_pct(level: int) -> int:
    """Convert Tuya level (1–6) to HA percentage."""
    return round(level * SPEED_PERCENTAGE_STEP)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TuyaFanCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TuyaCeilingFan(coordinator, entry)])


class TuyaCeilingFan(CoordinatorEntity[TuyaFanCoordinator], FanEntity):
    """Representation of a Tuya ceiling fan motor."""

    _attr_has_entity_name = True
    _attr_name = "Fan"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.DIRECTION
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = FAN_SPEED_COUNT

    def __init__(self, coordinator: TuyaFanCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_fan"
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
        return bool(dps.get(DPS_FAN_ON))

    @property
    def percentage(self) -> int | None:
        dps = self.coordinator.data
        if dps is None:
            return None
        level = dps.get(DPS_FAN_SPEED_NUM)
        if level is None:
            # fall back to parsing the enum value
            speed_enum = dps.get(DPS_FAN_SPEED, "")
            if speed_enum.startswith("level_"):
                try:
                    level = int(speed_enum.split("_")[1])
                except ValueError:
                    return None
        if level is not None:
            return _level_to_pct(int(level))
        return None

    @property
    def current_direction(self) -> str | None:
        dps = self.coordinator.data
        if dps is None:
            return None
        direction = dps.get(DPS_FAN_DIRECTION, "")
        if direction == FAN_DIRECTION_FORWARD:
            return "forward"
        if direction == FAN_DIRECTION_REVERSE:
            return "reverse"
        return None

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any
    ) -> None:
        dps: dict = {DPS_FAN_ON: True}
        if percentage is not None:
            level = _pct_to_level(percentage)
            dps[DPS_FAN_SPEED]     = f"level_{level}"
            dps[DPS_FAN_SPEED_NUM] = level
        await self.coordinator.async_set_dps(dps)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_dps({DPS_FAN_ON: False})

    async def async_set_percentage(self, percentage: int) -> None:
        level = _pct_to_level(percentage)
        await self.coordinator.async_set_dps(
            {
                DPS_FAN_SPEED:     f"level_{level}",
                DPS_FAN_SPEED_NUM: level,
            }
        )

    async def async_set_direction(self, direction: str) -> None:
        tuya_dir = FAN_DIRECTION_FORWARD if direction == "forward" else FAN_DIRECTION_REVERSE
        await self.coordinator.async_set_dps({DPS_FAN_DIRECTION: tuya_dir})
