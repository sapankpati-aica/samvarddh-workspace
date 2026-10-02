# SAMVARDDH WORK-SPACE
## Complete Deployment Guide
### Samvarddh Associates Pvt. Ltd. | Bengaluru

---

## WHAT IS THIS?

Samvarddh Work-Space is a full-featured business ERP portal for interior design companies.

It covers the full project lifecycle:
> Client → Quotation → Design Files → Procurement → Work Progress → Invoice → Reimbursement → Receipts → Dashboard → Backup

---

## SYSTEM REQUIREMENTS

| Requirement | Minimum | Recommended |
|---|---|---|
| Operating System | Windows 10 | Windows 10/11 |
| RAM | 4 GB | 8 GB |
| Storage | 5 GB free | 20 GB free |
| Python | 3.10+ | 3.11+ |
| Internet | Required (first setup only) | Always-on recommended |
| Browser | Chrome 90+ | Chrome / Edge latest |

---

## STEP-BY-STEP DEPLOYMENT (YOUR COMPUTER FIRST)

---

### STEP 1 — INSTALL PYTHON

1. Open your browser and go to: **https://www.python.org/downloads/**
2. Click the big yellow button: **"Download Python 3.x.x"**
3. Run the downloaded `.exe` file
4. ⚠️ **VERY IMPORTANT**: On the first screen, tick the checkbox:
   **☑ Add Python to PATH** ← Do NOT skip this
5. Click **"Install Now"**
6. Wait for installation to complete, click **Close**

**Verify installation:**
- Press `Windows Key + R`, type `cmd`, press Enter
- Type: `python --version` → Should show: `Python 3.x.x`
- Type: `pip --version` → Should show pip version

---

### STEP 2 — EXTRACT THE PROJECT

1. Copy the `SamvarddhWorkSpace` folder to your computer
   - Recommended location: `C:\SamvarddhWorkSpace`
2. Your folder structure should look like this:

```
C:\SamvarddhWorkSpace\
├── backend\
│   ├── main.py
│   ├── database.py
│   ├── requirements.txt
│   └── routers\
│       ├── __init__.py
│       ├── auth.py
│       ├── users.py
│       ├── clients.py
│       ├── quotations.py
│       ├── designs.py
│       ├── procurement.py
│       ├── worklogs.py
│       ├── invoices.py
│       ├── dashboard.py
│       ├── employees.py
│       ├── setup.py
│       └── backup.py
├── frontend\
│   └── index.html
├── installer\
│   ├── SETUP.bat
│   └── START_SERVER.bat
└── DEPLOYMENT_GUIDE.md
```

---

### STEP 3 — RUN SETUP (ONE TIME ONLY)

1. Open the `installer` folder
2. **Right-click** on `SETUP.bat`
3. Click **"Run as administrator"**
4. The setup will:
   - Check Python installation ✅
   - Create required folders ✅
   - Install all packages ✅
   - Initialise the database ✅
5. Wait for: `SETUP COMPLETE!` message
6. Press any key to close

> ℹ️ This step requires internet connection. Takes 2-5 minutes.

---

### STEP 4 — START THE SERVER

1. Open the `installer` folder
2. **Double-click** `START_SERVER.bat`
3. A black window will appear — **keep it open**
4. Your browser will automatically open with the login page
5. Or manually go to: **http://localhost:8000/app**

---

### STEP 5 — FIRST LOGIN

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin123` |

1. Enter the credentials above
2. Click **Sign In**
3. You will be prompted to **change your password immediately**
4. Enter current password: `admin123`
5. Set a new strong password (minimum 6 characters)
6. You will be logged in after changing

---

### STEP 6 — INITIAL SETUP

After first login, do these steps in order:

#### 6A. Company Setup
1. Click **⚙️ Setup** in the left sidebar
2. Fill in all company details:
   - Brand Name: `SAMVARDDH`
   - Legal Name: `Samvarddh Associates Private Ltd.`
   - GSTIN, PAN, Phone, Email, Website
   - Bank details for invoice printing
   - Default Terms (GST Rule 33 clause is pre-filled)
3. Upload company **Logo** (PNG/JPG)
4. Upload **Authorised Signatory Signature** image
5. Click **💾 Save Setup**

#### 6B. Create Users
1. Click **🔐 User Management**
2. For each team member, click **✚ Create User**
3. Fill: Full Name, Username, Temporary Password, Role, Designation
4. Click **✚ Create User**
5. Share the username and temporary password with the team member
6. They will be forced to change their password on first login

**Available Roles:**
| Role | Who Uses It |
|---|---|
| Admin | You (CA Sahab / Priyanka Ma'am) |
| Management | Senior management viewing reports |
| Lead Designer | Senior designers |
| Project Manager | Project coordinators |
| Project Engineer | Site engineers |
| Accounts | Billing and invoice team |
| Viewer | Read-only access for investors etc. |

#### 6C. Add Employees
1. Click **🏢 Employees**
2. Add all employees with their designation
3. These will be used in client and project assignment

---

### STEP 7 — DAILY WORKFLOW

```
NEW PROJECT WORKFLOW:
─────────────────────────────────────────────────────────
1. 👥 CLIENTS    → Add client with all project details
2. 📋 QUOTATION  → Create quotation with line items
                    → Save as Draft → Finalise after approval
