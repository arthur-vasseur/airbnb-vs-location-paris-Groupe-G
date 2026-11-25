@echo off
rem Lanceur Windows : double-cliquer sur ce fichier.
rem Au premier lancement, installe les bibliotheques (1 a 2 minutes), puis ouvre l'application.

cd /d "%~dp0"

py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
if errorlevel 1 (
    echo Python 3.11 ou plus recent est necessaire.
    echo Installez-le depuis https://www.python.org/downloads/ puis relancez ce fichier.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\streamlit.exe" (
    echo Premier lancement : installation des bibliotheques...
    py -3 -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
    if errorlevel 1 (
        echo L'installation a echoue.
        pause
        exit /b 1
    )
)

echo L'application s'ouvre dans le navigateur. Fermez cette fenetre pour l'arreter.
start "" cmd /c "timeout /t 4 >nul & start http://localhost:8501"
".venv\Scripts\streamlit.exe" run app.py --server.headless true --server.port 8501
pause
