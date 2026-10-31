# 职责：所有 WMS 模块共用的操作——打开专用 Chrome、检查登录、按左侧菜单进入页面。
# 输入：Playwright 对象、菜单路径（例如 ["仓库管理", "数据管理", "包裹管理"]）。
# 输出：浏览器（上下文）和页面；出错时抛出 自动化错误（带类型、原因、建议）。
# 说明：不保存、不输入密码。掉线时会请你在弹出的窗口里手动登录。
import os
import re
import shutil
from pathlib import Path

from 公共.错误 import (自动化错误, 需要登录, 页面改版, 网络超时, 环境问题, 浏览器被关, 是浏览器被关, 归类,
                     网络断开, 等不到)

WMS首页 = "https://wms-admin.rakufun.jp/#/index"
# 浏览器配置（登录状态）在程序文件夹里，按这个文件的位置推算，换了文件夹也能找到（2026-10-29）
专用配置目录 = str(Path(__file__).resolve().parent.parent / "浏览器配置")
找不到Chrome说明 = ("这台电脑上找不到 Google Chrome（常见的几个安装位置都没有）。"
                "请先安装 Google Chrome（https://www.google.com/chrome/ ），或告诉 Claude 它装在哪里。")


# —— 浏览器配置里的纯缓存：Chrome 会自己重建，攒大了很占地方（2026-10-31 实测：整个配置 697MB，其中约 172MB 是这两块）——
# 只在启动前清一次，超过 150MB 才清。绝不碰 Cookies / Login Data / IndexedDB（登录状态和网页自己的数据）。
缓存目录们 = ("Cache", "Code Cache")
缓存上限 = 150 * 1024 * 1024
上次清缓存字节 = 0


def _目录大小(路径):
    总 = 0
    for 根, _, 文件们 in os.walk(路径):
        for 名 in 文件们:
            try:
                总 += os.path.getsize(os.path.join(根, 名))
            except OSError:
                pass
    return 总


def _清缓存():
    """Chrome 的 Cache / Code Cache 超过上限就删掉，返回清掉多少字节。删不掉也不挡运行。"""
    默认 = Path(专用配置目录) / "Default"
    大小 = sum(_目录大小(默认 / 名) for 名 in 缓存目录们)
    if 大小 <= 缓存上限:
        return 0
    for 名 in 缓存目录们:
        shutil.rmtree(默认 / 名, ignore_errors=True)
    return 大小


