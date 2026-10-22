# 职责：统计“增值服务 + 待处理”的任务还剩多少单，按日期和区域列成表格，反映当前货量压力。只读，不改任何 WMS 数据。
# 输入：已登录的 WMS 页面、运行记录、参数（查询区域，默认 D区、E区，在窗口的模块“设置”里改）。
# 输出：结果字典 {状态, 数量, 开始时间, 区域们, 日期们, 表[区域][日期], 全部[区域], 错误信息, 错误列表}
#   飞书发一张带表格的卡片；窗口里显示对齐的文字表格；另存 Excel 到本次日志文件夹。
# 步骤（小柒 2026-10-23 确认）：首页 → 仓库管理 → 数据管理 → 任务管理 → 展开
#   → 任务大类=增值服务 → 任务状态=待处理 → 清空“创建时间”
#   → 每个区域：所属区域=该区 → “待增值时间”空着查一次 = 全部时间的总数（用来查漏单）
#                → 今天 + 往前 5 个自然日，每天填 YYYY-MM-DD 00:00:00 ~ 23:59:59 查一次，读“共 N 条记录”
#   更早未处理 = 全部总数 − 这 6 天之和；大于 0 说明有漏掉的老单，会标 ⚠。
# 防连点：两次查询至少隔 1 秒；WMS 提示“点击次数过多”时等 3、5、8、8 秒重查（最多 4 次），
#   还不行就这一格标“失败”，绝不记 0。每次等待都写进日志。
# 排错：每次运行的详细记录在 日志\日期_时间_增值待处理\ 文件夹里。
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

根目录 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(根目录))
from 公共 import 模块参数, 表格  # noqa: E402
from 公共.wms import 进入页面  # noqa: E402
from 公共.表单 import 下拉选择, 下拉选项, 填日期, 清空日期, 日期值  # noqa: E402
from 公共.错误 import 自动化错误, 页面改版, 网络超时, 数据不完整  # noqa: E402

模块名 = "增值待处理"
默认参数 = {"区域": ["D区", "E区"], "发到飞书": True, "往前天数": 5}
查询接口 = "task/pageV1"
最小间隔秒 = 1.0
重试等待秒 = [3, 5, 8, 8]
星期 = "一二三四五六日"


class _查询器:
    """点“查询”并拿到结果；负责防连点（最小间隔 + 检测“点击次数过多”后退避重查）。"""

    def __init__(self, 页面, 记录):
        self.页面, self.记录 = 页面, 记录
        self.上次 = 0.0
        self.间隔 = 最小间隔秒

    def 查(self, 区域字母, 日期范围):
        for 第几次 in range(len(重试等待秒) + 1):
            等 = self.间隔 - (time.time() - self.上次)
            if 等 > 0:
                time.sleep(等)
            try:
                with self.页面.expect_response(lambda r: 查询接口 in r.url and "pageNo=1" in r.url, timeout=30000) as 等待:
                    self.页面.get_by_role("button", name="查询").first.click()
                回应 = 等待.value
                数据 = 回应.json()
            except Exception:
                raise 自动化错误(网络超时, "点“查询”后 30 秒内没有拿到结果。")
            finally:
                self.上次 = time.time()
            if isinstance(数据, dict) and 数据.get("code") == 100010:   # 点击次数过多
                if 第几次 < len(重试等待秒):
                    秒 = 重试等待秒[第几次]
                    self.记录.写(f"    WMS 提示“点击次数过多”，等 {秒} 秒后重查（第 {第几次 + 1} 次）")
                    self.间隔 = max(self.间隔, 2.0)   # 本次运行后面的查询放慢一点
                    time.sleep(秒)
                    continue
                raise 自动化错误(网络超时, "WMS 一直提示“点击次数过多”，重查 4 次仍不行。")
            if not isinstance(数据, dict) or 数据.get("code") != 0 or 数据.get("data") is None:
                raise 自动化错误(网络超时, "WMS 返回了错误：" + str(数据)[:200])
            return self._核对(回应.url, 数据["data"], 区域字母, 日期范围)

    def _核对(self, 网址, 数据, 区域字母, 日期范围):
        参数 = parse_qs(urlparse(网址).query)
        应有 = {"taskCategories": "9", "taskStatus": "0", "shelvesRegionNum": 区域字母}
        for 键, 值 in 应有.items():
            if 参数.get(键, [None])[0] != 值:
                raise 自动化错误(页面改版, f"查询条件没有生效（{键}={参数.get(键)}），本次结果不可信。")
        if any(键.startswith("createTime") for 键 in 参数):
            raise 自动化错误(页面改版, "“创建时间”条件没有清空，本次结果不可信。")
        实际范围 = (参数.get("addValueTimeStart[0]", [None])[0], 参数.get("addValueTimeStart[1]", [None])[0])
        if 实际范围 != (日期范围 or (None, None)):
            raise 自动化错误(页面改版, f"待增值时间不对：应为 {日期范围 or '空'}，实际 {实际范围}。")
        总数 = 数据.get("total")
        if 总数 is None and not 数据.get("list"):
            总数 = 0   # 没有记录时 WMS 返回 list=null、total=null；下面还会核对页面上确实是“共 0 条记录”
        if not isinstance(总数, int):
            raise 自动化错误(数据不完整, "读不到总条数。")
        try:   # 核对：页面上显示的“共 N 条记录”和读到的一致
            self.页面.locator("span").filter(has_text=re.compile(f"^共 {总数} 条记录$")).first.wait_for(timeout=10000)
        except Exception:
            raise 自动化错误(数据不完整, f"页面显示的条数和读到的 {总数} 不一致。")
        return 总数


