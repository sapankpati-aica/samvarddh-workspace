"""Employees router"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db
from routers.auth import get_current_user, log_audit

router = APIRouter()

DESIGNATIONS = ["CXO","Lead Designer","Project Manager","Project Engineer","Associates","Management Trainee"]

class EmployeeCreate(BaseModel):
    name: str
    address: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    designation: Optional[str] = ""
    status: str = "Active"

@router.get("/")
def list_employees(current_user=Depends(get_current_user), db=Depends(get_db)):
    rows = db.execute("SELECT * FROM employees ORDER BY name").fetchall()
    return [dict(r) for r in rows]

@router.post("/")
def create_employee(data: EmployeeCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("INSERT INTO employees (name,address,phone,email,designation,status,created_date) VALUES (?,?,?,?,?,?,?)",
               (data.name, data.address, data.phone, data.email, data.designation, data.status, datetime.now().isoformat()))
    db.commit()
    log_audit(db, current_user["sub"], "Create Employee", "Employees", f"Employee: {data.name}")
    return {"message": "Employee added."}

@router.put("/{emp_id}")
def update_employee(emp_id: int, data: EmployeeCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("UPDATE employees SET name=?,address=?,phone=?,email=?,designation=?,status=? WHERE id=?",
               (data.name, data.address, data.phone, data.email, data.designation, data.status, emp_id))
    db.commit()
    return {"message": "Employee updated."}

@router.delete("/{emp_id}")
def delete_employee(emp_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("UPDATE employees SET status='Inactive' WHERE id=?", (emp_id,))
    db.commit()
    return {"message": "Employee deactivated."}