def 找Chrome():
    """Google Chrome 的位置：先看常见安装位置，再看 Windows 记录的安装位置（只读）。找不到返回 None。"""
    候选 = [os.path.join(os.environ.get(变量, ""), "Google", "Chrome", "Application", "chrome.exe")
          for 变量 in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA") if os.environ.get(变量)]
    候选.append(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    try:
        import winreg
        for 根 in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(根, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as 键:
                    候选.append(winreg.QueryValue(键, None))
            except OSError:
                pass
    except ImportError:
        pass
    return next((p for p in 候选 if p and os.path.isfile(p)), None)


def _启动(p, 可见):
    if 专用窗口开着():
        raise 自动化错误(环境问题, "“自动化专用 Chrome”窗口还开着，请先关掉它再运行。")
    global 上次清缓存字节
    上次清缓存字节 = _清缓存()
    try:
        if 可见:
            浏览器 = p.chromium.launch_persistent_context(
                专用配置目录, channel="chrome", headless=False, no_viewport=True)
        else:
            浏览器 = p.chromium.launch_persistent_context(
                专用配置目录, channel="chrome", headless=True, viewport={"width": 1600, "height": 900})
    except Exception as e:
        说明 = str(e)
        if "user data directory is already in use" in 说明 or "ProcessSingleton" in 说明:
            raise 自动化错误(环境问题, "“自动化专用 Chrome”窗口还开着，请先关掉它再运行。")
        if 找Chrome() is None:
            raise 自动化错误(环境问题, 找不到Chrome说明)
        raise 自动化错误(环境问题, "打不开 Chrome（英文技术原文写进了这次的日志）。")
    return 浏览器, (浏览器.pages[0] if 浏览器.pages else 浏览器.new_page())


启动浏览器 = _启动   # 只打开专用 Chrome、不进 WMS（飞书类模块用）


def _命令行等待登录(次数):
    """不是从窗口运行时（例如单独运行某个模块文件）：提示后等人按回车。返回 True=说登录好了，False=没法等（没有人在）。"""
    if 次数 == 2:
        print("还没有检测到登录成功，请再试一次。", flush=True)
    print("\n========================================", flush=True)
    print("WMS 需要登录：请在弹出的 Chrome 窗口里登录，", flush=True)
    print("登录完成后，回到这个窗口按回车键继续。", flush=True)
    print("========================================", flush=True)
    try:
        input()
        return True
    except (EOFError, RuntimeError):
        return False


def 打开WMS(p, 可见=False, 记录=None, 等待登录=None):
    """打开自动化专用 Chrome，进入 WMS 首页。返回 (浏览器, 页面)。
    可见=False：后台运行，屏幕上不出现窗口（默认）。
    掉线时会自动换成可见窗口，请人手动登录后继续。
    等待登录：掉线时怎么等人登录（窗口版传入弹窗；不传就用命令行按回车）。"""
    浏览器, 页面 = _启动(p, 可见)
    if 记录:
        记录.页面 = 页面
        if 上次清缓存字节:
            记录.写(f"    清掉了 Chrome 的旧缓存 {上次清缓存字节 / 1048576:.0f} MB（登录状态不受影响）")
    状态 = _登录状态(页面)
    if 状态 == "已登录":
        return 浏览器, 页面
    if 状态 == "其他":
        raise 自动化错误(页面改版, f"打开 WMS 首页后既不是登录页也找不到左侧菜单（网址 {页面.url}）。")

    # 掉线了：后台窗口没法登录，换成可见窗口
    if 记录:
        记录.写("    WMS 已掉线，打开可见窗口请人登录")
    if not 可见:
        浏览器.close()
        浏览器, 页面 = _启动(p, True)
        if 记录:
            记录.页面 = 页面
        _登录状态(页面)
    等待 = 等待登录 or _命令行等待登录
    for 次数 in (1, 2):
        if not 等待(次数):
            浏览器.close()
            raise 自动化错误(需要登录, "WMS 已掉线，没有完成登录。")
        if _登录状态(页面, 登录后=True) == "已登录":
            print("已登录，继续。", flush=True)
            if 记录:
                记录.写(f"    第{次数}次确认：已登录")
            return 浏览器, 页面
        if 次数 == 1:
            if 记录:
                记录.写("    第1次确认：还没登录")
    浏览器.close()
    raise 自动化错误(需要登录, "两次都没有检测到登录成功。")


def 关掉自动化Chrome(超时秒=4):
    """运行中关窗口时用：关掉用“浏览器配置”文件夹的 Chrome（就是程序运行时打开的那个）。
    只找命令行里带这个文件夹的 chrome.exe，别的 Chrome 不碰。超时就不等了，返回 False（照常退出）。"""
    import subprocess
    命令 = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
          "Where-Object { $_.CommandLine -and $_.CommandLine.Contains($env:CANGKU_PROFILE) } | "
          "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")
    try:
        结果 = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", 命令], timeout=超时秒,
                             env={**os.environ, "CANGKU_PROFILE": 专用配置目录}, capture_output=True,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return 结果.returncode == 0     # PowerShell 自己报错（返回码不是 0）也算没关掉，不能报成关掉了
    except Exception:
        return False


def 专用窗口开着():
    """专用 Chrome 开着时，它会锁住配置目录里的 lockfile 文件。"""
    锁 = os.path.join(专用配置目录, "lockfile")
    if not os.path.exists(锁):
        return False
    try:
        with open(锁, "a"):
            return False
    except OSError:
        return True


def _登录状态(页面, 登录后=False):
    """打开首页，返回 已登录 / 登录页 / 其他。打不开网页时抛出网络错误。
    登录后=True：是在等人登录之后检查的——这时浏览器没了，几乎都是登录用的 Chrome 窗口被关掉了（体检 2026-10-28）。"""
    try:
        页面.goto(WMS首页, timeout=30000)
    except Exception as e:
        if 是浏览器被关(e):
            raise 自动化错误(浏览器被关, "登录用的 Chrome 窗口被关闭了，程序没法继续检查登录。" if 登录后
                         else "运行用的 Chrome 窗口被关闭了（或浏览器意外退出），程序没法继续。")
        e2 = 归类(e)
        if e2.类型 == 网络断开:
            raise 自动化错误(网络断开, "打不开 WMS 网站：" + e2.原因)
        raise 自动化错误(网络超时, "30 秒内打不开 WMS 首页（网速慢、网络断了或电脑睡着了）。")
    try:
        页面.locator(".el-menu").first.wait_for(timeout=15000)
    except Exception:
        pass
    if "/login" in 页面.url:
        return "登录页"
    if 页面.locator(".el-menu").count() > 0:
        return "已登录"
    return "其他"


_读提示JS = """() => {
  const 看得见 = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  for (const 框 of document.querySelectorAll('.el-message-box, .el-message--error, .el-message--warning')) {
    if (!看得见(框)) continue;
    const 字 = (框.querySelector('.el-message-box__message, .el-message__content') || 框).innerText.trim();
    if (字) return 字;
  }
  return '';
}"""


def 读系统提示(页面):
    """WMS 自己弹出的提示框（“系统提示”对话框、顶部提示条）里的文字；没有或读不到返回 ""。只读，不点它。"""
    try:
        return 页面.evaluate(_读提示JS) or ""
    except Exception:
        return ""


def 进入页面(页面, 菜单路径, 等待接口=None):
    """按左侧菜单逐级点击，例如 ["仓库管理", "数据管理", "包裹管理"]。
    等待接口：页面打开时会自动发出的查询请求网址里的一段文字；给了就等它返回。"""
    菜单 = 页面.locator(".el-menu").first
    *上级, 最后一项 = 菜单路径
    for 名称 in 上级:
        标题 = 菜单.locator(".el-sub-menu__title").filter(has_text=re.compile("^" + 名称 + "$")).first
        if 标题.count() == 0:
            raise 自动化错误(页面改版, f"左侧菜单里找不到“{名称}”。")
        所在 = 标题.locator("xpath=..")
        if "is-opened" not in (所在.get_attribute("class") or ""):
            标题.click()
            页面.wait_for_timeout(500)
    项 = 菜单.locator("li.el-menu-item").filter(has_text=re.compile("^" + 最后一项 + "$")).first
    if 项.count() == 0:
        raise 自动化错误(页面改版, f"左侧菜单里找不到“{最后一项}”。")
    if 等待接口:
        try:
            with 页面.expect_response(lambda r: 等待接口 in r.url, timeout=30000):
                项.click()
        except Exception as e:
            e2 = 归类(e)
            if e2.类型 in (浏览器被关, 网络断开, 等不到):   # 点菜单本身就点不动 / 断网：如实报（体检 2026-10-28）
                raise e2
            raise 自动化错误(网络超时, f"“{最后一项}”页面 30 秒内没有加载完成。")
    else:
        项.click()
        页面.wait_for_timeout(2000)
