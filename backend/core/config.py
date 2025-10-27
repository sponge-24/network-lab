import os

PROJECT_ROOT = "/app"

BASE_IMAGE_PATH = "/app/images/base.qcow2"
OVERLAY_DIR = "/app/overlays"
DB_FILE = os.path.join(OVERLAY_DIR, "lab_state.json")

# --- Guacamole Configuration ---
GUACAMOLE_URL = "http://guacamole:8080/guacamole"
GUAC_USERNAME = "guacadmin"
GUAC_PASSWORD = "guacadmin"
GUAC_DATA_SOURCE = "postgresql"

# --- VM Configuration ---
VNC_PORT_POOL = list(range(5900, 5921)) # VNC ports :0 through :20