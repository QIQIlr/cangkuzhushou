# 职责：检查 Python + Playwright 能否调用电脑上已装的 Chrome。
# 输入：无。输出：屏幕打印“测试通过”或报错信息。
# 用法：C:\1LR\自动化工作流\.venv\Scripts\python.exe C:\1LR\自动化工作流\脚本\环境测试.py
# 说明：用临时空白配置打开 Chrome，访问 about:blank，然后关闭；不会登录任何网站。
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    浏览器 = p.chromium.launch(channel="chrome", headless=False)
    页面 = 浏览器.new_page()
    页面.goto("about:blank")
    print("Chrome 版本:", 浏览器.version)
    print("页面地址:", 页面.url)
    浏览器.close()
    print("测试通过")
