# backend/api/routes.py
import uuid
from fastapi import APIRouter, HTTPException
import base64
from core import config
import os
from . import models
from core import state_manager, vm_manager, guacamole_client

router = APIRouter()

def _get_guac_url(conn_id: str | None) -> str | None:
    """Helper to format the Guacamole URL."""
    if not conn_id:
        return None
    
    data_source = config.GUAC_DATA_SOURCE
    conn_type = "c" 

    identifier_bytes = f"{conn_id}\0{conn_type}\0{data_source}".encode('utf-8')
    
    encoded_string = base64.b64encode(identifier_bytes).decode('ascii')

    url = f"http://localhost:3001/guacamole/#/client/{encoded_string}"

    return url

def _format_node_response(node_id: str, node_data: dict) -> models.Node:
    """Helper to format node data into the Pydantic model."""
    return models.Node(
        id=node_id,
        status=node_data["status"],
        vnc_port=node_data.get("vnc_port"),
        guac_conn_id=node_data.get("guac_conn_id"),
        guac_url=_get_guac_url(node_data.get("guac_conn_id"))
    )

@router.get("/nodes", response_model=list[models.Node])
async def list_nodes():
    """Get a list of all nodes and their current status."""
    node_list = []
    nodes = state_manager.get_all_nodes()
    
    for node_id, data in nodes.items():
        if data["status"] == "running" and not state_manager.is_pid_running(data.get("pid")):
            print(f"Pruning stale node {node_id} during GET /nodes")
            state_manager.update_node_stop(node_id) 
            data["status"] = "stopped" 
        
        node_list.append(_format_node_response(node_id, data))
    return node_list

@router.post("/nodes", response_model=models.Node)
async def create_node():
    """Create a new, stopped node."""
    node_id = str(uuid.uuid4())
    overlay_path = vm_manager.create_vm_overlay(node_id)
    if not overlay_path:
        raise HTTPException(status_code=500, detail="Failed to create node overlay")

    if not vm_manager.create_cloud_init_seed(node_id):
        os.remove(overlay_path) 
        raise HTTPException(status_code=500, detail="Failed to create cloud-init ISO. Is 'genisoimage' installed?")
    

    new_node_data = state_manager.create_node_entry(node_id, overlay_path)
    return _format_node_response(node_id, new_node_data)

@router.post("/nodes/{node_id}/run", response_model=models.Node)
async def run_node(node_id: str):
    """Start a node."""
    node = state_manager.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node["status"] == "running" and state_manager.is_pid_running(node.get("pid")):
        raise HTTPException(status_code=400, detail="Node is already running")

    vnc_port = None
    token = None
    guac_conn_id = None
    try:
        vnc_port = state_manager.get_free_port()
        token = guacamole_client.get_guac_token()
        if not token:
            raise Exception("Could not authenticate with Guacamole")
        
        guac_conn_name = f"node-{node_id[:8]}"
        guac_conn = guacamole_client.create_guac_connection(token, guac_conn_name, vnc_port)
        guac_conn_id = guac_conn["identifier"]

        pid = vm_manager.start_vm(node_id, node, vnc_port)
        if not pid:
            raise Exception("Failed to start QEMU process")
        
        state_manager.update_node_run(node_id, pid, vnc_port, guac_conn_id)
        
        updated_node_data = state_manager.get_node(node_id)
        return _format_node_response(node_id, updated_node_data)

    except Exception as e:
        if vnc_port:
            state_manager.release_port(vnc_port)
        if guac_conn_id and token:
            try:
                guacamole_client.delete_guac_connection(token, guac_conn_id)
            except Exception as del_e:
                print(f"Failed to rollback Guac connection: {del_e}")
        
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/nodes/{node_id}/stop", response_model=models.Node)
async def stop_node(node_id: str):
    """Stop a running node."""
    node = state_manager.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node["status"] == "stopped":
        return _format_node_response(node_id, node)


    vm_manager.stop_vm(node.get("pid"))

    guac_conn_id = node.get("guac_conn_id")
    if guac_conn_id:
        token = guacamole_client.get_guac_token()
        if token:
            try:
                guacamole_client.delete_guac_connection(token, guac_conn_id)
            except Exception as e:
                print(f"Warning: Could not delete Guac connection {guac_conn_id}: {e}")
        else:
            print("Warning: Could not get Guac token to delete connection.")

    state_manager.update_node_stop(node_id)
    
    updated_node_data = state_manager.get_node(node_id)
    return _format_node_response(node_id, updated_node_data)

@router.post("/nodes/{node_id}/wipe", response_model=models.Node)
async def wipe_node(node_id: str):
    """Stop a node (if running) and reset its overlay disk."""
    node = state_manager.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if node["status"] == "running":
        await stop_node(node_id)
        node = state_manager.get_node(node_id) 

    if not vm_manager.wipe_vm_files(node_id, node["overlay_path"]):
        raise HTTPException(status_code=500, detail="Failed to wipe and re-create overlay")

    return _format_node_response(node_id, node)

@router.delete("/nodes/{node_id}", status_code=204)
async def delete_node(node_id: str):
    """Permanently delete a node."""
    node = state_manager.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if node["status"] == "running":
        await stop_node(node_id)

    if not vm_manager.delete_vm_files(node_id, node["overlay_path"]):
        print(f"Warning: Failed to delete all files for node {node_id}")

    state_manager.delete_node_entry(node_id)

    return