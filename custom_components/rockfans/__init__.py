"""Tuya Ceiling Fan integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_IP,
    CONF_NAME,
    PLATFORM_FAN,
    PLATFORM_LIGHT,
)
from .coordinator import TuyaFanCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [PLATFORM_FAN, PLATFORM_LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya Ceiling Fan from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = TuyaFanCoordinator(
        hass=hass,
        name=entry.data[CONF_NAME],
        ip=entry.data[CONF_IP],
        device_id=entry.data[CONF_DEVICE_ID],
        local_key=entry.data[CONF_LOCAL_KEY],
    )

    # Do the first refresh — raises ConfigEntryNotReady on failure
    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
