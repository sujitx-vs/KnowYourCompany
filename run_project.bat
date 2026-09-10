@echo off

cd /d "%~dp0"

echo Starting KnowYourCompany Backend...

start "KnowYourCompany Backend" cmd /k "%~dp0venv\Scripts\python.exe -m uvicorn backend.main:app --reload"

echo Starting KnowYourCompany Frontend...

start "KnowYourCompany Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 5 /nobreak >nul

start "" "http://localhost:3000"

exit