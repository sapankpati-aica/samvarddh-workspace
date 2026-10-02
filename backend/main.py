"""
Samvarddh Work-Space Backend
FastAPI + SQLite | Serves both API and Frontend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import pathlib

from database import init_db
from routers import auth, users, clients, quotations, designs, procurement, worklogs, invoices, dashboard, employees, setup, backup, suppliers

app = FastAPI(
    title="Samvarddh Work-Space API",
    description="Interior Design ERP for Samvarddh Associates Pvt. Ltd.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api/auth",        tags=["Auth"])
app.include_router(users.router,       prefix="/api/users",       tags=["Users"])
app.include_router(clients.router,     prefix="/api/clients",     tags=["Clients"])
app.include_router(quotations.router,  prefix="/api/quotations",  tags=["Quotations"])
app.include_router(designs.router,     prefix="/api/designs",     tags=["Designs"])
app.include_router(procurement.router, prefix="/api/procurement", tags=["Procurement"])
app.include_router(worklogs.router,    prefix="/api/worklogs",    tags=["WorkLogs"])
app.include_router(invoices.router,    prefix="/api/invoices",    tags=["Invoices"])
app.include_router(dashboard.router,   prefix="/api/dashboard",   tags=["Dashboard"])
app.include_router(employees.router,   prefix="/api/employees",   tags=["Employees"])
app.include_router(setup.router,       prefix="/api/setup",       tags=["Setup"])
app.include_router(backup.router,      prefix="/api/backup",      tags=["Backup"])
app.include_router(suppliers.router,   prefix="/api/suppliers",   tags=["Suppliers"])

uploads_path = pathlib.Path("samvarddh_data/uploads")
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

FRONTEND = pathlib.Path(__file__).parent.parent / "frontend" / "index.html"

@app.get("/app", response_class=HTMLResponse)
@app.get("/app/", response_class=HTMLResponse)
def serve_frontend():
    if FRONTEND.exists():
        return HTMLResponse(content=FRONTEND.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>Frontend not found.</h2>", status_code=404)

@app.get("/")
def root():
    return {"message": "Samvarddh Work-Space", "open_app": "/app", "api_docs": "/docs"}

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@app.on_event("startup")
async def startup():
    init_db()
    print("\n✅ Samvarddh Work-Space is running!")
    print("📱 Open in browser: http://localhost:8000/app")
    print("🌐 For office LAN: http://<your-ip>:8000/app\n")
