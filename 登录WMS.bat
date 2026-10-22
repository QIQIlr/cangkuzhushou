@echo off
chcp 65001 >nul
title 登录WMS
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%~dp0浏览器配置" --no-first-run --new-window https://wms-admin.rakufun.jp/#/index
echo 已打开自动化专用 Chrome。
echo 请在那个窗口里登录 WMS（已登录就不用管），然后关掉那个 Chrome 窗口。
echo.
pause
