"""Invoices router - Full receivable reconciliation with date-wise receipts"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from database import get_db
from routers.auth import get_current_user, log_audit

router = APIRouter()

GST_CLAUSE = ("GST is charged under Section 15 on the supply of service and GST is not "
              "chargeable on the value of reimbursements for the expenses made as pure agent "
              "of the client as per Rule 33 of the CGST Rules, 2017.")

class InvoiceCreate(BaseModel):
    invoice_number: str
    invoice_type: str
    client_id: int
    quotation_id: Optional[int] = None
    invoice_date: str
    gst_type: Optional[str] = "Intra-State"
    taxable_value: float = 0
    reimbursement_amount: float = 0
    terms: Optional[str] = ""
    payment_terms: Optional[str] = ""
    notes: Optional[str] = ""

class ReceiptCreate(BaseModel):
    invoice_id: int
    invoice_number: str
    invoice_type: str
    receipt_date: str
    amount: float
    mode: Optional[str] = "Bank Transfer"
    reference_number: Optional[str] = ""
    remarks: Optional[str] = ""

def calc_gst(taxable: float, gst_type: str, gst_rate: float = 18):
    if gst_type == "Inter-State":
        igst = round(taxable * gst_rate / 100, 2)
        return 0, 0, igst, round(taxable + igst, 2)
    else:
        half = round(taxable * gst_rate / 2 / 100, 2)
        return half, half, 0, round(taxable + half * 2, 2)

@router.get("/")
def list_invoices(
    client_id: Optional[int] = None,
    invoice_type: Optional[str] = None,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    q = """SELECT i.*,c.client_name,c.phone,c.gstin,c.billing_address,
           COALESCE((SELECT SUM(amount) FROM receipts WHERE invoice_id=i.id),0) as total_received
           FROM invoices i LEFT JOIN clients c ON i.client_id=c.id WHERE 1=1"""
    params = []
    if client_id:
        q += " AND i.client_id=?"; params.append(client_id)
    if invoice_type:
        q += " AND i.invoice_type=?"; params.append(invoice_type)
    q += " ORDER BY i.id DESC"
    rows = db.execute(q, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["balance"] = round(d["total_amount"] - d["total_received"], 2)
        result.append(d)
    return result

@router.post("/")
def create_invoice(data: InvoiceCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    existing = db.execute("SELECT id FROM invoices WHERE invoice_number=?",
                          (data.invoice_number,)).fetchone()
    if existing:
        raise HTTPException(400, f"Invoice number '{data.invoice_number}' already exists.")

    setup = db.execute("SELECT * FROM company_setup LIMIT 1").fetchone()
    terms = data.terms or (setup["default_terms"] if setup else GST_CLAUSE)
    if GST_CLAUSE not in (terms or ""):
        terms = (terms or "") + "\n\n" + GST_CLAUSE

    cgst = sgst = igst = total = 0
    if data.invoice_type == "Tax":
        cgst, sgst, igst, total = calc_gst(data.taxable_value, data.gst_type or "Intra-State")
    else:
        total = data.reimbursement_amount

    db.execute("""INSERT INTO invoices 
                  (invoice_number,invoice_type,client_id,quotation_id,invoice_date,gst_type,
                   taxable_value,reimbursement_amount,cgst,sgst,igst,total_amount,
                   terms,payment_terms,notes,status,created_by,created_date)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (data.invoice_number, data.invoice_type, data.client_id, data.quotation_id,
                data.invoice_date, data.gst_type, data.taxable_value,
                data.reimbursement_amount, cgst, sgst, igst, total,
                terms, data.payment_terms, data.notes,
                "Draft", current_user["sub"], datetime.now().isoformat()))
    db.commit()
    log_audit(db, current_user["sub"], "Create Invoice", "Invoices",
              f"Inv: {data.invoice_number} | Type: {data.invoice_type} | Amt: {total}")
    return {"message": f"Invoice {data.invoice_number} created successfully."}

