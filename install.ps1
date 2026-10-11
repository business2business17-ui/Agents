# Local install of the Amazon agents for terminal work (Windows PowerShell 5.1+ / PowerShell 7).
#   .\install.ps1              install Python packages + register the agents in Claude Code (if the `claude` CLI is present)
#   .\install.ps1 -Test        also run the self-tests
#   .\install.ps1 -NoClaude    Python packages only (other AIs: use dist\)
#   .\install.ps1 -Venv        use a virtual environment in .\.venv (run .\.venv\Scripts\Activate.ps1 before `claude`)
# If scripts are blocked:  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
param([switch]$Test, [switch]$NoClaude, [switch]$Venv)
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Here
$Py = $null
foreach ($c in @("py", "python3", "python")) { if (Get-Command $c -ErrorAction SilentlyContinue) { $Py = $c; break } }
if (-not $Py) { Write-Host "Python 3.9+ is required: https://www.python.org/downloads/"; exit 1 }
$PyArgs = @(); if ($Py -eq "py") { $PyArgs = @("-3") }
& $Py @PyArgs -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"
if ($LASTEXITCODE -ne 0) { Write-Host "Python 3.9 or newer is required"; exit 1 }
Write-Host ("Python: " + (& $Py @PyArgs --version))
$UserFlag = @("--user")
if ($Venv) {
  & $Py @PyArgs -m venv .venv
  $Py = Join-Path $Here ".venv\Scripts\python.exe"; $PyArgs = @(); $UserFlag = @()
  Write-Host "virtualenv created: run .\.venv\Scripts\Activate.ps1 before starting claude"
}
& $Py @PyArgs -m pip install --quiet --disable-pip-version-check -r requirements.txt @UserFlag
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed. Try again with -Venv"; exit 1 }
& $Py @PyArgs -c "import importlib.util as u,sys; m=[x for x in ('openpyxl','lxml','PIL') if u.find_spec(x) is None]; print('check imports:', 'OK' if not m else 'MISSING '+str(m)); sys.exit(1 if m else 0)"
if ($LASTEXITCODE -ne 0) { exit 1 }
if (Get-Command ffprobe -ErrorAction SilentlyContinue) { Write-Host "ffprobe: found (video checks enabled)" } else { Write-Host "ffprobe: not found (optional; install ffmpeg to validate video files)" }
if (-not $NoClaude) {
  if (Get-Command claude -ErrorAction SilentlyContinue) {
    $mp = (Get-Content .claude-plugin\marketplace.json -Raw | ConvertFrom-Json)
    claude plugin marketplace add "$Here"
    foreach ($p in $mp.plugins) {
      if (Test-Path $p.source) { claude plugin install ("{0}@{1}" -f $p.name, $mp.name); Write-Host ("installed: " + $p.name) }
    }
    Write-Host "Done. Start 'claude' in your project folder; list agents with /agents."
  } else { Write-Host "Claude Code CLI not found. For other AIs use the files in dist\ (see docs\LOCAL_INSTALL.md)." }
}
if ($Test) { & $Py @PyArgs -W ignore -m unittest discover -s tests; if ($LASTEXITCODE -eq 0) { Write-Host "self-tests: OK" } }
Write-Host "Create a working folder for a project:  $Py tools\init_project.py $HOME\amazon-projects\my-brand"
