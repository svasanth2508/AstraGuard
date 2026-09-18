@echo off
setlocal
cd /d "%~dp0"
start "AstraGuard Backend" cmd /k "cd /d backend && if not exist .venv python -m venv .venv && call .venv\Scripts\activate.bat && pip install -r requirements.txt && uvicorn main:app --reload"
start "AstraGuard Frontend" cmd /k "cd /d frontend && if not exist node_modules npm install && npm run dev"
echo AstraGuard backend and frontend are starting in separate windows.
echo Open http://localhost:5173 after both windows report ready.
endlocal