@router.get("/{inv_id}")
def get_invoice(inv_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("""SELECT i.*,c.client_name,c.phone,c.email,c.billing_address,c.gstin,c.site_address
                        FROM invoices i LEFT JOIN clients c ON i.client_id=c.id WHERE i.id=?""",
                     (inv_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Invoice not found.")
    receipts = db.execute(
        "SELECT * FROM receipts WHERE invoice_id=? ORDER BY receipt_date",
        (inv_id,)).fetchall()
    result = dict(row)
    result["receipts"] = [dict(r) for r in receipts]
    result["total_received"] = sum(r["amount"] for r in receipts)
    result["balance"] = round(result["total_amount"] - result["total_received"], 2)
    return result

@router.put("/{inv_id}")
def update_invoice(inv_id: int, data: InvoiceCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT status FROM invoices WHERE id=?", (inv_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Not found.")
    if row["status"] == "Finalised":
        raise HTTPException(400, "Finalised invoices cannot be modified.")
    cgst = sgst = igst = total = 0
    if data.invoice_type == "Tax":
        cgst, sgst, igst, total = calc_gst(data.taxable_value, data.gst_type or "Intra-State")
    else:
        total = data.reimbursement_amount
    db.execute("""UPDATE invoices SET invoice_date=?,gst_type=?,taxable_value=?,reimbursement_amount=?,
                  cgst=?,sgst=?,igst=?,total_amount=?,terms=?,payment_terms=?,notes=? WHERE id=?""",
               (data.invoice_date, data.gst_type, data.taxable_value, data.reimbursement_amount,
                cgst, sgst, igst, total, data.terms, data.payment_terms, data.notes, inv_id))
    db.commit()
    return {"message": "Invoice updated."}

@router.post("/{inv_id}/finalise")
def finalise_invoice(inv_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT * FROM invoices WHERE id=?", (inv_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Not found.")
    if row["status"] == "Finalised":
        raise HTTPException(400, "Already finalised.")
    db.execute("UPDATE invoices SET status='Finalised', finalised_date=? WHERE id=?",
               (datetime.now().isoformat(), inv_id))
    db.commit()
    log_audit(db, current_user["sub"], "Finalise Invoice", "Invoices",
              f"Inv ID: {inv_id} | No: {row['invoice_number']}")
    return {"message": "Invoice finalised and locked."}

@router.delete("/{inv_id}")
def delete_invoice(inv_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT status FROM invoices WHERE id=?", (inv_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Not found.")
    if row["status"] == "Finalised":
        raise HTTPException(400, "Finalised invoices cannot be deleted.")
    db.execute("DELETE FROM receipts WHERE invoice_id=?", (inv_id,))
    db.execute("DELETE FROM invoices WHERE id=?", (inv_id,))
    db.commit()
    log_audit(db, current_user["sub"], "Delete Invoice", "Invoices", f"Inv ID: {inv_id}")
    return {"message": "Invoice deleted."}

# ---- RECEIPTS ----
@router.post("/receipts/add")
def add_receipt(data: ReceiptCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    if data.amount <= 0:
        raise HTTPException(400, "Amount must be greater than zero.")
    
    # Check if receipt would exceed invoice total
    inv = db.execute("SELECT total_amount FROM invoices WHERE id=?", (data.invoice_id,)).fetchone()
    if inv:
        already = db.execute("SELECT COALESCE(SUM(amount),0) FROM receipts WHERE invoice_id=?",
                             (data.invoice_id,)).fetchone()[0]
        if already + data.amount > inv["total_amount"] + 0.01:
            raise HTTPException(400, f"Receipt amount exceeds invoice balance. Balance: ₹{inv['total_amount']-already:,.2f}")

    db.execute("""INSERT INTO receipts 
                  (invoice_id,invoice_number,invoice_type,receipt_date,amount,mode,
                   reference_number,remarks,created_by,created_date)
                  VALUES (?,?,?,?,?,?,?,?,?,?)""",
               (data.invoice_id, data.invoice_number, data.invoice_type,
                data.receipt_date, data.amount, data.mode,
                data.reference_number, data.remarks,
                current_user["sub"], datetime.now().isoformat()))
    db.commit()
    log_audit(db, current_user["sub"], "Receipt Entry", "Invoices",
              f"Inv {data.invoice_number}: Rs.{data.amount:,.0f} on {data.receipt_date} via {data.mode}")
    return {"message": f"Receipt of Rs.{data.amount:,.0f} recorded for {data.receipt_date}."}

@router.delete("/receipts/{receipt_id}")
def delete_receipt(receipt_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("DELETE FROM receipts WHERE id=?", (receipt_id,))
    db.commit()
    return {"message": "Receipt deleted."}

@router.get("/receipts/reconciliation")
def get_reconciliation(
    client_id: Optional[int] = None,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    """Date-wise reconciliation matrix per invoice"""
    cond = f"AND i.client_id={client_id}" if client_id else ""
    
    # Get all invoices with totals
    invoices = db.execute(f"""
        SELECT i.id, i.invoice_number, i.invoice_type, i.invoice_date,
               i.total_amount, i.status, i.client_id, c.client_name
        FROM invoices i LEFT JOIN clients c ON i.client_id=c.id
        WHERE 1=1 {cond}
        ORDER BY i.invoice_type, i.id
    """).fetchall()

    # Get all receipts
    receipts = db.execute(f"""
        SELECT r.*, i.client_id
        FROM receipts r
        JOIN invoices i ON r.invoice_id=i.id
        WHERE 1=1 {cond}
        ORDER BY r.receipt_date
    """).fetchall()

    # Build per-invoice receipt data
    result = []
    for inv in invoices:
        inv_dict = dict(inv)
        inv_receipts = [dict(r) for r in receipts if r["invoice_id"] == inv["id"]]
        inv_dict["receipts"] = inv_receipts
        inv_dict["total_received"] = sum(r["amount"] for r in inv_receipts)
        inv_dict["balance"] = round(inv["total_amount"] - inv_dict["total_received"], 2)
        # Date-wise breakdown
        date_map = {}
        for r in inv_receipts:
            dt = r["receipt_date"]
            date_map[dt] = date_map.get(dt, 0) + r["amount"]
        inv_dict["date_wise"] = date_map
        result.append(inv_dict)

    return result

@router.get("/receipts/all")
def get_all_receipts(
    client_id: Optional[int] = None,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    cond = f"AND i.client_id={client_id}" if client_id else ""
    rows = db.execute(f"""
        SELECT r.*, i.total_amount, i.status as inv_status, i.invoice_type,
               c.client_name
        FROM receipts r
        LEFT JOIN invoices i ON r.invoice_id=i.id
        LEFT JOIN clients c ON i.client_id=c.id
        WHERE 1=1 {cond}
        ORDER BY r.receipt_date DESC, r.id DESC
    """).fetchall()
    return [dict(r) for r in rows]

@router.get("/receipts/aging")
def get_aging_report(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Receivables aging report"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    rows = db.execute(f"""
        SELECT i.invoice_number, i.invoice_type, i.invoice_date, i.total_amount,
               i.status, c.client_name,
               COALESCE((SELECT SUM(amount) FROM receipts WHERE invoice_id=i.id),0) as received,
               i.total_amount - COALESCE((SELECT SUM(amount) FROM receipts WHERE invoice_id=i.id),0) as balance,
               CAST(julianday('{today_str}') - julianday(i.invoice_date) AS INTEGER) as age_days
        FROM invoices i
        LEFT JOIN clients c ON i.client_id=c.id
        WHERE i.total_amount > COALESCE((SELECT SUM(amount) FROM receipts WHERE invoice_id=i.id),0)
        ORDER BY age_days DESC
    """).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        age = d["age_days"] or 0
        if age <= 30:
            d["aging_bucket"] = "0-30 days"
        elif age <= 60:
            d["aging_bucket"] = "31-60 days"
        elif age <= 90:
            d["aging_bucket"] = "61-90 days"
        else:
            d["aging_bucket"] = "90+ days"
        result.append(d)
    return result
