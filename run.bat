@echo off
cd /d D:\cc-chat
conda run -n translate-app python translate_app.py
if %errorlevel% neq 0 pause