def 要查的日期(今天, 往前天数):
    return [今天 - timedelta(days=n) for n in range(往前天数, -1, -1)]   # 从旧到新，最后是今天


def 失败结果(e, 开始时间, 参数=None):
    参数 = 参数 or 默认参数
    日期们 = 要查的日期(开始时间.date(), 参数.get("往前天数", 5))
    return {"状态": "失败", "数量": None, "开始时间": 开始时间, "区域们": 参数["区域"], "日期们": 日期们,
            "表": {}, "全部": {}, "错误信息": e.一句话(模块名), "错误列表": [e]}


def 运行(页面, 记录, 参数=None):
    参数 = 参数 or 默认参数
    开始时间 = datetime.now()
    区域们 = 参数["区域"]
    日期们 = 要查的日期(开始时间.date(), 参数.get("往前天数", 5))
    表 = {区: {} for 区 in 区域们}     # 表[区域][日期] = 数字 或 "失败"
    全部 = {}                          # 全部[区域] = 全部时间的总数 或 "失败"
    错误 = []
    try:
        with 记录.步骤("进入 仓库管理 → 数据管理 → 任务管理"):
            进入页面(页面, ["仓库管理", "数据管理", "任务管理"], 等待接口=查询接口)
        with 记录.步骤("展开更多条件"):
            页面.get_by_text("展开").first.click()
            页面.wait_for_timeout(800)
        with 记录.步骤("任务大类选“增值服务”、任务状态选“待处理”"):
            下拉选择(页面, "任务大类", "增值服务")
            下拉选择(页面, "任务状态", "待处理")
        with 记录.步骤("清空“创建时间”"):
            清空日期(页面, "创建时间")
        with 记录.步骤("读取“所属区域”的选项"):
            选项 = [x for x in 下拉选项(页面, "所属区域") if x != "全部"]
            if 选项:
                模块参数.保存区域选项(选项)
            记录.写(f"    WMS 里的区域：{'、'.join(选项)}")
    except 自动化错误 as e:
        return 失败结果(e, 开始时间, 参数)

    查询器 = _查询器(页面, 记录)
    for 区域 in 区域们:
        字母 = 区域.replace("区", "")
        try:
            with 记录.步骤(f"{区域}：选择区域，查全部时间的总数"):
                下拉选择(页面, "所属区域", 区域)
                清空日期(页面, "待增值时间")
                全部[区域] = 查询器.查(字母, None)
                记录.写(f"    全部时间：{全部[区域]}")
        except 自动化错误 as e:
            全部[区域] = "失败"
            错误.append(e)
            for 日 in 日期们:
                表[区域][日] = "失败"
            continue
        for 日 in 日期们:
            范围 = (f"{日:%Y-%m-%d} 00:00:00", f"{日:%Y-%m-%d} 23:59:59")
            try:
                with 记录.步骤(f"{区域}：{日:%m/%d}"):
                    填日期(页面, "待增值时间", *范围)
                    表[区域][日] = 查询器.查(字母, 范围)
                    记录.写(f"    {日:%m/%d}：{表[区域][日]}")
            except 自动化错误 as e:
                表[区域][日] = "失败"
                错误.append(e)

    格数 = len(区域们) * (len(日期们) + 1)
    失败格 = sum(1 for 区 in 区域们 for 日 in 日期们 if 表[区][日] == "失败") + sum(1 for 区 in 区域们 if 全部[区] == "失败")
    if 失败格 == 格数:
        状态 = "失败"
    elif 失败格:
        状态 = "不完整"
    else:
        状态 = "成功"
    合计 = sum(v for v in 全部.values() if isinstance(v, int))
    return {"状态": 状态, "数量": None if 状态 == "失败" else 合计, "开始时间": 开始时间,
            "区域们": 区域们, "日期们": 日期们, "表": 表, "全部": 全部,
            "错误信息": "；".join(e.一句话(模块名) for e in 错误), "错误列表": 错误}


