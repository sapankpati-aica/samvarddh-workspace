"""Dashboard router — rich management analytics"""
from fastapi import APIRouter, Depends
from database import get_db
from routers.auth import get_current_user

router = APIRouter()

def q1(db, sql, params=()):
    row = db.execute(sql, params).fetchone()
    return row[0] if row else 0

@router.get("/summary")
def get_summary(current_user=Depends(get_current_user), db=Depends(get_db)):
    total_contract   = q1(db,"SELECT COALESCE(SUM(negotiated_amount),0) FROM quotations WHERE status='Finalised'")
    total_tax_inv    = q1(db,"SELECT COALESCE(SUM(total_amount),0) FROM invoices WHERE invoice_type='Tax'")
    total_reimb_inv  = q1(db,"SELECT COALESCE(SUM(total_amount),0) FROM invoices WHERE invoice_type='Reimbursement'")
    total_invoiced   = total_tax_inv + total_reimb_inv
    total_received   = q1(db,"SELECT COALESCE(SUM(amount),0) FROM receipts")
    tax_received     = q1(db,"SELECT COALESCE(SUM(r.amount),0) FROM receipts r JOIN invoices i ON r.invoice_id=i.id WHERE i.invoice_type='Tax'")
    reimb_received   = q1(db,"SELECT COALESCE(SUM(r.amount),0) FROM receipts r JOIN invoices i ON r.invoice_id=i.id WHERE i.invoice_type='Reimbursement'")
    active_projects  = q1(db,"SELECT COUNT(*) FROM clients WHERE status='Active'")
    total_clients    = q1(db,"SELECT COUNT(*) FROM clients")
    pending_proc     = q1(db,"SELECT COUNT(*) FROM procurement WHERE payment_status='Pending'")
    total_proc_amt   = q1(db,"SELECT COALESCE(SUM(amount),0) FROM procurement")
    conv_amt         = q1(db,"SELECT COALESCE(SUM(amount),0) FROM procurement WHERE entry_type='Conveyance'")
    pending_conv     = q1(db,"SELECT COUNT(*) FROM procurement WHERE entry_type='Conveyance' AND (approval_status='Pending' OR approval_status IS NULL)")
    draft_quotes     = q1(db,"SELECT COUNT(*) FROM quotations WHERE status='Draft'")
    final_quotes     = q1(db,"SELECT COUNT(*) FROM quotations WHERE status='Finalised'")
    draft_invoices   = q1(db,"SELECT COUNT(*) FROM invoices WHERE status='Draft'")
    total_employees  = q1(db,"SELECT COUNT(*) FROM employees WHERE status='Active'")

    # Client-wise full drill-down
    client_wise = db.execute("""
        SELECT c.id, c.client_name, c.project_type, c.lead_designer,
               COALESCE(q.contract,0) as contract_value,
               COALESCE(SUM(CASE WHEN i.invoice_type='Tax' THEN i.total_amount ELSE 0 END),0) as tax_invoiced,
               COALESCE(SUM(CASE WHEN i.invoice_type='Reimbursement' THEN i.total_amount ELSE 0 END),0) as reimb_invoiced,
               COALESCE(SUM(CASE WHEN i.invoice_type='Tax' THEN r.amount ELSE 0 END),0) as tax_collected,
               COALESCE(SUM(CASE WHEN i.invoice_type='Reimbursement' THEN r.amount ELSE 0 END),0) as reimb_collected,
               COALESCE(SUM(r.amount),0) as total_collected,
               COALESCE(SUM(i.total_amount),0) as total_invoiced,
               c.status
        FROM clients c
        LEFT JOIN (SELECT client_id, SUM(negotiated_amount) as contract FROM quotations WHERE status='Finalised' GROUP BY client_id) q ON q.client_id=c.id
        LEFT JOIN invoices i ON i.client_id=c.id
        LEFT JOIN receipts r ON r.invoice_id=i.id
        GROUP BY c.id, c.client_name
        ORDER BY contract_value DESC
    """).fetchall()

    # Monthly receipts — last 18 months
    monthly = db.execute("""
        SELECT strftime('%Y-%m', receipt_date) as month, SUM(amount) as amount
        FROM receipts WHERE receipt_date IS NOT NULL
        GROUP BY month ORDER BY month DESC LIMIT 18
    """).fetchall()

    # Quarterly receipts
    quarterly = db.execute("""
        SELECT strftime('%Y', receipt_date)||'-Q'||(CASE
            WHEN CAST(strftime('%m',receipt_date) AS INT) BETWEEN 1 AND 3 THEN '4'
            WHEN CAST(strftime('%m',receipt_date) AS INT) BETWEEN 4 AND 6 THEN '1'
            WHEN CAST(strftime('%m',receipt_date) AS INT) BETWEEN 7 AND 9 THEN '2'
            ELSE '3' END) as qtr,
            SUM(amount) as amount
        FROM receipts WHERE receipt_date IS NOT NULL
        GROUP BY qtr ORDER BY qtr DESC LIMIT 8
    """).fetchall()

    # Designer-wise revenue (from quotations/invoices by lead_designer)
    designer_wise = db.execute("""
        SELECT c.lead_designer as designer,
               COUNT(DISTINCT c.id) as client_count,
               COALESCE(SUM(q.negotiated_amount),0) as total_contract,
               COALESCE(SUM(r.amount),0) as total_collected
        FROM clients c
        LEFT JOIN quotations q ON q.client_id=c.id AND q.status='Finalised'
        LEFT JOIN invoices i ON i.client_id=c.id
        LEFT JOIN receipts r ON r.invoice_id=i.id
        WHERE c.lead_designer IS NOT NULL AND c.lead_designer != ''
        GROUP BY c.lead_designer
        ORDER BY total_contract DESC
    """).fetchall()

    # Work log status
    work_status = db.execute("SELECT status, COUNT(*) as count FROM work_logs GROUP BY status").fetchall()

    # Delayed tasks
    delayed_tasks = db.execute("""
        SELECT w.task, w.location, c.client_name, w.target_date, w.project_engineer,
               CAST(julianday('now') - julianday(w.target_date) AS INT) as delay_days
        FROM work_logs w LEFT JOIN clients c ON w.client_id=c.id
        WHERE w.status NOT IN ('Completed') AND w.target_date < date('now')
        ORDER BY delay_days DESC LIMIT 10
    """).fetchall()

    # Procurement category breakdown
    proc_by_cat = db.execute("""
        SELECT category, SUM(amount) as total, COUNT(*) as count
        FROM procurement WHERE category IS NOT NULL AND category != ''
        GROUP BY category ORDER BY total DESC
    """).fetchall()

    # Employee conveyance summary
    emp_conveyance = db.execute("""
        SELECT employee_name, COUNT(*) as trips,
               SUM(amount) as total_amount,
               SUM(CASE WHEN approval_status='Reimbursed' THEN amount ELSE 0 END) as reimbursed,
               SUM(CASE WHEN approval_status='Pending' OR approval_status IS NULL THEN amount ELSE 0 END) as pending
        FROM procurement WHERE entry_type='Conveyance' AND employee_name IS NOT NULL AND employee_name != ''
        GROUP BY employee_name ORDER BY total_amount DESC
    """).fetchall()

    # Work performance — engineer wise
    engineer_perf = db.execute("""
        SELECT project_engineer,
               COUNT(*) as total_tasks,
               SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) as completed,
               SUM(CASE WHEN status='Delayed' THEN 1 ELSE 0 END) as delayed,
               SUM(CASE WHEN status='In Progress' THEN 1 ELSE 0 END) as in_progress
        FROM work_logs WHERE project_engineer IS NOT NULL AND project_engineer != ''
        GROUP BY project_engineer ORDER BY total_tasks DESC
    """).fetchall()

    # Invoice aging — how old are outstanding invoices
    invoice_aging = db.execute("""
        SELECT i.invoice_number, i.invoice_type, c.client_name,
               i.total_amount,
               COALESCE(SUM(r.amount),0) as collected,
               i.total_amount - COALESCE(SUM(r.amount),0) as balance,
               CAST(julianday('now') - julianday(i.invoice_date) AS INT) as age_days
        FROM invoices i
        LEFT JOIN clients c ON i.client_id=c.id
        LEFT JOIN receipts r ON r.invoice_id=i.id
        WHERE i.status='Finalised'
        GROUP BY i.id
        HAVING balance > 0
        ORDER BY age_days DESC LIMIT 15
    """).fetchall()

    # Annual revenue summary
    annual = db.execute("""
        SELECT strftime('%Y', receipt_date) as year, SUM(amount) as amount
        FROM receipts WHERE receipt_date IS NOT NULL
        GROUP BY year ORDER BY year DESC LIMIT 5
    """).fetchall()

    return {
        "total_contract": total_contract,
        "total_invoiced": total_invoiced,
        "total_tax_invoice": total_tax_inv,
        "total_reimb_invoice": total_reimb_inv,
        "total_received": total_received,
        "tax_received": tax_received,
        "reimb_received": reimb_received,
        "balance_receivable": total_invoiced - total_received,
        "collection_pct": round(total_received/total_invoiced*100,1) if total_invoiced else 0,
        "active_projects": active_projects,
        "total_clients": total_clients,
        "draft_quotes": draft_quotes,
        "final_quotes": final_quotes,
        "draft_invoices": draft_invoices,
        "total_employees": total_employees,
        "pending_procurement": pending_proc,
        "total_procurement": total_proc_amt,
        "conveyance_total": conv_amt,
        "pending_conveyance_approvals": pending_conv,
        "client_wise": [dict(r) for r in client_wise],
        "monthly_receipts": [dict(r) for r in monthly],
        "quarterly_receipts": [dict(r) for r in quarterly],
        "annual_receipts": [dict(r) for r in annual],
        "designer_wise": [dict(r) for r in designer_wise],
        "work_status": [dict(r) for r in work_status],
        "delayed_tasks": [dict(r) for r in delayed_tasks],
        "proc_by_cat": [dict(r) for r in proc_by_cat],
        "emp_conveyance": [dict(r) for r in emp_conveyance],
        "engineer_perf": [dict(r) for r in engineer_perf],
        "invoice_aging": [dict(r) for r in invoice_aging],
    }

