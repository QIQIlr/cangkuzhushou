# 职责：查询 D区、E区“已挂起 + 任务小类=无任务”的包裹，列出转运单号。只读，不改任何 WMS 数据。
# 输入：已登录的 WMS 页面 + 运行记录（单独运行时自己打开）。
# 输出：结果字典 {状态, 结果文字, 数量, 错误信息}
#   状态：成功 / 无数据 / 不完整 / 失败
#   - 无数据：页面明确显示“共 0 条记录”
#   - 不完整：读到的单号个数和“共 N 条”对不上
#   - 失败：读不到总数或页面出错——这时绝不报 0
# 步骤（小柒 2026-10-22 确认）：首页 → 仓库管理 → 数据管理 → 包裹管理 → 已挂起 → 展开
#   → 任务小类选“无任务” → 清空“签收时间” → 区域选 D区 → 查询 → 读全部页；再对 E区 查一次。
# 一个区域失败不影响另一个区域。
# 排错：每次运行的详细记录在 日志\日期_时间_无任务包裹\ 文件夹里。
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

根目录 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(根目录))
from 公共.wms import 进入页面  # noqa: E402
from 公共.消息格式 import 套用 as 套用格式  # noqa: E402
from 公共.错误 import 自动化错误, 归类, 页面改版, 网络超时, 数据不完整  # noqa: E402

模块名 = "无任务包裹"
查询接口 = "selectAllPage"   # 包裹管理页面查询时，网址里带的这段文字
要查的区域 = ["D区", "E区"]
每页条数 = 30

# 格式文件（格式\无任务包裹.txt）坏了、又没有上次可用的备份时，用这个
默认格式 = """[开头]
【无任务包裹】{日期} {时间}
[每个区域]
{区域}：{数量}个无任务包裹
{单号列表}
[查询失败时]
{区域}：查询失败
"""


def _表单项(页面, 名称):
    return 页面.locator(".vxe-form--item-inner").filter(
        has=页面.locator(".vxe-form--item-title-label").filter(has_text=re.compile("^" + 名称 + "$"))).first


def _下拉选择(页面, 名称, 选项):
    框 = _表单项(页面, 名称)
    if 框.count() == 0:
        raise 自动化错误(页面改版, f"查询条件里找不到“{名称}”。")
    框.locator(".el-select").click()
    页面.wait_for_timeout(500)
    项 = 页面.locator(".el-select-dropdown__item:visible").filter(has_text=re.compile("^" + 选项 + "$")).first
    if 项.count() == 0:
        页面.keyboard.press("Escape")
        raise 自动化错误(页面改版, f"“{名称}”下拉里找不到“{选项}”。")
    项.click()
    页面.wait_for_timeout(300)


def _清空签收时间(页面):
    日期 = _表单项(页面, "签收时间")
    if 日期.count() == 0:
        raise 自动化错误(页面改版, "查询条件里找不到“签收时间”。")
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
        raise 自动化错误(页面改版, "“签收时间”没有清空。")


def _等查询结果(页面, 动作, 页码=1):
    """做一个动作（点查询/翻页），等页面自己的查询请求返回，返回 (参数, 数据)。"""
    try:
        with 页面.expect_response(
                lambda r: 查询接口 in r.url and f"pageNo={页码}" in r.url, timeout=30000) as 等待:
            动作()
        回应 = 等待.value
        数据 = 回应.json()
    except 自动化错误:
        raise
    except Exception as e:
        错误 = 归类(e)
        if 错误.类型 == 页面改版:
            raise 错误
        raise 自动化错误(网络超时, "点击后 30 秒内没有拿到查询结果。")
    if not isinstance(数据, dict) or 数据.get("code") != 0 or "data" not in 数据:
        raise 自动化错误(网络超时, "WMS 返回了错误：" + str(数据)[:200])
    return parse_qs(urlparse(回应.url).query), 数据["data"]


def 查询一个区域(页面, 区域, 记录=None):
    """在已设好“已挂起 / 无任务 / 无签收时间”的页面上，查一个区域，返回 (状态, 总数, 单号列表, 说明)。"""
    _下拉选择(页面, "区域", 区域)
    参数, 数据 = _等查询结果(页面, lambda: 页面.get_by_role("button", name="查询").first.click())

    # 核对：查询条件确实是我们要的
    区域字母 = None if 区域 == "全部" else 区域.replace("区", "")   # “全部”只在测试翻页时用
    应有 = {"packagesStatus": "11", "taskType": "-1", "shelvesRegionNum": 区域字母}
    for 键, 值 in 应有.items():
        if 参数.get(键, [None])[0] != 值:
            raise 自动化错误(页面改版, f"查询条件没有生效（{键}={参数.get(键)}），本次结果不可信。")
    if any("time" in 键.lower() for 键 in 参数):
        raise 自动化错误(页面改版, "签收时间条件没有清空，本次结果不可信。")

    总数 = 数据.get("total")
    if not isinstance(总数, int):
        raise 自动化错误(数据不完整, "读不到总条数。")
    try:   # 核对：页面上显示的“共 N 条记录”和读到的一致
        页面.locator("span").filter(has_text=re.compile(f"^共 {总数} 条记录$")).first.wait_for(timeout=10000)
    except Exception:
        raise 自动化错误(数据不完整, f"页面显示的条数和读到的 {总数} 不一致。")

    单号 = [项.get("transportNum") for 项 in 数据.get("list", [])]
    总页数 = math.ceil(总数 / 每页条数)
    if 记录:
        记录.写(f"    共 {总数} 条，{总页数} 页")
    for 页码 in range(2, 总页数 + 1):
        下一页 = 页面.locator(".vxe-pager--next-btn:visible").first
        _, 数据 = _等查询结果(页面, 下一页.click, 页码)
        单号 += [项.get("transportNum") for 项 in 数据.get("list", [])]
        if 记录:
            记录.写(f"    已读第 {页码} 页")

    单号 = [号 for 号 in 单号 if 号]
    if 总数 == 0:
        return "无数据", 0, [], ""
    if len(单号) != 总数 or len(set(单号)) != len(单号):
        return "不完整", 总数, 单号, f"应有 {总数} 条，实际读到 {len(单号)} 条（去重后 {len(set(单号))}）"
    return "成功", 总数, 单号, ""


