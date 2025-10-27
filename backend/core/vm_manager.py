# backend/core/vm_manager.py
import subprocess
import os
import signal
import time
import tempfile
import shutil
from . import config
from . import state_manager

USER_DATA_YAML = """#cloud-config
ssh_pwauth: True
chpasswd:
  expire: false
  list: |
    ubuntu:ubuntu
users:
  - name: ubuntu
    groups: sudo
    shell: /bin/bash
"""

META_DATA_YAML = """
instance-id: 1cc69f53-5636-433b-8821-a32e313f1a56
local-hostname: spongebob
"""


def create_cloud_init_seed(node_id: str) -> str | None:
    """Creates a cloud-init seed.img file in the OVERLAY_DIR using cloud-localds."""
    seed_path = os.path.join(config.OVERLAY_DIR, f"seed_{node_id}.img")
    temp_dir = tempfile.mkdtemp()
    
    user_data_path = os.path.join(temp_dir, "user-data.yml")
    meta_data_path = os.path.join(temp_dir, "metadata.yml")

    try:
        
        with open(user_data_path, 'w') as f:
            f.write(USER_DATA_YAML)
        
        with open(meta_data_path, 'w') as f:
            f.write(META_DATA_YAML)
        
        subprocess.run(
            [
                "cloud-localds",
                seed_path, 
                user_data_path,
                meta_data_path
            ],
            check=True, capture_output=True
        )
        return seed_path
    
    except (subprocess.CalledProcessError, OSError) as e:
        print(f"Failed to create cloud-init seed: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"cloud-localds stderr: {e.stderr.decode()}")
        print("Please ensure 'cloud-image-utils' is installed (e.g., 'sudo apt install cloud-image-utils')")
        return None
    
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def create_vm_overlay(node_id: str) -> str | None:
    """Creates a new qcow2 overlay file for a node."""
    overlay_path = os.path.join(config.OVERLAY_DIR, f"node_{node_id}.qcow2")
    try:
        subprocess.run(
            ["qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", config.BASE_IMAGE_PATH, overlay_path],
            check=True, capture_output=True
        )
        return overlay_path
    except subprocess.CalledProcessError as e:
        print(f"Failed to create overlay: {e.stderr.decode()}")
        return None


def start_vm(node_id: str, node_data: dict, vnc_port: int) -> int | None:
    """Starts a QEMU VM as a background process."""
    vnc_display = vnc_port - 5900
    
    seed_path = os.path.join(config.OVERLAY_DIR, f"seed_{node_id}.img")
    cloud_init_drive = []
    if os.path.exists(seed_path):
        cloud_init_drive = ["-drive", f"file={seed_path},format=raw,if=virtio"]
    else:
        print(f"Warning: Could not find cloud-init seed at {seed_path}")

    qemu_cmd = [
        "qemu-system-x86_64",
        "-cpu", "host",
        "-machine", "type=q35,accel=kvm",
        "-m", "2048", # 2G RAM
        "-nographic",
        "-netdev", "user,id=net0", # Using "net0" for consistency
        "-device", "virtio-net-pci,netdev=net0",
        "-drive", f"file={node_data['overlay_path']},if=virtio,format=qcow2", # Our overlay
        *cloud_init_drive,  # Our seed.img
        "-vnc", f"0.0.0.0:{vnc_display}" # VNC for Guacamole
    ]
    
    try:
        process = subprocess.Popen(qemu_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return process.pid
    except Exception as e:
        print(f"Failed to start QEMU: {e}")
        return None


def stop_vm(pid: int | None):
    if pid and state_manager.is_pid_running(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            if state_manager.is_pid_running(pid):
                os.kill(pid, signal.SIGKILL)
            return True
        except OSError as e:
            print(f"Error stopping VM (PID: {pid}): {e}")
            return False
    return True


def wipe_vm_files(node_id: str, overlay_path: str) -> bool:
    """Deletes/re-creates overlay and deletes/re-creates cloud-init seed.img."""
    seed_path = os.path.join(config.OVERLAY_DIR, f"seed_{node_id}.img") 
    try:
        if os.path.exists(overlay_path):
            os.remove(overlay_path)
        
        if os.path.exists(seed_path):
            os.remove(seed_path)
        
        subprocess.run(
            ["qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", config.BASE_IMAGE_PATH, overlay_path],
            check=True, capture_output=True
        )
        
        if not create_cloud_init_seed(node_id): 
             print(f"Warning: Failed to re-create cloud-init seed for {node_id}")
        
        return True
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"Failed to wipe/re-create files: {e}")
        return False

def delete_vm_files(node_id: str, overlay_path: str) -> bool:
    """Deletes all files associated with a VM."""
    seed_path = os.path.join(config.OVERLAY_DIR, f"seed_{node_id}.img")
    try:
        if os.path.exists(overlay_path):
            os.remove(overlay_path)
        if os.path.exists(seed_path):
            os.remove(seed_path)
        return True
    except OSError as e:
        print(f"Error deleting VM files for node {node_id}: {e}")
        return False