@router.get("/summary/filtered")
def get_summary_filtered(
    fy: str = None,
    quarter: str = None,
    city: str = None,
    client_id: int = None,
    project_manager: str = None,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    """Filtered dashboard — Financial Year, Quarter, City, Client, PM"""

    # Build date range from FY + Quarter
    date_cond = ""
    date_params = []

    if fy:
        # FY like "2025-26" => April 2025 to March 2026
        try:
            yr = int(fy.split("-")[0])
            fy_start = f"{yr}-04-01"
            fy_end   = f"{yr+1}-03-31"
            date_cond = "AND receipt_date BETWEEN ? AND ?"
            date_params = [fy_start, fy_end]

            if quarter:
                q_map = {
                    "Q1": (f"{yr}-04-01",   f"{yr}-06-30"),
                    "Q2": (f"{yr}-07-01",   f"{yr}-09-30"),
                    "Q3": (f"{yr}-10-01",   f"{yr}-12-31"),
                    "Q4": (f"{yr+1}-01-01", f"{yr+1}-03-31"),
                }
                if quarter in q_map:
                    qs, qe = q_map[quarter]
                    date_cond = "AND receipt_date BETWEEN ? AND ?"
                    date_params = [qs, qe]
        except Exception:
            pass

    # Client/city filter for clients table
    client_where = []
    client_params = []
    if city:
        client_where.append("(c.billing_address LIKE ? OR c.site_address LIKE ?)")
        client_params += [f"%{city}%", f"%{city}%"]
    if client_id:
        client_where.append("c.id = ?")
        client_params.append(client_id)
    if project_manager:
        client_where.append("c.project_manager LIKE ?")
        client_params.append(f"%{project_manager}%")
    client_filter = ("WHERE " + " AND ".join(client_where)) if client_where else ""

    # Receipts with date filter
    r_sql_base = f"SELECT COALESCE(SUM(r.amount),0) FROM receipts r JOIN invoices i ON r.invoice_id=i.id JOIN clients c ON i.client_id=c.id {client_filter} {'AND' if client_filter else 'WHERE'} r.receipt_date IS NOT NULL {date_cond}"
    def qf(extra_where="", params=[]):
        sql = r_sql_base.replace("IS NOT NULL "+date_cond, "IS NOT NULL "+date_cond+" "+extra_where)
        return db.execute(sql, client_params+date_params+params).fetchone()

    total_received = q1(db,
        f"SELECT COALESCE(SUM(r.amount),0) FROM receipts r JOIN invoices i ON r.invoice_id=i.id JOIN clients c ON i.client_id=c.id {client_filter} {'AND' if client_filter else 'WHERE'} r.receipt_date IS NOT NULL {date_cond}",
        client_params+date_params)

    # Total contract with filters
    total_contract = q1(db,
        f"SELECT COALESCE(SUM(q.negotiated_amount),0) FROM quotations q JOIN clients c ON q.client_id=c.id {client_filter} {'AND' if client_filter else 'WHERE'} q.status='Finalised'",
        client_params)

    # Procurement with filters
    proc_filter = client_filter.replace("c.", "c2.") if client_filter else ""
    total_proc = q1(db,
        f"SELECT COALESCE(SUM(p.amount),0) FROM procurement p JOIN clients c2 ON p.client_id=c2.id {proc_filter}",
        client_params)

    # Monthly collections filtered
    monthly = db.execute(
        f"SELECT strftime('%Y-%m', r.receipt_date) as month, SUM(r.amount) as amount FROM receipts r JOIN invoices i ON r.invoice_id=i.id JOIN clients c ON i.client_id=c.id {client_filter} {'AND' if client_filter else 'WHERE'} r.receipt_date IS NOT NULL {date_cond} GROUP BY month ORDER BY month DESC LIMIT 18",
        client_params+date_params).fetchall()

    # Quarterly filtered
    quarterly = db.execute(
        f"SELECT strftime('%Y', r.receipt_date)||'-Q'||(CASE WHEN CAST(strftime('%m',r.receipt_date) AS INT) BETWEEN 1 AND 3 THEN '4' WHEN CAST(strftime('%m',r.receipt_date) AS INT) BETWEEN 4 AND 6 THEN '1' WHEN CAST(strftime('%m',r.receipt_date) AS INT) BETWEEN 7 AND 9 THEN '2' ELSE '3' END) as qtr, SUM(r.amount) as amount FROM receipts r JOIN invoices i ON r.invoice_id=i.id JOIN clients c ON i.client_id=c.id {client_filter} {'AND' if client_filter else 'WHERE'} r.receipt_date IS NOT NULL {date_cond} GROUP BY qtr ORDER BY qtr DESC LIMIT 8",
        client_params+date_params).fetchall()

    # Client-wise filtered
    client_wise = db.execute(f"""
        SELECT c.id, c.client_name, c.project_type, c.lead_designer, c.project_manager,
               COALESCE(qt.contract,0) as contract_value,
               COALESCE(SUM(CASE WHEN i.invoice_type='Tax' THEN i.total_amount ELSE 0 END),0) as tax_invoiced,
               COALESCE(SUM(CASE WHEN i.invoice_type='Reimbursement' THEN i.total_amount ELSE 0 END),0) as reimb_invoiced,
               COALESCE(SUM(r.amount),0) as total_collected,
               COALESCE(SUM(i.total_amount),0) as total_invoiced,
               COALESCE(SUM(p.amount),0) as procurement_spent,
               c.status
        FROM clients c
        {client_filter}
        LEFT JOIN (SELECT client_id, SUM(negotiated_amount) as contract FROM quotations WHERE status='Finalised' GROUP BY client_id) qt ON qt.client_id=c.id
        LEFT JOIN invoices i ON i.client_id=c.id
        LEFT JOIN receipts r ON r.invoice_id=i.id {'AND r.receipt_date IS NOT NULL '+date_cond if date_cond else ''}
        LEFT JOIN procurement p ON p.client_id=c.id
        GROUP BY c.id ORDER BY contract_value DESC
    """, client_params+(date_params if date_cond else [])).fetchall()

    # Revenue vs Procurement (project-wise)
    rev_vs_proc = db.execute(f"""
        SELECT c.client_name,
               COALESCE(qt.contract,0) as contract_value,
               COALESCE(SUM(r.amount),0) as revenue_collected,
               COALESCE(SUM(p.amount),0) as total_procurement
        FROM clients c
        {client_filter}
        LEFT JOIN (SELECT client_id, SUM(negotiated_amount) as contract FROM quotations WHERE status='Finalised' GROUP BY client_id) qt ON qt.client_id=c.id
        LEFT JOIN invoices i ON i.client_id=c.id
        LEFT JOIN receipts r ON r.invoice_id=i.id
        LEFT JOIN procurement p ON p.client_id=c.id
        GROUP BY c.id ORDER BY contract_value DESC LIMIT 10
    """, client_params).fetchall()

    return {
        "total_contract": total_contract,
        "total_received": total_received,
        "total_procurement": total_proc,
        "balance_receivable": total_contract - total_received,
        "client_wise": [dict(r) for r in client_wise],
        "monthly_receipts": [dict(r) for r in monthly],
        "quarterly_receipts": [dict(r) for r in quarterly],
        "rev_vs_proc": [dict(r) for r in rev_vs_proc],
    }
