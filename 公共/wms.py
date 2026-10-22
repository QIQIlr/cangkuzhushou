# 职责：所有 WMS 模块共用的操作——打开专用 Chrome、检查登录、按左侧菜单进入页面。
# 输入：Playwright 对象、菜单路径（例如 ["仓库管理", "数据管理", "包裹管理"]）。
# 输出：浏览器（上下文）和页面；出错时抛出“WMS错误”，里面是给人看的中文说明。
# 说明：不保存、不输入密码。掉线时会请你在弹出的窗口里手动登录。
import os
import re

WMS首页 = "https://wms-admin.rakufun.jp/#/index"
专用配置目录 = r"C:\1LR\自动化工作流\浏览器配置"


class WMS错误(Exception):
    """给人看的错误说明。"""


def 打开WMS(p):
    """打开自动化专用 Chrome，进入 WMS 首页；未登录时请人手动登录。返回 (浏览器, 页面)。"""
    if 专用窗口开着():
        raise WMS错误("请先关闭“自动化专用 Chrome”窗口（登录 WMS 时打开的那个），然后重新运行。")
    try:
        浏览器 = p.chromium.launch_persistent_context(
            专用配置目录, channel="chrome", headless=False, no_viewport=True)
    except Exception as e:
        说明 = str(e)
        if "user data directory is already in use" in 说明 or "ProcessSingleton" in 说明 or "exitCode=21" in 说明:
            raise WMS错误("请先关闭“自动化专用 Chrome”窗口（登录 WMS 时打开的那个），然后重新运行。")
        raise WMS错误("打不开 Chrome：" + 说明.splitlines()[0])

    页面 = 浏览器.pages[0] if 浏览器.pages else 浏览器.new_page()
    if not _已登录(页面):
        for 次数 in (1, 2):
            print("\n========================================", flush=True)
            print("WMS 需要登录：请在弹出的 Chrome 窗口里登录，", flush=True)
            print("登录完成后，回到这个窗口按回车键继续。", flush=True)
            print("========================================", flush=True)
            try:
                input()
            except EOFError:
                浏览器.close()
                raise WMS错误("需要人工登录：WMS 已掉线，请双击 C:\\1LR\\自动化工作流\\登录WMS.bat 登录一次后再运行。")
            if _已登录(页面):
                print("已登录，继续查询。", flush=True)
                break
            if 次数 == 1:
                print("还没有检测到登录成功，请再试一次。", flush=True)
        else:
            浏览器.close()
            raise WMS错误("需要人工登录：两次都没有检测到登录成功。")
    return 浏览器, 页面


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


def _已登录(页面):
    """打开首页，看是否被跳到登录页。"""
    页面.goto(WMS首页)
    try:
        页面.locator(".el-menu").first.wait_for(timeout=15000)
    except Exception:
        pass
    return "/login" not in 页面.url and 页面.locator(".el-menu").count() > 0


def 进入页面(页面, 菜单路径, 等待接口=None):
    """按左侧菜单逐级点击，例如 ["仓库管理", "数据管理", "包裹管理"]。
    等待接口：页面打开时会自动发出的查询请求网址里的一段文字；给了就等它返回。"""
    菜单 = 页面.locator(".el-menu").first
    *上级, 最后一项 = 菜单路径
    for 名称 in 上级:
        标题 = 菜单.locator(".el-sub-menu__title").filter(has_text=re.compile("^" + 名称 + "$")).first
        if 标题.count() == 0:
            raise WMS错误(f"左侧菜单里找不到“{名称}”。")
        所在 = 标题.locator("xpath=..")
        if "is-opened" not in (所在.get_attribute("class") or ""):
            标题.click()
            页面.wait_for_timeout(500)
    项 = 菜单.locator("li.el-menu-item").filter(has_text=re.compile("^" + 最后一项 + "$")).first
    if 项.count() == 0:
        raise WMS错误(f"左侧菜单里找不到“{最后一项}”。")
    if 等待接口:
        try:
            with 页面.expect_response(lambda r: 等待接口 in r.url, timeout=30000):
                项.click()
        except Exception:
            raise WMS错误(f"“{最后一项}”页面 30 秒内没有加载完成。")
    else:
        项.click()
        页面.wait_for_timeout(2000)
