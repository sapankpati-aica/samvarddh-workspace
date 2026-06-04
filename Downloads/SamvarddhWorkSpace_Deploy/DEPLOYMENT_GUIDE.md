# Samvarddh Work-Space ERP — Deployment Guide
## Developed by CA Sapan Pati | Samvarddh Associates Pvt. Ltd.

---

# OPTION A: RAILWAY.APP (RECOMMENDED — Easiest & Free)

## What you get:
- Live URL: https://samvarddh-XXXXX.railway.app/app
- Free 500 hours/month
- Persistent SQLite database
- No credit card needed

---

## STEP 1: Create GitHub Account (if you don't have one)
1. Go to https://github.com
2. Click "Sign Up" — use your email
3. Verify your email

---

## STEP 2: Install Git on your Windows PC
1. Go to https://git-scm.com/download/win
2. Download and install (click Next all the way through)
3. Restart your computer after install

---

## STEP 3: Upload code to GitHub
Open Command Prompt (type "cmd" in Windows search):

```
cd "C:\Users\Sapan Pati\Downloads"
mkdir samvarddh-deploy
cd samvarddh-deploy
```

Now copy the contents of SamvarddhWorkSpace_V9\samvarddh\backend 
and SamvarddhWorkSpace_V9\samvarddh\frontend into this folder.
Also copy Procfile, railway.json, requirements.txt, .gitignore from the deploy folder.

Then run:
```
git init
git add .
git commit -m "Initial deployment"
git branch -M main
```

Go to GitHub.com → New Repository → Name: "samvarddh-workspace" → Public → Create
Then run:
```
git remote add origin https://github.com/YOUR_USERNAME/samvarddh-workspace.git
git push -u origin main
```

---

## STEP 4: Deploy on Railway.app
1. Go to https://railway.app
2. Click "Sign In with GitHub" — use same GitHub account
3. Click "New Project"
4. Click "Deploy from GitHub repo"
5. Select "samvarddh-workspace"
6. Railway auto-detects Python and deploys!
7. Wait 2-3 minutes for deployment
8. Click "Generate Domain" → get your URL

---

## STEP 5: Set Environment Variables on Railway
In your Railway project → Settings → Variables → Add:
- DATA_DIR = /app/samvarddh_data

---

## STEP 6: Access your live app
Your URL will be: https://samvarddh-XXXXX.railway.app/app
Login: admin / admin123
CHANGE PASSWORD IMMEDIATELY after first login!

---

# OPTION B: RENDER.COM (Alternative Free Option)

1. Go to https://render.com
2. Sign Up with GitHub
3. New → Web Service → Connect your GitHub repo
4. Settings:
   - Build Command: pip install -r requirements.txt
   - Start Command: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
5. Click Deploy

Note: Render free tier sleeps after 15 min of inactivity.
First request after sleep takes ~30 seconds to wake up.

---

# IMPORTANT SECURITY NOTES FOR CLIENT DEMO

1. Change admin password immediately after deployment
2. Create a separate "demo" user with Viewer role for clients
3. Don't upload real client financial data to cloud demo
4. Use demo/test data only on cloud version

---

# KEEPING YOUR DATA SAFE

The cloud version uses a separate database.
Your local Windows version (in C:\SamvarddhWorkSpace) is your 
REAL production system and is completely separate.

---

# CUSTOM DOMAIN (Optional)
If you want samvarddh.com/app instead of railway.app:
- Buy domain at GoDaddy/BigRock (~Rs.500/year)
- In Railway: Settings → Custom Domain → Add your domain
- Point DNS to Railway as instructed

