@echo off
chcp 65001 >nul
title 仓库助手
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
"%~dp0.venv\Scripts\python.exe" "%~dp0公共\仓库助手.py"
