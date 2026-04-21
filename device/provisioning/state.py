from enum import StrEnum


class ProvisioningState(StrEnum):
    FACTORY_RESET = "factory_reset"
    AP_MODE = "ap_mode"
    CREDENTIALS_RECEIVED = "credentials_received"
    WIFI_CONNECTING = "wifi_connecting"
    BACKEND_REGISTERING = "backend_registering"
    ONLINE = "online"
    ERROR = "error"
