"""Clients router"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db
from routers.auth import get_current_user, log_audit

router = APIRouter()

class ClientCreate(BaseModel):
    client_name: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    gstin: Optional[str] = ""
    billing_address: Optional[str] = ""
    site_address: Optional[str] = ""
    project_type: Optional[str] = ""
    referred_by: Optional[str] = ""
    lead_designer: Optional[str] = ""
    project_manager: Optional[str] = ""
    project_engineer: Optional[str] = ""
    status: str = "Active"

@router.get("/")
def list_clients(current_user=Depends(get_current_user), db=Depends(get_db)):
    rows = db.execute("SELECT * FROM clients ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]

@router.post("/")
def create_client(data: ClientCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("""INSERT INTO clients (client_name,phone,email,gstin,billing_address,site_address,project_type,referred_by,lead_designer,project_manager,project_engineer,status,created_date)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (data.client_name, data.phone, data.email, data.gstin,
                data.billing_address, data.site_address, data.project_type,
                data.referred_by, data.lead_designer, data.project_manager,
                data.project_engineer, data.status, datetime.now().isoformat()))
    db.commit()
    log_audit(db, current_user["sub"], "Create Client", "Clients", f"Client: {data.client_name}")
    return {"message": "Client created."}

@router.get("/{client_id}")
def get_client(client_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    if not row: raise HTTPException(404, "Client not found.")
    return dict(row)

@router.put("/{client_id}")
def update_client(client_id: int, data: ClientCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("""UPDATE clients SET client_name=?,phone=?,email=?,gstin=?,billing_address=?,site_address=?,project_type=?,referred_by=?,lead_designer=?,project_manager=?,project_engineer=?,status=? WHERE id=?""",
               (data.client_name, data.phone, data.email, data.gstin,
                data.billing_address, data.site_address, data.project_type,
                data.referred_by, data.lead_designer, data.project_manager,
                data.project_engineer, data.status, client_id))
    db.commit()
    log_audit(db, current_user["sub"], "Update Client", "Clients", f"Client ID: {client_id}")
    return {"message": "Client updated."}
