"""Quotations router - Full CRUD including Edit/Modify"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from database import get_db
from routers.auth import get_current_user, log_audit

router = APIRouter()

LOCATIONS = ["Design Fees","Foyer","Living Area","Dining & Kitchen","Utility",
             "Bedroom 1","Bedroom 2","Master Bedroom","Washroom","Flooring",
             "Electrical Work","Painting","Breaking and Debris Removal",
             "Balcony","Plumbing","Other"]

ELEMENTS = ["Design Fees","Designer Wall","Shoe Rack","Tall Cabinet","Cabinet Wall",
            "TV Unit","Panelling","False Fire Place","Partition","Foldable French Door",
            "Lower Cabinet","Middle Cabinet","Glass Shutter","Upper Cabinet / Loft",
            "Tall Unit","Backtiles","Hardware","Bottle Pull Out","Granite","Installation",
            "Sink","S Corner","Walk-in Wardrobe","Wardrobe","Face Door","Cabinets",
            "Mirror","Vanity","Glass","Tiles","Full Body Tile","Pelmet","Drawers",
            "Feature Wall","Storage Unit","Study Table","Washroom Door","Panel Lights",
            "Strip Light","Balcony Glass Boundary","Painting","Labour","Light Fixture",
            "Other"]

class LineItem(BaseModel):
    location: str
    element: str
    length_ft: float = 0
    breadth_ft: float = 1
    height_ft: float = 0
    qty: float = 0
    rate: float = 0
    remarks: str = ""
    sort_order: int = 0

class QuotationCreate(BaseModel):
    quotation_number: str
    client_id: int
    quotation_date: str
    project_name: Optional[str] = ""
    financial_year: Optional[str] = ""
    gst_rate: float = 18
    gst_type: str = "Intra-State"
    discount: float = 0
    negotiated_amount: float = 0
    approver_name: Optional[str] = ""
    terms: Optional[str] = ""
    payment_terms: Optional[str] = ""
    items: List[LineItem] = []

@router.get("/locations")
def get_locations(): return LOCATIONS

@router.get("/elements")
def get_elements(): return ELEMENTS

@router.get("/")
def list_quotations(
    client_id: Optional[int] = None,
    fy: Optional[str] = None,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    q = """SELECT q.*, c.client_name, c.phone, c.email, c.billing_address, c.gstin,
           COALESCE((SELECT SUM(amount) FROM quotation_items WHERE quotation_id=q.id),0) as line_total
           FROM quotations q LEFT JOIN clients c ON q.client_id=c.id WHERE 1=1"""
    params = []
    if client_id:
        q += " AND q.client_id=?"; params.append(client_id)
    if fy:
        q += " AND q.financial_year=?"; params.append(fy)
    q += " ORDER BY q.id DESC"
    rows = db.execute(q, params).fetchall()
    return [dict(r) for r in rows]

@router.post("/")
def create_quotation(data: QuotationCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    existing = db.execute("SELECT id FROM quotations WHERE quotation_number=?", (data.quotation_number,)).fetchone()
    if existing:
        raise HTTPException(400, f"Quotation number '{data.quotation_number}' already exists.")
    cur = db.execute("""INSERT INTO quotations 
                        (quotation_number,client_id,quotation_date,project_name,financial_year,
                         gst_rate,gst_type,discount,negotiated_amount,approver_name,terms,
                         payment_terms,status,created_by,created_date)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (data.quotation_number, data.client_id, data.quotation_date,
                      data.project_name, data.financial_year, data.gst_rate,
                      data.gst_type, data.discount, data.negotiated_amount,
                      data.approver_name, data.terms, data.payment_terms,
                      "Draft", current_user["sub"], datetime.now().isoformat()))
    q_id = cur.lastrowid
    _save_items(db, q_id, data.items)
    db.commit()
    log_audit(db, current_user["sub"], "Create Quotation", "Quotations", f"Q No: {data.quotation_number}")
    return {"id": q_id, "message": "Quotation saved as Draft."}

