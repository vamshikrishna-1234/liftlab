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

# Don't auto-stop on stderr from native commands (gh writes status to stderr).
$ErrorActionPreference = "Continue"

function Fail($msg) {
    Write-Host ""
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

# ---------- 0. Sanity checks ----------
Write-Host "Checking prerequisites..." -ForegroundColor Cyan

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Fail "GitHub CLI ('gh') is not on PATH. Install with: winget install GitHub.cli"
}

gh auth status *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  You're not logged in to GitHub yet. Run this once:" -ForegroundColor Yellow
    Write-Host "      gh auth login" -ForegroundColor White
    Write-Host "  Pick:  GitHub.com  ->  HTTPS  ->  Login with a web browser" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path ".git")) {
    Fail "No git repo found in this folder. Run from the liftlab_demo/ root."
}

# ---------- 1. Create or update the GitHub repo ----------
$user = (gh api user -q .login 2>$null)
if (-not $user) { Fail "Could not read GitHub username from gh CLI." }
Write-Host "GitHub user: $user" -ForegroundColor Cyan

# Detect if a remote repo already exists.
gh repo view "$user/liftlab" *> $null
$repoExists = ($LASTEXITCODE -eq 0)

if ($repoExists) {
    Write-Host "Repo $user/liftlab already exists on GitHub." -ForegroundColor Cyan
    # Make sure 'origin' points at it.
    git remote remove origin 2>$null | Out-Null
    git remote add origin "https://github.com/$user/liftlab.git"
    Write-Host "Pushing latest commits..." -ForegroundColor Cyan
    git push -u origin main
    if ($LASTEXITCODE -ne 0) { Fail "git push failed." }
} else {
    Write-Host "Creating public GitHub repo '$user/liftlab' and pushing..." -ForegroundColor Cyan
    gh repo create liftlab `
        --public `
        --source=. `
        --remote=origin `
        --push `
        --description "AI marketing analyst for retail & CPG incrementality testing"
    if ($LASTEXITCODE -ne 0) { Fail "gh repo create failed." }
}

$repoSlug = "$user/liftlab"
$repoUrl  = "https://github.com/$repoSlug"

# ---------- 2. Publish the landing page via GitHub Pages (/docs on main) ----------
Write-Host "Publishing landing page to GitHub Pages..." -ForegroundColor Cyan

if (-not (Test-Path "docs")) { New-Item -ItemType Directory -Path docs | Out-Null }
Copy-Item -Path "landing\*" -Destination "docs\" -Recurse -Force

git add docs 2>$null | Out-Null
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git -c user.email="$user@users.noreply.github.com" -c user.name="$user" `
        commit -m "Publish landing page via GitHub Pages (/docs)" | Out-Null
    git push origin main | Out-Null
}

# Enable Pages (idempotent — ignore 'already enabled' errors).
gh api `
    --method POST `
    -H "Accept: application/vnd.github+json" `
    "/repos/$repoSlug/pages" `
    -f "source[branch]=main" `
    -f "source[path]=/docs" *> $null

$pagesUrl = "https://$user.github.io/liftlab/"

# ---------- 3. Open Streamlit Cloud deploy page + landing page + repo ----------
$streamlitDeploy = "https://share.streamlit.io/deploy?repository=$repoUrl&branch=main&mainModule=app.py"

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  GITHUB REPO:    $repoUrl" -ForegroundColor White
Write-Host "  LANDING PAGE:   $pagesUrl  (live in ~60 seconds)" -ForegroundColor White
Write-Host "  STREAMLIT APP:  click Deploy in the browser tab opening now" -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

Start-Process $streamlitDeploy
Start-Sleep -Seconds 1
Start-Process $pagesUrl
Start-Sleep -Seconds 1
Start-Process $repoUrl

Write-Host "Three browser tabs opened:" -ForegroundColor Green
Write-Host "    1. Streamlit Cloud deploy page  -> click 'Deploy' (one click)"
Write-Host "    2. Your live landing page       -> may take ~60s for first build"
Write-Host "    3. Your GitHub repo"
Write-Host ""
Write-Host "After Streamlit gives you a URL like https://<name>.streamlit.app:"
Write-Host "  paste it back to the assistant and it will wire it into the landing page."
