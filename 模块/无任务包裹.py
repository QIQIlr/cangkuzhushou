# 职责：查询 D区、E区“已挂起 + 任务小类=无任务”的包裹，列出转运单号。只读，不改任何 WMS 数据。
# 输入：已登录的 WMS 页面（单独运行时自己打开）。
# 输出：结果字典 {状态, 结果文字, 数量, 错误信息}
#   状态：成功 / 无数据 / 不完整 / 失败
#   - 无数据：页面明确显示“共 0 条记录”
#   - 不完整：读到的单号个数和“共 N 条”对不上
#   - 失败：读不到总数或页面出错——这时绝不报 0
# 步骤（小柒 2026-10-22 确认）：首页 → 仓库管理 → 数据管理 → 包裹管理 → 已挂起 → 展开
#   → 任务小类选“无任务” → 清空“签收时间” → 区域选 D区 → 查询 → 读全部页；再对 E区 查一次。
# 排错：失败时截图保存在 日志 文件夹，文件名带时间。
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

根目录 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(根目录))
from 公共.wms import WMS错误, 打开WMS, 进入页面  # noqa: E402

查询接口 = "selectAllPage"   # 包裹管理页面查询时，网址里带的这段文字
要查的区域 = ["D区", "E区"]
每页条数 = 30


def _表单项(页面, 名称):
    return 页面.locator(".vxe-form--item-inner").filter(
        has=页面.locator(".vxe-form--item-title-label").filter(has_text=re.compile("^" + 名称 + "$"))).first


def _下拉选择(页面, 名称, 选项):
    _表单项(页面, 名称).locator(".el-select").click()
    页面.wait_for_timeout(500)
    项 = 页面.locator(".el-select-dropdown__item:visible").filter(has_text=re.compile("^" + 选项 + "$")).first
    if 项.count() == 0:
        页面.keyboard.press("Escape")
        raise WMS错误(f"“{名称}”下拉里找不到“{选项}”。")
    项.click()
    页面.wait_for_timeout(300)


def _清空签收时间(页面):
    日期 = _表单项(页面, "签收时间")
    叉 = 日期.locator(".el-range__close-icon")
    for _ in range(5):   # 小叉只在鼠标停在上面时出现，所以多试几次
        页面.mouse.move(0, 0)
        日期.locator(".el-date-editor").hover()
        页面.wait_for_timeout(400)
        if "hidden" not in (叉.get_attribute("class") or ""):
            break
    叉.click(timeout=5000)
    页面.wait_for_timeout(300)
    if any(框.input_value() for 框 in 日期.locator("input").all()):
        raise WMS错误("“签收时间”没有清空。")


def _等查询结果(页面, 动作, 页码=1):
    """做一个动作（点查询/翻页），等页面自己的查询请求返回，返回 (参数, 数据)。"""
    try:
        with 页面.expect_response(
                lambda r: 查询接口 in r.url and f"pageNo={页码}" in r.url, timeout=30000) as 等待:
            动作()
        回应 = 等待.value
        数据 = 回应.json()
    except Exception:
        raise WMS错误("点击后 30 秒内没有拿到查询结果。")
    if not isinstance(数据, dict) or 数据.get("code") != 0 or "data" not in 数据:
        raise WMS错误("WMS 返回了错误：" + str(数据)[:200])
    return parse_qs(urlparse(回应.url).query), 数据["data"]


def 查询一个区域(页面, 区域):
    """在已设好“已挂起 / 无任务 / 无签收时间”的页面上，查一个区域，返回 (状态, 总数, 单号列表, 说明)。"""
    _下拉选择(页面, "区域", 区域)
    参数, 数据 = _等查询结果(页面, lambda: 页面.get_by_role("button", name="查询").first.click())

    # 核对：查询条件确实是我们要的
    区域字母 = None if 区域 == "全部" else 区域.replace("区", "")   # “全部”只在测试翻页时用
    应有 = {"packagesStatus": "11", "taskType": "-1", "shelvesRegionNum": 区域字母}
    for 键, 值 in 应有.items():
        if 参数.get(键, [None])[0] != 值:
            raise WMS错误(f"查询条件不对（{键}={参数.get(键)}），本次结果不可信。")
    if any("time" in 键.lower() for 键 in 参数):
        raise WMS错误("签收时间条件没有清空，本次结果不可信。")

    总数 = 数据.get("total")
    if not isinstance(总数, int):
        raise WMS错误("读不到总条数。")
    try:   # 核对：页面上显示的“共 N 条记录”和读到的一致
        页面.locator("span").filter(has_text=re.compile(f"^共 {总数} 条记录$")).first.wait_for(timeout=10000)
    except Exception:
        raise WMS错误(f"页面显示的条数和读到的 {总数} 不一致。")

    单号 = [项.get("transportNum") for 项 in 数据.get("list", [])]
    总页数 = math.ceil(总数 / 每页条数)
    for 页码 in range(2, 总页数 + 1):
        下一页 = 页面.locator(".vxe-pager--next-btn:visible").first
        _, 数据 = _等查询结果(页面, 下一页.click, 页码)
        单号 += [项.get("transportNum") for 项 in 数据.get("list", [])]

    单号 = [号 for 号 in 单号 if 号]
    if 总数 == 0:
        return "无数据", 0, [], ""
    if len(单号) != 总数 or len(set(单号)) != len(单号):
        return "不完整", 总数, 单号, f"应有 {总数} 条，实际读到 {len(单号)} 条（去重后 {len(set(单号))}）"
    return "成功", 总数, 单号, ""


