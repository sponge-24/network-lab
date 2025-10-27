# backend/core/guacamole_client.py
import requests
import time
from . import config

def get_guac_token() -> str | None:
    """Authenticates with Guacamole and returns an auth token."""
    try:
        response = requests.post(
            f"{config.GUACAMOLE_URL}/api/tokens",
            data={"username": config.GUAC_USERNAME, "password": config.GUAC_PASSWORD}
        )
        response.raise_for_status()
        return response.json()["authToken"]
    except requests.exceptions.RequestException as e:
        print(f"Error getting Guac token (is Guacamole running?): {e}")
        time.sleep(2)
        try:
            response = requests.post(
                f"{config.GUACAMOLE_URL}/api/tokens",
                data={"username": config.GUAC_USERNAME, "password": config.GUAC_PASSWORD}
            )
            response.raise_for_status()
            return response.json()["authToken"]
        except Exception as retry_e:
            print(f"Failed to get Guac token on retry: {retry_e}")
            return None

def create_guac_connection(token: str, name: str, vnc_port: int) -> dict:
    """Creates a new VNC connection in Guacamole."""
    connection_data = {
        "parentIdentifier": "ROOT",
        "name": name,
        "protocol": "vnc",
        "parameters": {
            "hostname": "backend",
            "port": str(vnc_port),
            "password": "",
            "username": "",
            "enable-sftp": "false" 
        },
        "attributes": {
        }
    }
    
    response = requests.post(
        f"{config.GUACAMOLE_URL}/api/session/data/{config.GUAC_DATA_SOURCE}/connections?token={token}",
        json=connection_data
    )
    response.raise_for_status()
    print(response.json())
    return response.json()

def delete_guac_connection(token: str, conn_id: str):
    """Deletes a connection from Guacamole."""
    encoded_conn_id = conn_id.replace('/', '%2F')
    response = requests.delete(
        f"{config.GUACAMOLE_URL}/api/session/data/{config.GUAC_DATA_SOURCE}/connections/{encoded_conn_id}?token={token}"
    )
    response.raise_for_status()