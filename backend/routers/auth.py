"""Auth router - JWT login, logout, password change"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
import bcrypt, jwt, sqlite3
from datetime import datetime, timedelta
from database import get_db, DB_PATH

router = APIRouter()
SECRET_KEY = "samvarddh-secret-key-2025-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 12

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

ROLE_ACCESS = {
    "Admin":            ["*"],
    "Management":       ["dashboard","clients","quotation","design","procurement","worklogs","invoices","employees","setup"],
    "Lead Designer":    ["clients","quotation","design","worklogs","dashboard"],
    "Project Manager":  ["clients","quotation","design","procurement","worklogs","dashboard","employees"],
    "Project Engineer": ["worklogs","procurement","dashboard"],
    "Accounts":         ["clients","quotation","procurement","invoices","dashboard"],
    "Viewer":           ["dashboard"],
}

def create_token(data: dict):
    exp = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({**data, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token.")

def log_audit(conn, username, action, module, details=""):
    conn.execute("INSERT INTO audit_log (username,action,module,details,created_at) VALUES (?,?,?,?,?)",
                 (username, action, module, details, datetime.now().isoformat()))
    conn.commit()

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    row = db.execute("SELECT * FROM users WHERE username=? AND status='Active'",
                     (form.username,)).fetchone()
    if not row or not bcrypt.checkpw(form.password.encode(), row["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    db.execute("UPDATE users SET last_login=? WHERE id=?",
               (datetime.now().isoformat(), row["id"]))
    db.commit()
    log_audit(db, form.username, "Login", "Auth", "User logged in")

    token = create_token({
        "sub": row["username"],
        "role": row["role"],
        "full_name": row["full_name"],
        "force_change": bool(row["force_password_change"])
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": row["role"],
        "full_name": row["full_name"],
        "force_password_change": bool(row["force_password_change"]),
        "allowed_modules": ROLE_ACCESS.get(row["role"], ["dashboard"])
    }

@router.post("/change-password")
def change_password(data: PasswordChange, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT * FROM users WHERE username=?", (current_user["sub"],)).fetchone()
    if not row or not bcrypt.checkpw(data.current_password.encode(), row["password_hash"].encode()):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")
    new_hash = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt()).decode()
    db.execute("UPDATE users SET password_hash=?, force_password_change=0 WHERE username=?",
               (new_hash, current_user["sub"]))
    db.commit()
    log_audit(db, current_user["sub"], "Change Password", "Auth", "Password changed successfully")
    return {"message": "Password changed successfully."}

@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return current_user

@router.get("/audit-log")
def get_audit_log(current_user=Depends(get_current_user), db=Depends(get_db)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only.")
    rows = db.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 500").fetchall()
    return [dict(r) for r in rows]
