"""Users router - Admin user management"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import bcrypt
from datetime import datetime
from database import get_db
from routers.auth import get_current_user, log_audit

router = APIRouter()

ROLES = ["Admin","Management","Lead Designer","Project Manager","Project Engineer","Accounts","Viewer"]
DESIGNATIONS = ["CXO","Lead Designer","Project Manager","Project Engineer","Associates","Management Trainee"]

class UserCreate(BaseModel):
    full_name: str
    email: Optional[str] = ""
    username: str
    password: str
    role: str
    designation: Optional[str] = ""
    status: str = "Active"

class UserUpdate(BaseModel):
    full_name: Optional[str]
    email: Optional[str]
    role: Optional[str]
    designation: Optional[str]
    status: Optional[str]

class PasswordReset(BaseModel):
    new_password: str

def require_admin(current_user=Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user

@router.get("/")
def list_users(current_user=Depends(require_admin), db=Depends(get_db)):
    rows = db.execute("SELECT id,full_name,email,username,role,designation,status,created_date,last_login FROM users ORDER BY id").fetchall()
    return [dict(r) for r in rows]

@router.post("/")
def create_user(data: UserCreate, current_user=Depends(require_admin), db=Depends(get_db)):
    existing = db.execute("SELECT id FROM users WHERE username=?", (data.username,)).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists.")
    pw_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    db.execute("""INSERT INTO users (full_name,email,username,password_hash,role,designation,status,force_password_change,created_date)
                  VALUES (?,?,?,?,?,?,?,1,?)""",
               (data.full_name, data.email, data.username, pw_hash, data.role,
                data.designation, data.status, datetime.now().isoformat()))
    db.commit()
    log_audit(db, current_user["sub"], "Create User", "Users", f"Created user: {data.username} ({data.role})")
    return {"message": "User created successfully."}

@router.put("/{user_id}")
def update_user(user_id: int, data: UserUpdate, current_user=Depends(require_admin), db=Depends(get_db)):
    row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found.")
    updates = {k: v for k, v in data.dict().items() if v is not None}
    if not updates:
        return {"message": "Nothing to update."}
    sets = ", ".join(f"{k}=?" for k in updates)
    db.execute(f"UPDATE users SET {sets} WHERE id=?", (*updates.values(), user_id))
    db.commit()
    log_audit(db, current_user["sub"], "Update User", "Users", f"Updated user ID {user_id}")
    return {"message": "User updated."}

@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, data: PasswordReset, current_user=Depends(require_admin), db=Depends(get_db)):
    row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found.")
    new_hash = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt()).decode()
    db.execute("UPDATE users SET password_hash=?, force_password_change=1 WHERE id=?", (new_hash, user_id))
    db.commit()
    log_audit(db, current_user["sub"], "Reset Password", "Users", f"Reset password for user ID {user_id}")
    return {"message": "Password reset. User must change on next login."}

@router.delete("/{user_id}")
def deactivate_user(user_id: int, current_user=Depends(require_admin), db=Depends(get_db)):
    db.execute("UPDATE users SET status='Inactive' WHERE id=?", (user_id,))
    db.commit()
    log_audit(db, current_user["sub"], "Deactivate User", "Users", f"Deactivated user ID {user_id}")
    return {"message": "User deactivated."}

@router.get("/roles/list")
def get_roles():
    return ROLES

@router.get("/designations/list")
def get_designations():
    return DESIGNATIONS
