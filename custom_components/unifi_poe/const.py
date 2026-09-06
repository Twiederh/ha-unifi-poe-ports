"""Constants for the UniFi PoE Ports integration."""

from homeassistant.const import Platform

DOMAIN = "unifi_poe"

CONF_SITE = "site"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_PORT = 443
DEFAULT_SITE = "default"
DEFAULT_VERIFY_SSL = False

# Wie oft der UniFi-Controller nach Port-/PoE-Status abgefragt wird.
SCAN_INTERVAL_SECONDS = 30

# PoE-Modus, der beim Wiedereinschalten verwendet wird, solange noch kein
# anderer Modus für den Port beobachtet wurde.
DEFAULT_ON_POE_MODE = "auto"
OFF_POE_MODE = "off"

PLATFORMS = [Platform.SWITCH]
