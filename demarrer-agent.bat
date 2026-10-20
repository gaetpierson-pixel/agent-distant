@echo off
rem Demarre l'agent et le relance tout seul s'il s'arrete (veille, coupure reseau...).
rem Le journal est ecrit dans state\agent.log.
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist state mkdir state
:boucle
.venv\Scripts\python -m agent lancer >> state\agent.log 2>&1
rem 3 = un autre agent tourne deja : on ne relance pas.
if %errorlevel%==3 exit /b 0
echo %date% %time% Agent arrete (code %errorlevel%), relance dans 30 s. >> state\agent.log
timeout /t 30 /nobreak >nul
goto boucle
