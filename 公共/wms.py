# 职责：所有 WMS 模块共用的操作——打开专用 Chrome、检查登录、按左侧菜单进入页面。
# 输入：Playwright 对象、菜单路径（例如 ["仓库管理", "数据管理", "包裹管理"]）。
# 输出：浏览器（上下文）和页面；出错时抛出 自动化错误（带类型、原因、建议）。
# 说明：不保存、不输入密码。掉线时会请你在弹出的窗口里手动登录。
import os
import re

from 公共.错误 import 自动化错误, 需要登录, 页面改版, 网络超时, 环境问题

WMS首页 = "https://wms-admin.rakufun.jp/#/index"
专用配置目录 = r"C:\1LR\自动化工作流\浏览器配置"


def _启动(p, 可见):
    if 专用窗口开着():
        raise 自动化错误(环境问题, "“自动化专用 Chrome”窗口还开着，请先关掉它再运行。")
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
        raise 自动化错误(环境问题, "打不开 Chrome：" + 说明.splitlines()[0][:200])
    return 浏览器, (浏览器.pages[0] if 浏览器.pages else 浏览器.new_page())


def _命令行等待登录(次数):
    """命令行版：提示后等人按回车。返回 True=说登录好了，False=没法等（没有人在）。"""
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
        if _登录状态(页面) == "已登录":
            print("已登录，继续。", flush=True)
            if 记录:
                记录.写(f"    第{次数}次确认：已登录")
            return 浏览器, 页面
        if 次数 == 1:
            if 记录:
                记录.写("    第1次确认：还没登录")
    浏览器.close()
    raise 自动化错误(需要登录, "两次都没有检测到登录成功。")


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


def _登录状态(页面):
    """打开首页，返回 已登录 / 登录页 / 其他。打不开网页时抛出网络错误。"""
    try:
        页面.goto(WMS首页, timeout=30000)
    except Exception as e:
        raise 自动化错误(网络超时, "打不开 WMS 网站：" + str(e).splitlines()[0][:200])
    try:
        页面.locator(".el-menu").first.wait_for(timeout=15000)
    except Exception:
        pass
    if "/login" in 页面.url:
        return "登录页"
    if 页面.locator(".el-menu").count() > 0:
        return "已登录"
    return "其他"


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
        except Exception:
            raise 自动化错误(网络超时, f"“{最后一项}”页面 30 秒内没有加载完成。")
    else:
        项.click()
        页面.wait_for_timeout(2000)
