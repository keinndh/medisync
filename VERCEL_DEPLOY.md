# Deploying MediSync to Vercel

## Prerequisites
- Vercel account (vercel.com) — free tier works
- PostgreSQL database (use Neon.tech — free, works great with Vercel)
- GitHub account (push your code here first)

---

## Step 1 — Push to GitHub
1. Create a new repo on github.com (e.g. `medisync`)
2. Upload all these project files to it

---

## Step 2 — Create a free PostgreSQL database (Neon.tech)
1. Go to neon.tech → Sign up free
2. Create a new project → copy the **Connection string** (looks like `postgresql://user:pass@host/db`)

---

## Step 3 — Deploy on Vercel
1. Go to vercel.com → Add New Project
2. Import your GitHub repo
3. **Framework Preset**: select **Other**
4. Click **Environment Variables** and add:

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | your Neon PostgreSQL connection string |
   | `SECRET_KEY` | any long random string (e.g. `abc123xyz789...`) |
   | `FRONTEND_URL` | leave blank for now, fill after first deploy |

5. Click **Deploy**

---

## Step 4 — After first deploy
1. Vercel gives you a URL like `https://medisync-abc123.vercel.app`
2. Go back to Vercel → your project → Settings → Environment Variables
3. Add/update `FRONTEND_URL` = `https://medisync-abc123.vercel.app`
4. Redeploy (Vercel dashboard → Deployments → Redeploy)

---

## Notes
- Unlike Netlify, Vercel runs Flask **directly** — no `dist/` folder needed
- The `dist/` folder is ignored on Vercel
- All pages (`/dashboard`, `/inventory` etc.) are served by Flask via `templates/`
- No build command needed — Vercel detects `vercel.json` automatically
