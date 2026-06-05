"""Work Progress Log router"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db
from routers.auth import get_current_user, log_audit

router = APIRouter()

STATUSES = ["Not Started","In Progress","Completed","On Hold","Delayed"]

class WorkLogCreate(BaseModel):
    client_id: int
    quotation_id: Optional[int] = None
    location: str
    task: str
    target_date: str
    actual_completion_date: Optional[str] = ""
    status: str = "Not Started"
    project_engineer: Optional[str] = ""
    work_done: Optional[str] = ""
    issues: Optional[str] = ""
    next_action: Optional[str] = ""

@router.get("/")
def list_logs(client_id: Optional[int] = None, current_user=Depends(get_current_user), db=Depends(get_db)):
    q = "SELECT w.*,c.client_name FROM work_logs w LEFT JOIN clients c ON w.client_id=c.id WHERE 1=1"
    params = []
    if client_id: q += " AND w.client_id=?"; params.append(client_id)
    q += " ORDER BY w.target_date, w.id"
    rows = db.execute(q, params).fetchall()
    return [dict(r) for r in rows]

@router.post("/")
def create_log(data: WorkLogCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("""INSERT INTO work_logs (client_id,quotation_id,location,task,target_date,actual_completion_date,status,project_engineer,work_done,issues,next_action,created_by,created_date)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (data.client_id, data.quotation_id, data.location, data.task,
                data.target_date, data.actual_completion_date, data.status,
                data.project_engineer, data.work_done, data.issues,
                data.next_action, current_user["sub"], datetime.now().isoformat()))
    db.commit()
    return {"message": "Work log added."}

@router.put("/{log_id}")
def update_log(log_id: int, data: WorkLogCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("""UPDATE work_logs SET location=?,task=?,target_date=?,actual_completion_date=?,status=?,project_engineer=?,work_done=?,issues=?,next_action=? WHERE id=?""",
               (data.location, data.task, data.target_date, data.actual_completion_date,
                data.status, data.project_engineer, data.work_done, data.issues,
                data.next_action, log_id))
    db.commit()
    return {"message": "Updated."}

@router.delete("/{log_id}")
def delete_log(log_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("DELETE FROM work_logs WHERE id=?", (log_id,))
    db.commit()
    return {"message": "Deleted."}

@router.get("/performance-report")
def performance_report(current_user=Depends(get_current_user), db=Depends(get_db)):
    rows = db.execute("""
        SELECT c.client_name, w.location, w.task, w.project_engineer,
               w.target_date, w.actual_completion_date, w.status,
               CASE WHEN w.actual_completion_date > w.target_date
                    THEN CAST(julianday(w.actual_completion_date) - julianday(w.target_date) AS INTEGER)
                    ELSE 0 END as delay_days,
               CASE WHEN w.status='Completed' AND w.actual_completion_date <= w.target_date THEN 'On Time'
                    WHEN w.status='Completed' AND w.actual_completion_date > w.target_date THEN 'Delayed'
                    WHEN w.target_date < date('now') AND w.status != 'Completed' THEN 'Overdue'
                    ELSE 'On Track' END as performance_remark
        FROM work_logs w LEFT JOIN clients c ON w.client_id=c.id
        ORDER BY w.target_date
    """).fetchall()
    return [dict(r) for r in rows]
