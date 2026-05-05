# Liftlab one-shot deploy script.
#
# Prerequisite (one time, ~30 seconds):
#   gh auth login            # pick GitHub.com / HTTPS / Login with web browser
#
# Then just run:
#   .\deploy.ps1
#
# This will:
#   1. Create a public GitHub repo at https://github.com/<you>/liftlab
#   2. Push the current code
#   3. Enable GitHub Pages for the landing page (free https://<you>.github.io/liftlab)
#   4. Open Streamlit Community Cloud's "deploy" page pre-filled so you can
#      click "Deploy" once for the live app at https://<name>.streamlit.app
#
# Total user-facing work after `gh auth login`: 1 click.

$ErrorActionPreference = "Stop"

# ---------- 0. Sanity checks ----------
Write-Host "Checking prerequisites..." -ForegroundColor Cyan

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI ('gh') is not on PATH. Install with: winget install GitHub.cli"
    exit 1
}

$auth = (gh auth status 2>&1 | Out-String)
if ($auth -match "not logged" -or $LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  You're not logged in to GitHub yet. Run this once:" -ForegroundColor Yellow
    Write-Host "      gh auth login" -ForegroundColor White
    Write-Host "  Pick:  GitHub.com  ->  HTTPS  ->  Yes (auth git with creds)  ->  Login with a web browser"
    Write-Host "  Then re-run this script." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path ".git")) {
    Write-Error "No git repo found in this folder. Run from the liftlab_demo/ root."
    exit 1
}

# ---------- 1. Create + push the GitHub repo ----------
$existing = (gh repo view --json url 2>$null) | Out-String
if ($existing -match "url") {
    Write-Host "Repo already exists on GitHub, pushing latest commits..." -ForegroundColor Cyan
    git push origin main
} else {
    Write-Host "Creating public GitHub repo 'liftlab' and pushing..." -ForegroundColor Cyan
    gh repo create liftlab `
        --public `
        --source=. `
        --remote=origin `
        --push `
        --description "AI marketing analyst for retail & CPG incrementality testing"
}

# ---------- 2. Enable GitHub Pages on /landing ----------
Write-Host "Enabling GitHub Pages for the landing page..." -ForegroundColor Cyan

$repoSlug = (gh repo view --json nameWithOwner -q .nameWithOwner)
$user = $repoSlug.Split("/")[0]
$repo = $repoSlug.Split("/")[1]

# Pages can serve from / or /docs on a branch. We'll publish from /landing
# by copying it to /docs. Cleanest cross-platform approach.
if (-not (Test-Path "docs")) { New-Item -ItemType Directory -Path docs | Out-Null }
Copy-Item -Path "landing\*" -Destination "docs\" -Recurse -Force
git add docs
git diff --cached --quiet; if ($LASTEXITCODE -ne 0) {
    git -c user.email="$user@users.noreply.github.com" -c user.name="$user" `
        commit -m "Publish landing page via GitHub Pages (/docs)"
    git push origin main
}

try {
    gh api `
        --method POST `
        -H "Accept: application/vnd.github+json" `
        "/repos/$repoSlug/pages" `
        -f source[branch]=main `
        -f source[path]=/docs 2>&1 | Out-Null
} catch {
    # Already enabled — fine.
}

$pagesUrl = "https://$user.github.io/$repo/"
Write-Host ""
Write-Host "Landing page URL (live in ~60s):" -ForegroundColor Green
Write-Host "    $pagesUrl" -ForegroundColor White

# ---------- 3. Open Streamlit Cloud deploy page pre-filled ----------
$repoUrl = "https://github.com/$repoSlug"
$streamlitDeploy = "https://share.streamlit.io/deploy?repository=$repoUrl&branch=main&mainModule=app.py"

Write-Host ""
Write-Host "Opening Streamlit Community Cloud deploy page..." -ForegroundColor Cyan
Write-Host "  Just click the 'Deploy' button. First boot takes ~3 minutes."
Write-Host "  You'll get a URL like https://<your-app>.streamlit.app"

Start-Process $streamlitDeploy
Start-Process $pagesUrl
Start-Process $repoUrl

Write-Host ""
Write-Host "Done. Three browser tabs opened:" -ForegroundColor Green
Write-Host "    1. Streamlit Cloud deploy page  (click 'Deploy')"
Write-Host "    2. Your live landing page (may take 60s for first build)"
Write-Host "    3. Your GitHub repo"
Write-Host ""
Write-Host "After Streamlit deploys, edit landing/index.html and replace LIFTLAB_DEMO_URL"
Write-Host "with your live https://<app>.streamlit.app URL, then commit and push."
