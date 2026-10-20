@echo off
rem Installe l'agent : environnement Python, dependances, fichier de reglages.
cd /d "%~dp0"
where python >nul 2>nul || (echo Python est introuvable. Installez-le depuis python.org en cochant "Add Python to PATH". & pause & exit /b 1)
if not exist .venv python -m venv .venv
call .venv\Scripts\python -m pip install --upgrade pip
call .venv\Scripts\python -m pip install -r requirements.txt || (echo L'installation des dependances a echoue. & pause & exit /b 1)
if not exist .env (
  copy .env.example .env >nul
  echo Le fichier .env a ete cree : ouvrez-le avec le Bloc-notes et remplissez-le.
)
echo Installation terminee.
pause