def _求和(值们):
    if any(v == "失败" for v in 值们):
        return "失败"
    return sum(值们)


def 做表(结果):
    """返回 (列名, 行们, 更早合计)。行们从上到下：更早未处理、6 天（旧→新）、合计。"""
    区域们, 日期们, 表, 全部 = 结果["区域们"], 结果["日期们"], 结果["表"], 结果["全部"]
    今天 = 结果["开始时间"].date()
    列名 = ["日期"] + 区域们 + ["合计"]
    更早 = {}
    for 区 in 区域们:
        六天 = _求和([表.get(区, {}).get(日, "失败") for 日 in 日期们])
        总 = 全部.get(区, "失败")
        更早[区] = "失败" if "失败" in (六天, 总) else max(0, 总 - 六天)
    行们 = []
    更早行 = [更早[区] for 区 in 区域们]
    更早合计 = _求和(更早行)
    标 = "⚠ " if isinstance(更早合计, int) and 更早合计 > 0 else ""
    行们.append([f"{标}更早未处理"] + 更早行 + [更早合计])
    for 日 in 日期们:
        值们 = [表.get(区, {}).get(日, "失败") for 区 in 区域们]
        名 = f"{日:%m/%d} 周{星期[日.weekday()]}" + ("（今天）" if 日 == 今天 else "")
        行们.append([名] + 值们 + [_求和(值们)])
    总们 = [全部.get(区, "失败") for 区 in 区域们]
    行们.append(["**合计**"] + [f"**{v}**" for v in 总们] + [f"**{_求和(总们)}**"])
    return 列名, 行们, 更早合计


def 组成消息(结果, 文件夹名, 用时=None):
    时间 = 结果["开始时间"]
    标题 = f"增值待处理（截至 {时间:%m/%d %H:%M}）"
    备注 = []
    if 结果.get("表") or 结果.get("全部"):
        列名, 行们, 更早合计 = 做表(结果)
        if isinstance(更早合计, int) and 更早合计 > 0:
            备注.append(f"⚠ **有 {更早合计} 单超过 {len(结果['日期们'])} 天仍未处理**（见“更早未处理”一行），请检查是否漏单。")
    else:
        列名, 行们, 更早合计 = None, [], None
    if 结果["状态"] != "成功":
        备注.append(f"⚠ 状态：{结果['状态']}" + ("（标“失败”的格子没查到，不是 0）" if 结果["状态"] == "不完整" else ""))
        for e in 结果.get("错误列表", []):
            备注.append(e.一句话(模块名))
        备注.append(f"日志：{文件夹名}")
    颜色 = "blue" if 结果["状态"] == "成功" and not (isinstance(更早合计, int) and 更早合计 > 0) else "orange"
    if 结果["状态"] == "失败":
        颜色 = "red"

    文字 = 标题 + "\n\n" + (表格.文字表格(列名, 行们) if 列名 else "（没有查到数据）")
    if 备注:
        文字 += "\n\n" + "\n".join(x.replace("**", "") for x in 备注)
    附件 = None
    if 列名:
        try:
            附件 = str(根目录 / "日志" / 文件夹名 / f"增值待处理_{时间:%Y%m%d_%H%M}.xlsx")
            表格.存Excel(附件, 标题, 列名, 行们, 备注)
        except Exception:
            附件 = None
    卡片 = 表格.卡片(标题, 列名, 行们, 备注, 颜色) if 列名 else \
        {"schema": "2.0", "header": {"title": {"tag": "plain_text", "content": 标题}, "template": "red"},
         "body": {"elements": [{"tag": "markdown", "content": "\n".join(备注) or "没有查到数据"}]}}
    return {"文字": 文字, "卡片": 卡片, "附件": 附件, "标题": 标题, "备注": [x.replace("**", "") for x in 备注],
            "表们": [("按日期", 列名, 行们)] if 列名 else []}, ""


if __name__ == "__main__":
    # 单独运行这个模块。参数：--可见 显示浏览器窗口（排查用）；--不发送 不发飞书
    from 公共.运行 import 运行模块们
    结果 = 运行模块们([模块名], 可见="--可见" in sys.argv, 发送="--不发送" not in sys.argv)
    sys.exit(0 if 结果["结果们"][0]["状态"] in ("成功", "无数据") else 1)
