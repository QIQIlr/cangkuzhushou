@echo off
chcp 65001 >nul
title 设置消息格式
set PYTHONIOENCODING=utf-8
"%~dp0.venv\Scripts\python.exe" "%~dp0公共\设置消息格式.py"
echo.
pause
