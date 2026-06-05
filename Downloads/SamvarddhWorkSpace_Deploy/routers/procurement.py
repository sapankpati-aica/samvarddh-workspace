"""Procurement router - with conveyance expense tracking"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import pathlib, shutil, uuid
from database import get_db
from routers.auth import get_current_user, log_audit

router = APIRouter()
UPLOAD_DIR = pathlib.Path("samvarddh_data/uploads/procurement")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = ["Wood Work","Hardware","Tiles","Electrical","Plumbing","Painting",
              "Flooring","Glass Work","Conveyance","Labour","Other"]

class ProcurementCreate(BaseModel):
    client_id: int
    quotation_id: Optional[int] = None
    entry_type: str = "Material"          # Material | Conveyance | Labour
    procurement_date: str
    vendor_name: Optional[str] = ""
    item_name: str
    category: Optional[str] = ""
    bill_number: Optional[str] = ""
    amount: float = 0
    payment_status: str = "Pending"
    drive_link: Optional[str] = ""
    remarks: Optional[str] = ""
    # Conveyance fields
    employee_name: Optional[str] = ""
    conveyance_from: Optional[str] = ""
    conveyance_to: Optional[str] = ""
    conveyance_mode: Optional[str] = ""   # Auto / Cab / Own Vehicle / Bus
    conveyance_purpose: Optional[str] = ""
    approval_status: Optional[str] = "Pending"  # Pending | Approved | Rejected | Reimbursed
    approved_by: Optional[str] = ""
    approved_date: Optional[str] = ""

@router.get("/")
def list_procurement(
    client_id: Optional[int] = None,
    entry_type: Optional[str] = None,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    # Add missing columns if upgrading from old DB
    for col, typ in [("entry_type","TEXT"), ("employee_name","TEXT"),
                     ("conveyance_from","TEXT"), ("conveyance_to","TEXT"),
                     ("conveyance_mode","TEXT"), ("conveyance_purpose","TEXT"),
                     ("approval_status","TEXT"), ("approved_by","TEXT"),
                     ("approved_date","TEXT")]:
        try:
            db.execute(f"ALTER TABLE procurement ADD COLUMN {col} {typ}")
            db.commit()
        except:
            pass

    q = "SELECT p.*,c.client_name FROM procurement p LEFT JOIN clients c ON p.client_id=c.id WHERE 1=1"
    params = []
    if client_id:
        q += " AND p.client_id=?"; params.append(client_id)
    if entry_type:
        q += " AND p.entry_type=?"; params.append(entry_type)
    q += " ORDER BY p.id DESC"
    rows = db.execute(q, params).fetchall()
    return [dict(r) for r in rows]

@router.get("/summary")
def procurement_summary(client_id: Optional[int] = None, current_user=Depends(get_current_user), db=Depends(get_db)):
    cond = f"WHERE client_id={client_id}" if client_id else ""
    rows = db.execute(f"""
        SELECT entry_type, SUM(amount) as total, COUNT(*) as count
        FROM procurement {cond}
        GROUP BY entry_type
    """).fetchall()
    return [dict(r) for r in rows]

@router.post("/")
def create_procurement(data: ProcurementCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    # Add columns if not exist
    for col, typ in [("entry_type","TEXT"), ("employee_name","TEXT"),
                     ("conveyance_from","TEXT"), ("conveyance_to","TEXT"),
                     ("conveyance_mode","TEXT"), ("conveyance_purpose","TEXT"),
                     ("approval_status","TEXT"), ("approved_by","TEXT"),
                     ("approved_date","TEXT")]:
        try:
            db.execute(f"ALTER TABLE procurement ADD COLUMN {col} {typ}")
            db.commit()
        except:
            pass

    db.execute("""INSERT INTO procurement 
                  (client_id,quotation_id,entry_type,procurement_date,vendor_name,item_name,category,
                   bill_number,amount,payment_status,drive_link,remarks,
                   employee_name,conveyance_from,conveyance_to,conveyance_mode,conveyance_purpose,
                   approval_status,created_by,created_date)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (data.client_id, data.quotation_id, data.entry_type,
                data.procurement_date, data.vendor_name, data.item_name,
                data.category, data.bill_number, data.amount,
                data.payment_status, data.drive_link, data.remarks,
                data.employee_name, data.conveyance_from, data.conveyance_to,
                data.conveyance_mode, data.conveyance_purpose,
                data.approval_status or "Pending",
                current_user["sub"], datetime.now().isoformat()))
    db.commit()
    log_audit(db, current_user["sub"], "Create Procurement", "Procurement",
              f"Type:{data.entry_type} | Item:{data.item_name} | Amt:{data.amount}")
    return {"message": "Entry added successfully."}

