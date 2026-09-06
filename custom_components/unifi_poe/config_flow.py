"""Config Flow für UniFi PoE Ports."""

from __future__ import annotations

import ssl
from typing import Any

import aiohttp
import voluptuous as vol
from aiounifi.controller import Controller
from aiounifi.errors import AiounifiException, LoginRequired, RequestError, Unauthorized
from aiounifi.models.configuration import Configuration

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_SITE,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_SITE,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SITE, default=DEFAULT_SITE): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


async def _validate_input(hass: Any, data: dict[str, Any]) -> None:
    """Verbindung zum UniFi-Controller mit den eingegebenen Daten testen."""
    session = async_get_clientsession(hass, verify_ssl=False)
    ssl_context: ssl.SSLContext | bool = False
    if data.get(CONF_VERIFY_SSL, False):
        ssl_context = ssl.create_default_context()

    config = Configuration(
        session,
        data[CONF_HOST],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        port=data[CONF_PORT],
        site=data.get(CONF_SITE, DEFAULT_SITE),
        ssl_context=ssl_context,
    )
    controller = Controller(config)
    await controller.login()


class UnifiPoeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config Flow für UniFi PoE Ports."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ersten (und einzigen) Konfigurationsschritt behandeln."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._async_abort_entries_match(
                {CONF_HOST: user_input[CONF_HOST], CONF_SITE: user_input[CONF_SITE]}
            )

            try:
                await _validate_input(self.hass, user_input)
            except (Unauthorized, LoginRequired):
                errors["base"] = "invalid_auth"
            except (RequestError, aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            except AiounifiException:
                errors["base"] = "unknown"
            else:
                title = f"UniFi PoE ({user_input[CONF_HOST]})"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