@router.get("/{q_id}")
def get_quotation(q_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("""SELECT q.*,c.client_name,c.phone,c.email,c.billing_address,c.gstin,c.site_address
                        FROM quotations q LEFT JOIN clients c ON q.client_id=c.id WHERE q.id=?""",
                     (q_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Quotation not found.")
    items = db.execute("SELECT * FROM quotation_items WHERE quotation_id=? ORDER BY sort_order,id",
                       (q_id,)).fetchall()
    result = dict(row)
    result["items"] = [dict(i) for i in items]
    return result

@router.put("/{q_id}")
def update_quotation(q_id: int, data: QuotationCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT status FROM quotations WHERE id=?", (q_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Quotation not found.")
    if row["status"] == "Finalised":
        raise HTTPException(400, "Finalised quotations cannot be modified.")
    db.execute("""UPDATE quotations SET client_id=?,quotation_date=?,project_name=?,financial_year=?,
                  gst_rate=?,gst_type=?,discount=?,negotiated_amount=?,approver_name=?,
                  terms=?,payment_terms=? WHERE id=?""",
               (data.client_id, data.quotation_date, data.project_name,
                data.financial_year, data.gst_rate, data.gst_type,
                data.discount, data.negotiated_amount, data.approver_name,
                data.terms, data.payment_terms, q_id))
    db.execute("DELETE FROM quotation_items WHERE quotation_id=?", (q_id,))
    _save_items(db, q_id, data.items)
    db.commit()
    log_audit(db, current_user["sub"], "Update Quotation", "Quotations", f"Q ID: {q_id}")
    return {"message": "Quotation updated successfully."}

@router.post("/{q_id}/finalise")
def finalise_quotation(q_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT * FROM quotations WHERE id=?", (q_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Not found.")
    if row["status"] == "Finalised":
        raise HTTPException(400, "Already finalised.")
    if not row["approver_name"] or not row["approver_name"].strip():
        raise HTTPException(400, "Approver Name is mandatory before finalising quotation.")
    db.execute("UPDATE quotations SET status='Finalised', finalised_date=? WHERE id=?",
               (datetime.now().isoformat(), q_id))
    db.commit()
    log_audit(db, current_user["sub"], "Finalise Quotation", "Quotations", f"Q ID: {q_id}")
    return {"message": "Quotation finalised and locked successfully."}

def _save_items(db, q_id, items):
    for i, item in enumerate(items):
        qty = item.qty if item.qty > 0 else round(item.length_ft * item.breadth_ft * item.height_ft, 3)
        amount = round(qty * item.rate, 2)
        db.execute("""INSERT INTO quotation_items 
                      (quotation_id,location,element,length_ft,breadth_ft,height_ft,qty,rate,amount,remarks,sort_order)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                   (q_id, item.location, item.element, item.length_ft,
                    item.breadth_ft, item.height_ft, qty, item.rate,
                    amount, item.remarks, i))


@router.get("/project-report/{client_id}")
def get_project_report(client_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Full project report for PDF generation"""
    from routers.auth import log_audit

    client = db.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    if not client:
        raise HTTPException(404, "Client not found.")

    quotations = db.execute(
        "SELECT * FROM quotations WHERE client_id=? AND status='Finalised' ORDER BY quotation_date",
        (client_id,)).fetchall()

    q_ids = [q["id"] for q in quotations]
    items_map = {}
    for qid in q_ids:
        items = db.execute("SELECT * FROM quotation_items WHERE quotation_id=?", (qid,)).fetchall()
        items_map[qid] = [dict(i) for i in items]

    design_files = db.execute(
        "SELECT * FROM design_files WHERE client_id=? ORDER BY upload_date DESC",
        (client_id,)).fetchall()

    procurement = db.execute(
        "SELECT * FROM procurement WHERE client_id=? ORDER BY procurement_date",
        (client_id,)).fetchall()

    invoices = db.execute(
        "SELECT * FROM invoices WHERE client_id=? ORDER BY invoice_date",
        (client_id,)).fetchall()

    inv_ids = [i["id"] for i in invoices]
    receipts_map = {}
    for iid in inv_ids:
        recs = db.execute("SELECT * FROM receipts WHERE invoice_id=? ORDER BY receipt_date", (iid,)).fetchall()
        receipts_map[iid] = [dict(r) for r in recs]

    work_logs = db.execute(
        "SELECT w.*, c.client_name FROM work_logs w LEFT JOIN clients c ON w.client_id=c.id WHERE w.client_id=? ORDER BY w.target_date",
        (client_id,)).fetchall()

    total_contract  = sum(q["negotiated_amount"] or 0 for q in quotations)
    total_proc      = sum(p["amount"] or 0 for p in procurement)
    total_invoiced  = sum(i["total_amount"] or 0 for i in invoices)
    all_receipts    = db.execute(
        "SELECT r.* FROM receipts r JOIN invoices i ON r.invoice_id=i.id WHERE i.client_id=? ORDER BY r.receipt_date",
        (client_id,)).fetchall()
    total_received  = sum(r["amount"] or 0 for r in all_receipts)

    return {
        "client":         dict(client),
        "quotations":     [dict(q) for q in quotations],
        "items_map":      items_map,
        "design_files":   [dict(d) for d in design_files],
        "procurement":    [dict(p) for p in procurement],
        "invoices":       [dict(i) for i in invoices],
        "receipts_map":   receipts_map,
        "all_receipts":   [dict(r) for r in all_receipts],
        "work_logs":      [dict(w) for w in work_logs],
        "summary": {
            "total_contract":  total_contract,
            "total_procurement": total_proc,
            "total_invoiced":  total_invoiced,
            "total_received":  total_received,
            "balance":         total_invoiced - total_received,
            "gross_margin":    total_contract - total_proc,
        }
    }