@router.put("/{proc_id}")
def update_procurement(proc_id: int, data: ProcurementCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("""UPDATE procurement SET client_id=?,quotation_id=?,entry_type=?,procurement_date=?,
                  vendor_name=?,item_name=?,category=?,bill_number=?,amount=?,payment_status=?,
                  drive_link=?,remarks=?,employee_name=?,conveyance_from=?,conveyance_to=?,
                  conveyance_mode=?,conveyance_purpose=? WHERE id=?""",
               (data.client_id, data.quotation_id, data.entry_type, data.procurement_date,
                data.vendor_name, data.item_name, data.category, data.bill_number,
                data.amount, data.payment_status, data.drive_link, data.remarks,
                data.employee_name, data.conveyance_from, data.conveyance_to,
                data.conveyance_mode, data.conveyance_purpose, proc_id))
    db.commit()
    return {"message": "Updated successfully."}

@router.delete("/{proc_id}")
def delete_procurement(proc_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("DELETE FROM procurement WHERE id=?", (proc_id,))
    db.commit()
    return {"message": "Deleted."}

@router.post("/{proc_id}/approve-conveyance")
def approve_conveyance(proc_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    """CXO approves a conveyance claim"""
    if current_user["role"] not in ["Admin","Management","CXO"]:
        # Also check designation via user table
        pass
    row = db.execute("SELECT * FROM procurement WHERE id=? AND entry_type='Conveyance'", (proc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Conveyance entry not found.")
    db.execute("UPDATE procurement SET approval_status='Approved', approved_by=?, approved_date=? WHERE id=?",
               (current_user["sub"], datetime.now().isoformat(), proc_id))
    db.commit()
    log_audit(db, current_user["sub"], "Approve Conveyance", "Procurement", f"ID:{proc_id}")
    return {"message": "Conveyance approved."}

@router.post("/{proc_id}/reject-conveyance")
def reject_conveyance(proc_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT id FROM procurement WHERE id=? AND entry_type='Conveyance'", (proc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Not found.")
    db.execute("UPDATE procurement SET approval_status='Rejected', approved_by=?, approved_date=? WHERE id=?",
               (current_user["sub"], datetime.now().isoformat(), proc_id))
    db.commit()
    return {"message": "Conveyance rejected."}

@router.post("/{proc_id}/reimburse-conveyance")
def reimburse_conveyance(proc_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT id FROM procurement WHERE id=? AND entry_type='Conveyance'", (proc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Not found.")
    db.execute("UPDATE procurement SET approval_status='Reimbursed', payment_status='Paid' WHERE id=?", (proc_id,))
    db.commit()
    return {"message": "Marked as reimbursed."}

@router.post("/{proc_id}/upload-bill")
async def upload_bill(
    proc_id: int,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    ext = pathlib.Path(file.filename).suffix.lower()
    allowed = [".pdf", ".jpg", ".jpeg", ".png"]
    if ext not in allowed:
        raise HTTPException(400, "Allowed: PDF, JPG, PNG only")
    fname = f"bill_{proc_id}_{uuid.uuid4()}{ext}"
    fpath = UPLOAD_DIR / fname
    content = await file.read()
    with open(fpath, "wb") as f:
        f.write(content)
    db.execute("UPDATE procurement SET file_path=? WHERE id=?", (str(fpath), proc_id))
    db.commit()
    return {"message": "Bill uploaded.", "url": "/uploads/procurement/" + fname}
