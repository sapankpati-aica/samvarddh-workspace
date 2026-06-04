"""Backup router"""
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
import pathlib, shutil, zipfile
from datetime import datetime
from database import DB_PATH, get_db
from routers.auth import get_current_user, log_audit

router = APIRouter()
BACKUP_DIR = pathlib.Path("samvarddh_data/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/create")
def create_backup(current_user=Depends(get_current_user), db=Depends(get_db)):
    if current_user["role"] != "Admin":
        from fastapi import HTTPException
        raise HTTPException(403, "Admin only.")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = BACKUP_DIR / f"samvarddh_backup_{ts}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if DB_PATH.exists():
            zf.write(DB_PATH, "samvarddh_portal.db")
        uploads = pathlib.Path("samvarddh_data/uploads")
        if uploads.exists():
            for f in uploads.rglob("*"):
                if f.is_file():
                    zf.write(f, str(f.relative_to("samvarddh_data")))
    log_audit(db, current_user["sub"], "Backup Created", "Backup", f"Backup: {zip_path.name}")
    return {"message": "Backup created.", "file": zip_path.name, "size_mb": round(zip_path.stat().st_size/1024/1024, 2)}

@router.get("/list")
def list_backups(current_user=Depends(get_current_user)):
    files = sorted(BACKUP_DIR.glob("*.zip"), reverse=True)
    return [{"name": f.name, "size_mb": round(f.stat().st_size/1024/1024, 2),
             "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat()} for f in files]

@router.get("/download/{filename}")
def download_backup(filename: str, current_user=Depends(get_current_user)):
    if current_user["role"] != "Admin":
        from fastapi import HTTPException
        raise HTTPException(403, "Admin only.")
    fpath = BACKUP_DIR / filename
    if not fpath.exists():
        from fastapi import HTTPException
        raise HTTPException(404, "Backup file not found.")
    return FileResponse(str(fpath), media_type="application/zip", filename=filename)

@router.get("/paths")
def get_paths(current_user=Depends(get_current_user)):
    return {
        "database": str(DB_PATH.absolute()),
        "uploads": str(pathlib.Path("samvarddh_data/uploads").absolute()),
        "reports": str(pathlib.Path("samvarddh_data/reports").absolute()),
        "backups": str(BACKUP_DIR.absolute()),
    }