def 失败结果(e, 开始时间):
    return {"状态": "失败", "数量": None, "开始时间": 开始时间,
            "区域列表": [{"区域": 区, "状态": "失败", "数量": "", "单号": []} for 区 in 要查的区域],
            "错误信息": e.一句话(模块名), "错误列表": [e]}


def 运行(页面, 记录):
    """主控以后也调用这个函数。页面需已登录。
    返回 {状态, 数量, 开始时间, 区域列表[{区域, 状态, 数量, 单号}], 错误信息, 错误列表}"""
    开始时间 = datetime.now()
    区域列表, 错误, 合计 = [], [], 0
    try:
        with 记录.步骤("进入 仓库管理 → 数据管理 → 包裹管理"):
            进入页面(页面, ["仓库管理", "数据管理", "包裹管理"], 等待接口=查询接口)
        with 记录.步骤("点击“已挂起”"):
            _等查询结果(页面, lambda: 页面.locator(".el-tabs__item").filter(
                has_text=re.compile("^已挂起")).first.click())
        with 记录.步骤("展开更多条件"):
            页面.get_by_text("展开").first.click()
            页面.wait_for_timeout(800)
        with 记录.步骤("任务小类选“无任务”"):
            _下拉选择(页面, "任务小类", "无任务")
        with 记录.步骤("清空“签收时间”"):
            _清空签收时间(页面)
    except 自动化错误 as e:
        return 失败结果(e, 开始时间)

    for 区域 in 要查的区域:
        try:
            with 记录.步骤(f"查询 {区域}"):
                状态, 总数, 单号, 说明 = 查询一个区域(页面, 区域, 记录)
                记录.写(f"    结果：{状态}，{总数} 个" + (f"（{说明}）" if 说明 else ""))
        except 自动化错误 as e:
            区域列表.append({"区域": 区域, "状态": "失败", "数量": "", "单号": []})
            错误.append(e)
            continue
        区域列表.append({"区域": 区域, "状态": 状态, "数量": 总数, "单号": 单号})
        合计 += 总数
        if 状态 == "不完整":
            e = 自动化错误(数据不完整, 说明)
            e.步骤 = f"查询 {区域}"
            错误.append(e)

    状态表 = [区["状态"] for 区 in 区域列表]
    if "失败" in 状态表:
        总状态 = "失败"
    elif "不完整" in 状态表:
        总状态 = "不完整"
    elif all(s == "无数据" for s in 状态表):
        总状态 = "无数据"
    else:
        总状态 = "成功"
    return {"状态": 总状态, "数量": None if 总状态 == "失败" else 合计, "开始时间": 开始时间,
            "区域列表": 区域列表,
            "错误信息": "；".join(e.一句话(模块名) for e in 错误), "错误列表": 错误}


def 排版内容(结果, 用时=None):
    """把结果整理成格式文件里能用的内容。"""
    开始 = 结果.get("开始时间") or datetime.now()
    if isinstance(开始, str):
        开始 = datetime.fromisoformat(开始)
    公共 = {"日期": f"{开始:%Y-%m-%d}", "时间": f"{开始:%H:%M}",
            "合计": "" if 结果["数量"] is None else 结果["数量"], "状态": 结果["状态"],
            "用时": f"{用时:.0f}秒" if 用时 is not None else ""}
    return 公共, 结果["区域列表"]


def 组成消息(结果, 文件夹名, 用时=None):
    """按 格式\\无任务包裹.txt 排版；不是成功/无数据时，在最后自动加上 状态、原因、建议和日志文件夹名（格式文件删不掉这段）。
    返回 (消息, 格式问题说明)。"""
    公共, 区域列表 = 排版内容(结果, 用时)
    消息, 格式问题 = 套用格式(模块名, 公共, 区域列表, 默认格式)
    if 结果["状态"] not in ("成功", "无数据"):
        消息 += f"\n\n⚠ 状态：{结果['状态']}"
        for e in 结果.get("错误列表", []):
            消息 += f"\n{e.一句话(模块名)}"
        消息 += f"\n日志：{文件夹名}"
    if 格式问题:
        消息 += f"\n\n（提醒：{格式问题}。双击 设置消息格式.bat 修改。）"
    return 消息, 格式问题


def 保存最近结果(结果):
    """给“设置消息格式”预览用。"""
    数据 = {k: 结果[k] for k in ("状态", "数量", "区域列表")}
    数据["开始时间"] = 结果["开始时间"].isoformat() if 结果.get("开始时间") else None
    try:
        (根目录 / "日志" / f"最近结果_{模块名}.json").write_text(
            json.dumps(数据, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    # 单独运行这个模块。参数：--可见 显示浏览器窗口（排查用）；--不发送 不发飞书
    from 公共.运行 import 运行模块们
    结果 = 运行模块们([模块名], 可见="--可见" in sys.argv, 发送="--不发送" not in sys.argv)
    sys.exit(0 if 结果["结果们"][0]["状态"] in ("成功", "无数据") else 1)