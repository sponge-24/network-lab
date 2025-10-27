# backend/api/models.py
from pydantic import BaseModel

class Node(BaseModel):
    id: str
    status: str
    vnc_port: int | None
    guac_conn_id: str | None
    guac_url: str | None