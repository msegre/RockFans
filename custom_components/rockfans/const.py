"""Constants for the Tuya Ceiling Fan integration."""

DOMAIN = "tuya_ceiling_fan"

# Config entry keys
CONF_DEVICE_ID = "device_id"
CONF_LOCAL_KEY = "local_key"
CONF_IP = "ip"
CONF_NAME = "name"

# DPS codes
DPS_LIGHT_ON      = "20"   # bool   True / False
DPS_LIGHT_MODE    = "21"   # enum   white | colour | music
DPS_BRIGHTNESS    = "22"   # int    0–1000
DPS_COLOR_TEMP    = "23"   # int    0–1000  (0=warm, 1000=cool)
DPS_FAN_DIRECTION = "101"  # enum   forward | reverse
DPS_FAN_SPEED     = "102"  # enum   level_1 … level_6
DPS_COUNTDOWN     = "103"  # enum   cancel
DPS_FAN_SPEED_NUM = "104"  # int    1–6
DPS_FAN_ON        = "105"  # bool   True / False
DPS_FAN_MODE      = "106"  # enum   fresh

# Fan speed constants (HA uses 1–6 percentage steps)
FAN_SPEED_COUNT = 6
FAN_DIRECTION_FORWARD = "forward"
FAN_DIRECTION_REVERSE = "reverse"

# Light mode constants
LIGHT_MODE_WHITE  = "white"
LIGHT_MODE_COLOUR = "colour"
LIGHT_MODE_MUSIC  = "music"

# Platform names
PLATFORM_FAN   = "fan"
PLATFORM_LIGHT = "light"

# Polling interval in seconds
POLL_INTERVAL = 30

# Protocol / socket
TUYA_VERSION       = 3.5
SOCKET_TIMEOUT     = 5
SOCKET_RETRY_LIMIT = 2
