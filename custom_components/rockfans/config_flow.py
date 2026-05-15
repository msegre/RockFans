"""Config flow for Tuya Ceiling Fan integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_DEVICE_ID, CONF_LOCAL_KEY, CONF_IP
from .tuya_client import TuyaClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_IP): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_LOCAL_KEY): str,
    }
)


class TuyaCeilingFanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Tuya Ceiling Fan."""

    VERSION = 1

   async def async_step_user(
    self, user_input: dict[str, Any] | None = None) -> FlowResult:
    if user_input is not None:
        await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=user_input[CONF_NAME],
            data=user_input,
        )

    return self.async_show_form(
        step_id="user",
        data_schema=STEP_USER_SCHEMA,
        errors={},
    )
