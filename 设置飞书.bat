@echo off
chcp 65001 >nul
title 设置飞书
set PYTHONIOENCODING=utf-8
"%~dp0.venv\Scripts\python.exe" "%~dp0公共\设置飞书.py"
echo.
pause
