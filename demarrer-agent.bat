@echo off
rem Demarre l'agent. Le journal est ecrit dans state\agent.log.
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist state mkdir state
.venv\Scripts\python -m agent lancer >> state\agent.log 2>&1
