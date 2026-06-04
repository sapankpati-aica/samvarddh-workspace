"""Design Files router - Fixed upload with proper error handling"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import Optional
from datetime import datetime
import pathlib, shutil, uuid
from database import get_db
from routers.auth import get_current_user, log_audit

router = APIRouter()
UPLOAD_DIR = pathlib.Path("samvarddh_data/uploads/designs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/")
def list_designs(client_id: Optional[int] = None, current_user=Depends(get_current_user), db=Depends(get_db)):
    q = "SELECT d.*,c.client_name FROM design_files d LEFT JOIN clients c ON d.client_id=c.id WHERE 1=1"
    params = []
    if client_id:
        q += " AND d.client_id=?"; params.append(client_id)
    q += " ORDER BY d.id DESC"
    rows = db.execute(q, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("file_path") and pathlib.Path(d["file_path"]).exists():
            d["file_url"] = "/uploads/designs/" + pathlib.Path(d["file_path"]).name
        result.append(d)
    return result

@router.delete("/{design_id}")
def delete_design(design_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT * FROM design_files WHERE id=?", (design_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Design not found.")
    # Optionally delete file
    if row["file_path"] and pathlib.Path(row["file_path"]).exists():
        pathlib.Path(row["file_path"]).unlink(missing_ok=True)
    db.execute("DELETE FROM design_files WHERE id=?", (design_id,))
    db.commit()
    return {"message": "Design deleted."}

@router.post("/upload")
async def upload_design(
    client_id: int = Form(...),
    version: str = Form(...),
    designer_names: str = Form(""),
    notes: str = Form(""),
    drive_link: str = Form(""),
    quotation_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    # Validate PDF
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed.")
    
    # Read file content
    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(400, "Uploaded file is empty.")
    except Exception as e:
        raise HTTPException(500, f"Could not read file: {str(e)}")
    
    # Save file
    fname = f"{uuid.uuid4()}_{file.filename}"
    fpath = UPLOAD_DIR / fname
    try:
        with open(fpath, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(500, f"Could not save file: {str(e)}")
    
    # Convert quotation_id
    q_id = None
    if quotation_id and quotation_id.strip() and quotation_id != "None":
        try:
            q_id = int(quotation_id)
        except:
            q_id = None
    
    # Save to DB
    db.execute("""INSERT INTO design_files 
                  (client_id, quotation_id, version, designer_names, notes, file_path, drive_link, uploaded_by, upload_date)
                  VALUES (?,?,?,?,?,?,?,?,?)""",
               (client_id, q_id, version, designer_names, notes,
                str(fpath), drive_link, current_user["sub"], datetime.now().isoformat()))
    db.commit()
    log_audit(db, current_user["sub"], "Upload Design", "Designs", 
              f"Client {client_id} | Version: {version} | File: {file.filename}")
    
    file_url = "/uploads/designs/" + fname
    return {"message": f"Design file '{file.filename}' uploaded successfully.", "url": file_url}
