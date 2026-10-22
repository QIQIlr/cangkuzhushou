@echo off
chcp 65001 >nul
title 查询无任务包裹
set PYTHONIOENCODING=utf-8
"%~dp0.venv\Scripts\python.exe" "%~dp0模块\无任务包裹.py"
echo.
pause
