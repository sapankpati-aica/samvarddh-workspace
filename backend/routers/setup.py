"""Setup router - Company details with fixed file upload"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import Optional
import pathlib, shutil, uuid, os
from database import get_db
from routers.auth import get_current_user

router = APIRouter()
UPLOAD_DIR = pathlib.Path("samvarddh_data/uploads/setup")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class SetupUpdate(BaseModel):
    brand_name: Optional[str] = ""
    legal_name: Optional[str] = ""
    gstin: Optional[str] = ""
    pan: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    website: Optional[str] = ""
    city: Optional[str] = ""
    state: Optional[str] = ""
    address: Optional[str] = ""
    bank_name: Optional[str] = ""
    bank_account: Optional[str] = ""
    bank_ifsc: Optional[str] = ""
    bank_branch: Optional[str] = ""
    default_terms: Optional[str] = ""
    default_footer: Optional[str] = ""
    authorised_signatory: Optional[str] = ""

@router.get("/")
def get_setup(current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT * FROM company_setup LIMIT 1").fetchone()
    if not row:
        return {}
    data = dict(row)
    # Convert file paths to accessible URLs
    if data.get("logo_path") and pathlib.Path(data["logo_path"]).exists():
        data["logo_url"] = "/uploads/setup/" + pathlib.Path(data["logo_path"]).name
    if data.get("signature_path") and pathlib.Path(data["signature_path"]).exists():
        data["signature_url"] = "/uploads/setup/" + pathlib.Path(data["signature_path"]).name
    return data

@router.put("/")
def update_setup(data: SetupUpdate, current_user=Depends(get_current_user), db=Depends(get_db)):
    if current_user["role"] not in ["Admin", "Management"]:
        raise HTTPException(403, "Admin/Management access required.")
    # Check if authorised_signatory column exists, add if not
    try:
        db.execute("ALTER TABLE company_setup ADD COLUMN authorised_signatory TEXT")
        db.commit()
    except:
        pass
    existing = db.execute("SELECT id FROM company_setup LIMIT 1").fetchone()
    if existing:
        db.execute("""UPDATE company_setup SET brand_name=?,legal_name=?,gstin=?,pan=?,phone=?,email=?,
                      website=?,city=?,state=?,address=?,bank_name=?,bank_account=?,bank_ifsc=?,
                      bank_branch=?,default_terms=?,default_footer=?,authorised_signatory=? WHERE id=?""",
                   (data.brand_name,data.legal_name,data.gstin,data.pan,data.phone,data.email,
                    data.website,data.city,data.state,data.address,data.bank_name,data.bank_account,
                    data.bank_ifsc,data.bank_branch,data.default_terms,data.default_footer,
                    data.authorised_signatory,existing["id"]))
    else:
        db.execute("""INSERT INTO company_setup (brand_name,legal_name,gstin,pan,phone,email,website,
                      city,state,address,bank_name,bank_account,bank_ifsc,bank_branch,default_terms,
                      default_footer,authorised_signatory) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (data.brand_name,data.legal_name,data.gstin,data.pan,data.phone,data.email,
                    data.website,data.city,data.state,data.address,data.bank_name,data.bank_account,
                    data.bank_ifsc,data.bank_branch,data.default_terms,data.default_footer,
                    data.authorised_signatory))
    db.commit()
    return {"message": "Setup saved successfully."}

@router.post("/upload-logo")
async def upload_logo(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    # Validate file type
    allowed = [".png", ".jpg", ".jpeg", ".gif", ".webp"]
    ext = pathlib.Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Invalid file type. Allowed: PNG, JPG, JPEG")
    
    fname = f"logo_{uuid.uuid4()}{ext}"
    fpath = UPLOAD_DIR / fname
    
    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(400, "File is empty.")
        with open(fpath, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(500, f"File save failed: {str(e)}")
    
    # Ensure company_setup row exists
    existing = db.execute("SELECT id FROM company_setup LIMIT 1").fetchone()
    if existing:
        db.execute("UPDATE company_setup SET logo_path=? WHERE id=?", (str(fpath), existing["id"]))
    else:
        db.execute("INSERT INTO company_setup (logo_path) VALUES (?)", (str(fpath),))
    db.commit()
    
    logo_url = "/uploads/setup/" + fname
    return {"message": "Logo uploaded successfully.", "path": str(fpath), "url": logo_url}

@router.post("/upload-signature")
async def upload_signature(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    allowed = [".png", ".jpg", ".jpeg", ".gif", ".webp"]
    ext = pathlib.Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, "Invalid file type. Allowed: PNG, JPG, JPEG")
    
    fname = f"sig_{uuid.uuid4()}{ext}"
    fpath = UPLOAD_DIR / fname
    
    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(400, "File is empty.")
        with open(fpath, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(500, f"File save failed: {str(e)}")
    
    existing = db.execute("SELECT id FROM company_setup LIMIT 1").fetchone()
    if existing:
        db.execute("UPDATE company_setup SET signature_path=? WHERE id=?", (str(fpath), existing["id"]))
    else:
        db.execute("INSERT INTO company_setup (signature_path) VALUES (?)", (str(fpath),))
    db.commit()
    
    sig_url = "/uploads/setup/" + fname
    return {"message": "Signature uploaded successfully.", "path": str(fpath), "url": sig_url}
