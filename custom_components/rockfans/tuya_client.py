"""Tuya client wrapper using tinytuya."""
from __future__ import annotations

import logging
from typing import Any, Optional

import tinytuya

_LOGGER = logging.getLogger(__name__)


class TuyaClient:
    def __init__(self, ip: str, device_id: str, local_key: str,
                 version: float = 3.5, timeout: int = 5) -> None:
        self._ip = ip
        self._device_id = device_id
        self._local_key = local_key
        self._version = version
        self._timeout = timeout

    def _make_device(self) -> tinytuya.OutletDevice:
        dev = tinytuya.OutletDevice(
            dev_id=self._device_id,
            address=self._ip,
            local_key=self._local_key,
            version=self._version,
        )
        dev.set_socketTimeout(self._timeout)
        dev.set_socketRetryLimit(2)
        return dev

    def get_status(self) -> Optional[dict]:
        dev = self._make_device()
        try:
            result = dev.status()
            if isinstance(result, dict) and "dps" in result:
                return result["dps"]
            _LOGGER.debug("Unexpected status response: %s", result)
            return None
        except Exception as exc:
            _LOGGER.error("get_status failed (%s): %s", self._ip, exc)
            return None
        finally:
            dev.close()

    def set_dps(self, dps: dict) -> bool:
        dev = self._make_device()
        try:
            result = dev.set_multiple_values(dps)
            if isinstance(result, dict) and result.get("Error"):
                _LOGGER.warning("set_dps error: %s", result)
                return False
            return True
        except Exception as exc:
            _LOGGER.error("set_dps failed (%s): %s", self._ip, exc)
            return False
        finally:
            dev.close()
