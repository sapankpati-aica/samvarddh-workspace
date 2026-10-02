"""Suppliers router"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db
from routers.auth import get_current_user, log_audit

router = APIRouter()

CATEGORIES = ["Wood & Carpentry","Hardware & Fittings","Tiles & Flooring","Electrical","Plumbing","Glass & Glazing","Painting","False Ceiling","HVAC","Furniture",
              "Modular Kitchen","Lighting","Stone & Granite","Labour Contractor","Other"]

class SupplierCreate(BaseModel):
    supplier_name: str
    contact_person: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    gstin: Optional[str] = ""
    address: Optional[str] = ""
    category: Optional[str] = ""
    payment_terms: Optional[str] = ""
    bank_name: Optional[str] = ""
    bank_account: Optional[str] = ""
    bank_ifsc: Optional[str] = ""
    notes: Optional[str] = ""

@router.get("/")
def list_suppliers(current_user=Depends(get_current_user), db=Depends(get_db)):
    rows = db.execute("SELECT * FROM suppliers ORDER BY supplier_name").fetchall()
    return [dict(r) for r in rows]

@router.post("/")
def create_supplier(data: SupplierCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("""INSERT INTO suppliers
        (supplier_name,contact_person,phone,email,gstin,address,category,payment_terms,
         bank_name,bank_account,bank_ifsc,notes,status,created_by,created_date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (data.supplier_name,data.contact_person,data.phone,data.email,data.gstin,
         data.address,data.category,data.payment_terms,data.bank_name,data.bank_account,
         data.bank_ifsc,data.notes,"Active",current_user["sub"],datetime.now().isoformat()))
    db.commit()
    log_audit(db,current_user["sub"],"Create Supplier","Suppliers",f"Supplier: {data.supplier_name}")
    return {"message":"Supplier added."}

@router.get("/{sup_id}")
def get_supplier(sup_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT * FROM suppliers WHERE id=?",(sup_id,)).fetchone()
    if not row: raise HTTPException(404,"Not found.")
    return dict(row)

@router.put("/{sup_id}")
def update_supplier(sup_id: int, data: SupplierCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("""UPDATE suppliers SET supplier_name=?,contact_person=?,phone=?,email=?,gstin=?,
        address=?,category=?,payment_terms=?,bank_name=?,bank_account=?,bank_ifsc=?,notes=? WHERE id=?""",
        (data.supplier_name,data.contact_person,data.phone,data.email,data.gstin,
         data.address,data.category,data.payment_terms,data.bank_name,data.bank_account,
         data.bank_ifsc,data.notes,sup_id))
    db.commit()
    return {"message":"Supplier updated."}

@router.delete("/{sup_id}")
def delete_supplier(sup_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("UPDATE suppliers SET status='Inactive' WHERE id=?",(sup_id,))
    db.commit()
    return {"message":"Supplier deactivated."}
