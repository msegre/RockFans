"""DataUpdateCoordinator for Tuya Ceiling Fan."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    POLL_INTERVAL,
    TUYA_VERSION,
    SOCKET_TIMEOUT,
)
from .tuya_client import TuyaClient

_LOGGER = logging.getLogger(__name__)


class TuyaFanCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls a single Tuya ceiling fan and shares state between fan + light entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        ip: str,
        device_id: str,
        local_key: str,
    ) -> None:
        self.client = TuyaClient(
            ip=ip,
            device_id=device_id,
            local_key=local_key,
            version=TUYA_VERSION,
            timeout=SOCKET_TIMEOUT,
        )
        self.device_name = name

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{name}",
            update_interval=timedelta(seconds=POLL_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        dps = await self.hass.async_add_executor_job(self.client.get_status)
        if dps is None:
            raise UpdateFailed(f"No response from {self.device_name}")
        return dps

    async def async_set_dps(self, dps: dict) -> bool:
        """Send a DPS command and immediately refresh coordinator state."""
        ok = await self.hass.async_add_executor_job(self.client.set_dps, dps)
        if ok:
            await self.async_request_refresh()
        return ok