def 运行(页面):
    """主控以后也调用这个函数。页面需已登录。"""
    时间 = datetime.now().strftime("%Y-%m-%d %H:%M")
    行 = [f"【无任务包裹】{时间}"]
    状态表, 错误, 合计 = [], [], 0
    try:
        进入页面(页面, ["仓库管理", "数据管理", "包裹管理"], 等待接口=查询接口)
        _等查询结果(页面, lambda: 页面.locator(".el-tabs__item").filter(
            has_text=re.compile("^已挂起")).first.click())
        页面.get_by_text("展开").first.click()
        页面.wait_for_timeout(800)
        _下拉选择(页面, "任务小类", "无任务")
        _清空签收时间(页面)
    except WMS错误 as e:
        _截图(页面, "准备")
        return {"状态": "失败", "结果文字": "\n".join(行 + [f"失败：{e}"]), "数量": None, "错误信息": str(e)}

    for 区域 in 要查的区域:
        try:
            状态, 总数, 单号, 说明 = 查询一个区域(页面, 区域)
        except WMS错误 as e:
            状态, 总数, 单号, 说明 = "失败", None, [], str(e)
            _截图(页面, 区域)
        状态表.append(状态)
        if 状态 == "失败":
            行.append(f"{区域}：查询失败（{说明}）")
            错误.append(f"{区域}：{说明}")
            continue
        合计 += 总数
        标记 = "（不完整！" + 说明 + "）" if 状态 == "不完整" else ""
        行.append(f"{区域}：{总数}个无任务包裹{标记}")
        行 += 单号
        if 状态 == "不完整":
            错误.append(f"{区域}：{说明}")

    if "失败" in 状态表:
        总状态 = "失败"
    elif "不完整" in 状态表:
        总状态 = "不完整"
    elif all(s == "无数据" for s in 状态表):
        总状态 = "无数据"
    else:
        总状态 = "成功"
    return {"状态": 总状态, "结果文字": "\n".join(行),
            "数量": None if 总状态 == "失败" else 合计, "错误信息": "；".join(错误)}


def _截图(页面, 名称):
    try:
        目录 = 根目录 / "日志"
        目录.mkdir(exist_ok=True)
        页面.screenshot(path=str(目录 / f"无任务包裹_{名称}_{datetime.now():%Y%m%d_%H%M%S}.png"))
    except Exception:
        pass


def _保存结果(结果):
    目录 = 根目录 / "日志"
    目录.mkdir(exist_ok=True)
    文件 = 目录 / f"无任务包裹_{datetime.now():%Y%m%d_%H%M%S}.txt"
    文件.write_text(f"状态：{结果['状态']}\n错误信息：{结果['错误信息'] or '无'}\n\n{结果['结果文字']}\n", encoding="utf-8")
    return 文件


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            浏览器, 页面 = 打开WMS(p)
        except WMS错误 as e:
            结果 = {"状态": "失败", "结果文字": f"【无任务包裹】失败：{e}", "数量": None, "错误信息": str(e)}
        else:
            结果 = 运行(页面)
            浏览器.close()
    文件 = _保存结果(结果)
    print("\n" + 结果["结果文字"])
    print(f"\n状态：{结果['状态']}" + (f"   错误：{结果['错误信息']}" if 结果["错误信息"] else ""))
    print(f"结果已保存：{文件}")
    sys.exit(0 if 结果["状态"] in ("成功", "无数据") else 1)
