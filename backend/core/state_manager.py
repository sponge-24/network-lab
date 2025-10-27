# backend/core/state_manager.py
import json
import os
from . import config

STATE = {
    "nodes": {},
    "port_manager": list(config.VNC_PORT_POOL)
}

def is_pid_running(pid: int | None) -> bool:
    """Check if a process with the given PID is running."""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

def save_state():
    """Saves the current STATE to the DB_FILE."""
    os.makedirs(config.OVERLAY_DIR, exist_ok=True)
    with open(config.DB_FILE, 'w') as f:
        json.dump(STATE, f, indent=2)

def load_state():
    """Loads and prunes state from the DB_FILE on startup."""
    global STATE
    if os.path.exists(config.DB_FILE):
        try:
            with open(config.DB_FILE, 'r') as f:
                STATE = json.load(f)
                if "port_manager" not in STATE:
                    STATE["port_manager"] = list(config.VNC_PORT_POOL)
        except json.JSONDecodeError:
            pass 
    
    # Prune any stale nodes that were 'running' but PID is gone
    all_nodes = list(STATE["nodes"].items())
    for node_id, node in all_nodes:
        if node.get("status") == "running" and not is_pid_running(node.get("pid")):
            print(f"Pruning stale node {node_id}")
            if node.get("vnc_port"):
                release_port(node["vnc_port"])
            node["status"] = "stopped"
            node["pid"] = None
            node["vnc_port"] = None
            node["guac_conn_id"] = None
    
    save_state()


def get_free_port() -> int:
    """Get the next available VNC port."""
    if not STATE["port_manager"]:
        raise Exception("No free VNC ports available")
    port = STATE["port_manager"].pop(0)
    save_state() 
    return port

def release_port(port: int | None):
    """Return a VNC port to the pool."""
    if port and port not in STATE["port_manager"]:
        STATE["port_manager"].append(port)
        save_state()

def get_all_nodes() -> dict:
    return STATE["nodes"]

def get_node(node_id: str) -> dict | None:
    return STATE["nodes"].get(node_id)

def create_node_entry(node_id: str, overlay_path: str) -> dict:
    """Adds a new node entry to the state."""
    new_node = {
        "status": "stopped",
        "pid": None,
        "vnc_port": None,
        "guac_conn_id": None,
        "overlay_path": overlay_path
    }
    STATE["nodes"][node_id] = new_node
    save_state()
    return new_node

def update_node_run(node_id: str, pid: int, vnc_port: int, guac_conn_id: str):
    """Updates a node's state to 'running'."""
    node = get_node(node_id)
    if node:
        node["status"] = "running"
        node["pid"] = pid
        node["vnc_port"] = vnc_port
        node["guac_conn_id"] = guac_conn_id
        save_state()

def update_node_stop(node_id: str):
    """Updates a node's state to 'stopped' and releases its port."""
    node = get_node(node_id)
    if node:
        release_port(node.get("vnc_port")) 
        node["status"] = "stopped"
        node["pid"] = None
        node["vnc_port"] = None
        node["guac_conn_id"] = None
        save_state()

def delete_node_entry(node_id: str):
    """Removes a node from the state entirely."""
    if node_id in STATE["nodes"]:
        del STATE["nodes"][node_id]
        save_state()