3. 🎨 DESIGN     → Upload design PDFs version-wise
4. 🛒 PROCUREMENT → Log all material purchases
5. 📓 WORK LOG   → Update daily site progress
6. 🧾 INVOICES   → Create Tax Invoice (50%)
                    → Create Reimbursement Invoice (50%)
                    → Add receipts as payments come in
7. 📊 DASHBOARD  → Track everything in real-time
```

---

## TEAM ACCESS (OFFICE LAN)

Once the server is running on your main computer:

1. Note the **LAN IP address** shown in the START_SERVER window
   Example: `http://192.168.1.25:8000/app`
2. Share this URL with your team
3. They can open it in their browser on the same WiFi/LAN
4. Each person logs in with their own username and password
5. **Main computer must stay ON** for others to access

**To find your IP manually:**
- Press `Windows Key + R`, type `cmd`
- Type: `ipconfig`
- Look for: `IPv4 Address . . . . . : 192.168.x.x`

---

## DATA & BACKUP

### Where is your data stored?

```
C:\SamvarddhWorkSpace\
└── samvarddh_data\           ← ⚠️ PROTECT THIS FOLDER
    ├── samvarddh_portal.db   ← All business data
    ├── uploads\              ← All uploaded files
    │   ├── designs\          ← Design PDFs
    │   ├── procurement\      ← Vendor bills
    │   └── setup\            ← Logo & signature
    ├── reports\
    └── backups\              ← Backup ZIP files
```

### How to take backup?

1. Click **💾 Backup** in the sidebar
2. Click **"Create Backup Now"**
3. A ZIP file is created in `samvarddh_data\backups\`
4. Download it and store on:
   - External hard drive
   - Pen drive
   - Google Drive (manual upload for now)

**Backup Policy:**
- ✅ Before every system update
- ✅ Every Friday (end of week)
- ✅ End of every month
- ✅ Before adding major data

---

## STOPPING THE SERVER

- Simply **close the black START_SERVER window**
- Or press `Ctrl + C` in that window

The application will stop and team members cannot access it until you start it again.

---

## TROUBLESHOOTING

### Problem: Browser shows "This site can't be reached"
**Solution:** Make sure START_SERVER.bat is running. The black window must be open.

### Problem: "Python not found" during setup
**Solution:** Reinstall Python from python.org and ensure "Add to PATH" is ticked.

### Problem: "Port 8000 already in use"
**Solution:** 
- Open Task Manager → Find Python process → End task
- Or restart the computer and try again

### Problem: Package installation fails
**Solution:**
- Check internet connection
- Run CMD as Administrator and type:
  `pip install fastapi uvicorn[standard] python-multipart pydantic bcrypt PyJWT reportlab openpyxl pandas Pillow`

### Problem: Login not working
**Solution:** 
- Default: `admin` / `admin123`
- If you've changed it and forgotten, contact technical support

---

## DEPLOYING ON PRIYANKA MA'AM'S COMPUTER (AFTER TESTING)

Once you have tested everything on your system:

1. **Take a backup** from the Backup tab
2. Copy entire `SamvarddhWorkSpace` folder to her computer
3. Copy your `samvarddh_data` folder into her `SamvarddhWorkSpace`
4. Run `SETUP.bat` on her computer (one time)
5. Run `START_SERVER.bat` to start
6. **All your data, clients, quotations will be there** (transferred via the data folder)

---

## FUTURE CLOUD DEPLOYMENT

When ready to go live on the internet:

| Item | Solution |
|---|---|
| Hosting | Railway.app or Render.com (free tier available) |
| Database | PostgreSQL (upgrade from SQLite — same code) |
| File Storage | Google Drive API or AWS S3 |
| Domain | workspace.samvarddh.com |
| SSL | Auto-provided by hosting platform |
| Backup | Automated daily backup |

**Estimated cloud cost:** ₹2,000 - ₹5,000/month depending on usage.

---

## SUPPORT & NEXT STEPS

After testing on your system, the following can be added:

- [ ] Professional branded PDF templates with logo
- [ ] Auto invoice numbering by financial year (SAM-TAX-2026-001)
- [ ] WhatsApp notification on invoice creation
- [ ] Email quotation sharing
- [ ] Google Drive integration for design file storage
- [ ] Mobile-responsive view for site engineers
- [ ] GST return reports
- [ ] Project profitability reports

---

*Samvarddh Work-Space | Built for Samvarddh Associates Pvt. Ltd.*
*Enriching Lives · Bengaluru, Karnataka*
