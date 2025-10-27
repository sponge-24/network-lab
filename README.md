# QEMU Network Lab

This project provides a web-based management interface for a QEMU/KVM virtual machine lab. It allows users to create, run, stop, and manage multiple VM 'nodes' through a simple React frontend. Remote access to the VM consoles is provided by an integrated Apache Guacamole instance.

The entire environment is containerized using Docker and Docker Compose, making it easy to set up and run.

## Features

- **Web-Based VM Management**: Simple UI to create, run, stop, wipe, and delete VMs.
- **Hardware-Accelerated Virtualization**: Leverages QEMU/KVM for efficient performance.
- **Efficient Storage**: Uses `qcow2` overlay images. Each new VM is a lightweight snapshot of a base image, saving disk space.
- **Integrated Remote Console**: In-browser terminal access to VMs via Apache Guacamole.
- **Containerized & Portable**: All services are defined in `docker-compose.yml` for one-command setup.
- **Real-time Status**: The frontend polls the backend to provide near real-time status of each VM.

## Architecture

The project consists of several services that work together:

- **Frontend**: A React application running on port **3000**. It provides the user interface for managing the virtual machine nodes.
- **Backend**: A FastAPI (Python) application on port **8000**. It exposes a REST API to control the lifecycle of QEMU VMs, manage disk images, and configure Guacamole connections.
- **Guacamole**: An Apache Guacamole web application on port **3001**. It provides the clientless remote desktop gateway. The backend automatically creates and manages connections here.
- **Guacd**: The core Guacamole proxy service that connects to the VNC ports exposed by the QEMU VMs.
- **PostgreSQL**: A PostgreSQL database used by Guacamole to store its connection data and user information.
- **QEMU/KVM**: The virtualization engine running on the host, accessed by the backend via the `/dev/kvm` device.

All services are connected on an internal Docker bridge network (`net-lab-internal`).

## Prerequisites

Before you begin, ensure you have the following installed on your host machine:

1.  **Docker**: [Installation Guide](https://docs.docker.com/engine/install/)
2.  **Docker Compose**: [Installation Guide](https://docs.docker.com/compose/install/)
3.  **KVM**: The backend requires KVM for hardware acceleration.
    -   Check if KVM is enabled:
        ```sh
        ls /dev/kvm
        ```
        If this command returns `/dev/kvm`, you are ready.
    -   If not, you may need to enable virtualization in your BIOS and install KVM packages (`qemu-kvm`, `libvirt-daemon-system`, etc.). The user running Docker also needs to be in the `kvm` group.

## Getting Started

1.  **Clone the Repository**
    ```sh
    git clone <your-repo-url>
    cd sandbox-labs-docker
    ```

2.  **Place Base Image**
    This project requires a base `qcow2` disk image to create new VMs from.
    -   Place your base image file in the `images/` directory.
    -   The default expected name is `base.qcow2`. If your image has a different name, you will need to update the configuration in `backend/core/config.py`.

3.  **Build and Run the Services**
    Use Docker Compose to build the images and start all the containers.
    ```sh
    docker-compose up --build -d
    ```
    This command will:
    -   Build the `frontend` and `backend` images based on their Dockerfiles.
    -   Pull the `postgres`, `guacamole`, and `guacd` images.
    -   Start all services in detached mode (`-d`).

4.  **Initialize the Guacamole Database**
    After the services have started for the first time, you need to initialize the PostgreSQL database schema for Guacamole. Run the following command in your terminal:
    ```sh
    docker run --rm guacamole/guacamole /opt/guacamole/bin/initdb.sh --postgresql | docker exec -i guac-postgres psql -U guacamole_user -d guacamole_db
    ```

5.  **Restart the Services**
    To ensure all services are running with the new database schema, restart the containers.
    ```sh
    docker-compose restart
    ```
    Alternatively, you can take them down and bring them back up:
    ```sh
    docker-compose down && docker-compose up -d
    ```

6.  **Verify the Setup**
    Check if all containers are running:
    ```sh
    docker-compose ps
    ```
    You should see `guac-postgres`, `guacd`, `guacamole`, `backend`, and `frontend` with a status of `Up`.

## Usage

1.  **Access the Frontend**
    Open your web browser and navigate to:
    [http://localhost:3000](http://localhost:3000)

2.  **Manage Nodes**
    -   **Create New Node**: Click this button to create a new VM. The backend will generate a unique ID and create a `qcow2` overlay image for it.
    -   **Run**: Starts the selected VM. The backend will launch a QEMU process and create a corresponding connection in Guacamole.
    -   **Stop**: Stops a running VM.
    -   **Wipe**: Stops the VM (if running) and reverts its disk to the state of the original base image by replacing its overlay file.
    -   **Delete**: Permanently deletes the VM, including its overlay image.

3.  **Accessing the VM Console**
    -   Once a node is `running`, an "Open Guacamole" link will appear.
    -   Clicking this link will open a new tab to the Guacamole interface, giving you direct console access to the VM.
    -   **Default Guacamole Credentials**:
        -   Username: `guacadmin`
        -   Password: `guacadmin`
    -   You will be logged in automatically to the correct connection for the selected node.

## API Endpoints

The backend exposes a RESTful API for managing the lifecycle of the virtual machine nodes.

| Method | Endpoint                  | Description                                                                                                                                 |
| :----- | :------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------ |
| `GET`  | `/nodes`                  | Retrieves a list of all VM nodes and their current state, including status (`running`, `stopped`), VNC port, and the Guacamole console URL. |
| `POST` | `/nodes`                  | Creates a new node with a unique ID and a fresh `qcow2` overlay image. The node is created in a `stopped` state.                             |
| `POST` | `/nodes/{node_id}/run`    | Starts the specified VM. This allocates a VNC port, starts the QEMU process, and creates a corresponding connection in Guacamole.            |
| `POST` | `/nodes/{node_id}/stop`   | Stops a running VM. This terminates the QEMU process and removes the associated Guacamole connection.                                         |
| `POST` | `/nodes/{node_id}/wipe`   | Resets a node's disk to its original state by replacing its `qcow2` overlay file with a fresh copy of the base image. Stops the VM if running. |
| `DELETE`| `/nodes/{node_id}`        | Permanently deletes a node, including its overlay disk image and all associated state. Stops the VM if running.                             |

---