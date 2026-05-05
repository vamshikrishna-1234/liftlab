# Deploying Liftlab as your YC "product link"

You need a public URL for the **"Please provide a link to the product"** field. Streamlit Community Cloud is free, takes ~10 minutes, and gives you `https://liftlab.streamlit.app` (or similar). This is the recommended path.

---

## Option A (recommended): Streamlit Community Cloud — free, ~10 minutes

### 1. Create a GitHub repo

```powershell
cd c:\Users\System162L\Documents\vamshi_psnl\YC_application\liftlab_demo

# Initialize git, ignore the venv and any local artifacts
@"
.venv/
__pycache__/
*.pyc
.DS_Store
smoke_test_report.xlsx
*.xlsx
"@ | Out-File -FilePath .gitignore -Encoding utf8

git init
git add .
git commit -m "Initial Liftlab demo"

# Create a new repo on github.com (e.g. github.com/<you>/liftlab) — public.
# Then:
git remote add origin https://github.com/<your-username>/liftlab.git
git branch -M main
git push -u origin main
```

### 2. Deploy

1. Go to [share.streamlit.io](https://share.streamlit.io).
2. Sign in with GitHub.
3. Click **"New app"** → pick the `liftlab` repo, branch `main`, main file `app.py`.
4. (Optional) under **Advanced settings → Secrets**, add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   # or
   OPENAI_API_KEY = "sk-..."
   ```
   This enables the LLM-narrated summary. The app works without these keys (uses the template narrator).
5. Click **Deploy**. First boot takes ~3–5 minutes (it builds the conda env).
6. You'll get a public URL like `https://liftlab.streamlit.app`. **Use this in the YC form's "Please provide a link to the product" field.**

### 3. (Optional) Custom subdomain

Streamlit lets you rename to `https://<anything>.streamlit.app` from the app's settings page. Pick something memorable (e.g. `liftlab`, `incrementa`).

---

## Option B: Render.com (free tier, slightly more polished)

If you want a custom domain on a free tier, Render is a good alternative.

1. Push the repo to GitHub (as above).
2. At [render.com](https://render.com), click **New → Web Service** → connect the repo.
3. Settings:
   - **Environment:** Python 3.11
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
   - **Plan:** Free
4. Set environment variables (`ANTHROPIC_API_KEY` etc.) under **Environment** if you want LLM mode.
5. You get `https://liftlab.onrender.com`.

Note: Render's free tier sleeps after 15 minutes of inactivity. The first hit after a sleep takes ~30 seconds to wake up — fine for a demo link, awkward for a live customer demo.

---

## Option C: Local-only + screen recording (fastest, weakest)

If you can't get a deploy working in time:

1. Just record the Loom against `localhost:8501`.
2. Leave the **product link** field on the YC form blank, or put your GitHub repo URL.
3. YC won't reject for this — but a live link is a real positive signal that you ship.

---

## Pre-deploy checklist

- [ ] `.gitignore` excludes `.venv/`, `__pycache__/`, `*.xlsx`, any local secrets.
- [ ] No API keys checked into the repo.
- [ ] `requirements.txt` reflects exactly what's needed.
- [ ] README's Quickstart actually works on a fresh clone.
- [ ] Deployed URL loads in incognito mode (no auth required).
- [ ] Footer caption "All numbers shown are from a synthetic data generator" is visible.

---

## After deploy: things to do

1. Buy a domain (`liftlab.ai`, `liftlab.app`, `getliftlab.com`, ~$15) and point it to the Streamlit/Render URL using their custom-domain feature.
2. Add a tiny landing page above the Streamlit app (one paragraph + a "Launch demo" button) using Carrd or Framer (~30 minutes). Use this `https://liftlab.ai` URL in the YC form's **"Company URL, if any"** field, and the raw Streamlit URL in **"Please provide a link to the product"**.
3. Set up Plausible / Fathom analytics (~5 min) so you can tell YC "X people used the demo this week" if they ask.
