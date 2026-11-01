# 只给小柒看效果用的临时脚本（2026-11-01，可随时删）。
# 用 2026-11-01 只读探索拿到的真实数字（各区 合箱增值 / 单箱增值 / 全部）造 3 份假结果，
# 按程序自己的界面零件画出结果页，再把新零件「格子小卡片」贴在格子上截图。
# 不查 WMS、不发飞书、不写快照。截图放 日志\效果图_格子卡片\（日志\ 不进 Git）。
# 用法：.venv\Scripts\python.exe 自测\效果图_格子卡片.py
import json
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "windows"

自测 = Path(__file__).resolve().parent
根目录 = 自测.parent
sys.path.insert(0, str(根目录))
sys.path.insert(0, str(自测))

import 回归测试 as 测  # noqa: E402  （只用它的 隔离() / 应用()）

测.隔离()
app = 测.应用()

import importlib  # noqa: E402

from PySide6.QtCore import QPoint, Qt  # noqa: E402

from 公共 import 窗口, 表格 as 表格包  # noqa: E402
from 公共.界面.格子卡片 import 格子卡片  # noqa: E402
from 公共.错误 import 自动化错误, 数据不完整  # noqa: E402
from 公共.结果页.数量页 import 数量表格  # noqa: E402

窗口.日志根 = 测.日志.日志根
窗口.专用窗口开着 = lambda: False

出图 = 根目录 / "日志" / "效果图_格子卡片"
出图.mkdir(parents=True, exist_ok=True)
for f in 出图.glob("*.png"):
    f.unlink()

宽, 窄 = (1600, 900), (1000, 640)

待处理 = importlib.import_module("公共.待处理")
待增值 = importlib.import_module("模块.待增值")


def 等(秒=0.2):
    t = time.time()
    while time.time() - t < 秒:
        app.processEvents()
        time.sleep(0.01)


# ---------------- 假数据（数字来自 2026-11-01 只读探索） ----------------
今天 = date(2026, 11, 1)
日们 = [date(2026, 10, 27), date(2026, 10, 28), date(2026, 10, 29), date(2026, 10, 30), 今天]


def 天(数们):
    return dict(zip(日们[:len(数们)], 数们))


def 回(全部, 数们):
    return {"全部": 全部, "天": 天(数们), "起点": 日们[0], "对上": True, "差": 0}


# 合箱 / 单箱 分开的数字（每天加起来 = 那天的全部）
合箱 = {"D区": 回(602, [0, 190, 292, 120]), "E区": 回(561, [0, 300, 166, 95]),
       "A区": 回(65, [0, 20, 30, 15]), "C区": 回(602, [0, 200, 302, 100]), "F区": 回(282, [0, 100, 150, 32])}
单箱 = {"D区": 回(134, [0, 40, 64, 30]), "E区": 回(313, [0, 180, 57, 76]),
       "A区": 回(34, [0, 10, 14, 10]), "C区": 回(73, [0, 20, 33, 20]), "F区": 回(75, [0, 25, 40, 10])}


def 合并(区):
    甲, 乙 = 合箱[区], 单箱[区]
    return {"全部": 甲["全部"] + 乙["全部"],
            "天": {d: 甲["天"][d] + 乙["天"][d] for d in 甲["天"]},
            "起点": min(甲["起点"], 乙["起点"]), "对上": True, "差": 0}


def 造结果(组们, 时间, 状态="成功", 错们=None):
    数据 = {"增值服务": {区: 合并(区) for _, 区们 in 组们 for 区 in 区们}}
    return {"状态": 状态, "数量": sum(v["全部"] for v in 数据["增值服务"].values()),
            "开始时间": 时间, "组们": 组们, "数据": 数据, "错误信息": "",
            "错误列表": 错们 or [], "范围提醒": []}


def 拆分(组们):
    return {"合箱增值": {区: 合箱[区] for _, 区们 in 组们 for 区 in 区们},
            "单箱增值": {区: 单箱[区] for _, 区们 in 组们 for 区 in 区们}}


def 造项(结果, 状态=None, 错们=None):
    消息 = 待增值.组成消息(结果, "效果图", 用时=64)[0]
    项 = {"模块": "待增值", "显示名": "待增值", "状态": 状态 or 结果["状态"], "飞书": ("未发送", "本次选择不发送"),
          "日志文件夹": "", "数量": 结果["数量"], "时间": 结果["开始时间"], "附件": None,
          "错误们": 错们 or [], "标题": ""}
    for 键, 值 in 消息.items():
        项.setdefault(键, 值)
    项["附件"] = None
    项["状态"] = 状态 or 结果["状态"]
    return 项


# ---------------- 格子小卡片：从假数据算出每一格写什么 ----------------
def 卡片们(结果, 组名, 区们):
    """{(行号, 列号): 卡片数据}。合计 = 表格那一格的字；对不上就不给这一格（方案 7.2 的校验）。"""
    主列, 主行, _ = 待处理.做组表(结果, 组名, 区们, ["增值服务"], 至少=True)
    列合, 行合, _ = 待处理.做组表({**结果, "数据": 拆分结果(结果)}, 组名, 区们, ["合箱增值"], 至少=True)
    列单, 行单, _ = 待处理.做组表({**结果, "数据": 拆分结果(结果)}, 组名, 区们, ["单箱增值"], 至少=True)
    出 = {}
    for r in range(len(主行)):
        if len(主行[r]) != len(行合[r]):
            continue
        for c in range(1, len(主列)):
            合, 单, 总 = 行合[r][c], 行单[r][c], 主行[r][c]
            行名 = str(主行[r][0]).replace("**", "")
            列名 = 主列[c]
            if 列名 == "" or 行名 == "":
                continue
            如果没查到 = 总 == "失败" or 合 == "失败" or 单 == "失败"
            if 如果没查到:
                出[(r, c)] = {"标题": f"{列名} · {_行标题(行名)}",
                              "行们": [["合箱增值", "没查到（不是 0）"], ["单箱增值", "没查到（不是 0）"]],
                              "合计": "—", "提醒": None}
                continue
            出[(r, c)] = {"标题": f"{列名} · {_行标题(行名)}",
                          "行们": [["合箱增值", f"{合} 单"], ["单箱增值", f"{单} 单"]],
                          "合计": f"{总} 单", "提醒": None}
    return 出


_拆分缓存 = {}


def 拆分结果(结果):
    if id(结果) not in _拆分缓存:
        _拆分缓存[id(结果)] = 结果.get("拆分") or 拆分(结果["组们"])
    return _拆分缓存[id(结果)]


def _行标题(行名):
    return 行名.replace("（今天）", "").replace("（这天及以前都是 0）", "")


def 贴卡片(卡表, 找行=None, 找列=None, 列名们=None, 首行=None):
    """在结果页上找到指定的那张表，把卡片贴在 (找行, 找列) 那一格旁边。"""
    候选 = []
    for t in w.findChildren(数量表格):
        if t.columnCount() != len(列名们) or t.rowCount() == 0:
            continue
        if [t.horizontalHeaderItem(c).text() for c in range(t.columnCount())] != list(列名们):
            continue
        if not str(t.item(0, 0).text()).startswith(首行):
            continue
        候选.append(t)
    if not 候选:
        raise RuntimeError(f"页面上找不到这张表：{列名们}")
    表 = 候选[-1]
    列们 = [表.horizontalHeaderItem(c).text() for c in range(表.columnCount())]
    c = 列们.index(找列)
    r = next(i for i in range(表.rowCount()) if str(表.item(i, 0).text()).startswith(找行))
    数据 = dict(卡表[(r, c)]) if (r, c) in 卡表 else None
    if 数据 is None:
        raise RuntimeError(f"这一格没有卡片：{找行}|{找列}")
    卡 = 格子卡片(数据, 表.window())
    卡.show()
    rect = 表.visualItemRect(表.item(r, c))
    全局 = 表.viewport().mapToGlobal(QPoint(rect.x(), rect.y()))
    from PySide6.QtCore import QRect
    卡.设位置(QRect(全局, rect.size()), 表.window())
    卡.raise_()
    return 卡


def 表签名(结果, 组名, 区们):
    列, 行们, _ = 待处理.做组表(结果, 组名, 区们, ["增值服务"], 至少=True)
    return 列, str(行们[0][0]).split(" ")[0]


# ---------------- 打开窗口 ----------------
w = 窗口.主窗口()
w.setAttribute(Qt.WA_DontShowOnScreen)
w.resize(*宽)
w.show()
等(0.4)


def 截图(名, 尺=宽, 放=None):
    """先按目标尺寸排好版，再贴卡片（不然卡片会按旧尺寸定位），再抓图。"""
    w.resize(*尺)
    等(0.7)
    卡 = 放() if 放 else None
    等(0.4)
    w.grab().save(str(出图 / f"{名}.png"))
    if 卡 is not None:
        卡.hide()
    print(f"  ✔ {名}.png")


# ===== 场景 1：瑞江，宽窗口，E区 10/30 的卡片 =====
组1 = [("瑞江仓库", ["D区", "E区"])]
结果1 = 造结果(组1, datetime(2026, 11, 1, 10, 12, 30))
结果1["拆分"] = 拆分(组1)
w._显示结果([造项(结果1)])
等(0.6)
w.运行页.列表.setCurrentRow(0)
等(0.5)
_列1, _首1 = 表签名(结果1, "瑞江仓库", ["D区", "E区"])
截图("01_瑞江_宽_E区10-30", 宽, 放=lambda: 贴卡片(卡片们(结果1, "瑞江仓库", ["D区", "E区"]),
                                              找行="10/30", 找列="E区", 列名们=_列1, 首行=_首1))

# ===== 场景 2：瑞江，窄窗口，最右一列“瑞江合计”的卡片（自动放到格子左边）=====
截图("02_瑞江_窄_瑞江合计10-30", 窄, 放=lambda: 贴卡片(卡片们(结果1, "瑞江仓库", ["D区", "E区"]),
                                                     找行="10/30", 找列="瑞江合计", 列名们=_列1, 首行=_首1))

# ===== 场景 3：有一格没查到 =====
结果3 = 造结果(组1, datetime(2026, 11, 1, 10, 12, 30))
结果3["数据"]["增值服务"]["E区"] = "失败"
结果3["状态"] = "不完整"
结果3["数量"] = 736
错3 = 自动化错误(数据不完整, "E区 没查到（不是 0）")
错3.步骤 = "增值服务 E区：清空待增值时间，查全部总数，再按天往前查"
错3框 = {"步骤": 错3.步骤, "原因": 错3.原因, "建议": 错3.建议}
w._显示结果([造项(结果3, 错们=[错3框])])
等(0.6)
w.运行页.列表.setCurrentRow(0)
等(0.5)
_列3, _首3 = 表签名(结果3, "瑞江仓库", ["D区", "E区"])
截图("03_瑞江_一格没查到", 宽, 放=lambda: 贴卡片(卡片们(结果3, "瑞江仓库", ["D区", "E区"]),
                                              找行="10/30", 找列="E区", 列名们=_列3, 首行=_首3))

# ===== 场景 4：核对没通过（卡片带橙字 + 结果页错误块）=====
结果4 = 造结果(组1, datetime(2026, 11, 1, 10, 12, 30), 状态="不完整")
错4 = 自动化错误(数据不完整, "E区：合箱增值 561 + 单箱增值 313 = 874，任务小类“全部”是 886，"
                          "复查后“全部”比合箱 + 单箱多 12 单（超过允许的 5 单；可能还有别的任务小类，"
                          "或查的时候任务在变），请到 WMS 看一下")
错4.步骤 = "E区 核对“全部 = 合箱 + 单箱”"
结果4["错误列表"] = [错4]
错4框 = {"步骤": 错4.步骤, "原因": 错4.原因, "建议": 错4.建议}
结果4["数量"] = 736 + 886
w._显示结果([造项(结果4, 错们=[错4框])])
等(0.6)
w.运行页.列表.setCurrentRow(0)
等(0.5)
卡表4 = 卡片们(结果4, "瑞江仓库", ["D区", "E区"])
for 键 in 卡表4:
    if 键[1] == 2:
        卡表4[键]["提醒"] = "⚠ 全部 886，和合箱 + 单箱差 12 单"
_列4, _首4 = 表签名(结果4, "瑞江仓库", ["D区", "E区"])
截图("04_瑞江_核对没通过", 宽, 放=lambda: 贴卡片(卡表4, 找行="10/30", 找列="E区",
                                            列名们=_列4, 首行=_首4))

# ===== 场景 5：松户 A/C/F 三区的表 =====
组5 = [("松户仓库", ["A区", "C区", "F区"])]
结果5 = 造结果(组5, datetime(2026, 11, 1, 10, 12, 30))
结果5["拆分"] = 拆分(组5)
w._显示结果([造项(结果5)])
等(0.6)
w.运行页.列表.setCurrentRow(0)
等(0.5)
_列5, _首5 = 表签名(结果5, "松户仓库", ["A区", "C区", "F区"])
截图("05_松户_三区_C区10-29", 宽, 放=lambda: 贴卡片(卡片们(结果5, "松户仓库", ["A区", "C区", "F区"]),
                                                    找行="10/29", 找列="C区", 列名们=_列5, 首行=_首5))
w.close()

# ---------------- Excel：合箱 / 单箱 两张分表 + 核对表 ----------------
def 出Excel(组们, 文件名):
    结果 = 造结果(组们, datetime(2026, 11, 1, 10, 12, 30))
    结果["拆分"] = 拆分(组们)
    表们 = []
    核对行们 = []
    for 组名, 区们 in 组们:
        列W, 行W, _ = 待处理.做组表(结果, 组名, 区们, ["增值服务"], 至少=True)
        列合, 行合, _ = 待处理.做组表({**结果, "数据": 结果["拆分"]}, 组名, 区们, ["合箱增值"], 至少=True)
        列单, 行单, _ = 待处理.做组表({**结果, "数据": 结果["拆分"]}, 组名, 区们, ["单箱增值"], 至少=True)
        表们 += [(组名, 列W, 行W), (f"{组名}_合箱增值", 列合, 行合), (f"{组名}_单箱增值", 列单, 行单)]
        for 区 in 区们:
            合, 单 = 合箱[区]["全部"], 单箱[区]["全部"]
            核对行们.append([区, 合, 单, 合 + 单, 合 + 单, 0, "对上"])
        合计 = sum(合箱[区]["全部"] for 区 in 区们) + sum(单箱[区]["全部"] for 区 in 区们)
        核对行们.append([f"**{组名.replace('仓库', '')}合计**", f"**{sum(合箱[区]['全部'] for 区 in 区们)}**",
                       f"**{sum(单箱[区]['全部'] for 区 in 区们)}**", f"**{合计}**", f"**{合计}**", "**0**", "**对上**"])
    表们.append(("核对", ["区", "合箱增值", "单箱增值", "合箱+单箱", "全部（任务小类=全部）", "差", "结果"], 核对行们))
    路径 = 出图 / 文件名
    表格包.存Excel多表(str(路径), "待增值（截至 11/01 10:12）", 表们, ["效果图：假数据，数字来自 2026-11-01 探索"])
    print(f"  ✔ {路径.name}（{len(表们)} 个工作表：{'、'.join(t[0] for t in 表们)}）")
    return 表们


瑞江表 = 出Excel([("瑞江仓库", ["D区", "E区"])], "效果图_瑞江.xlsx")
松户表 = 出Excel([("松户仓库", ["A区", "C区", "F区"])], "效果图_松户.xlsx")

# ---------------- 把这几张表画成一张图（Excel 里的样子）----------------
def 表HTML(名, 列名, 行们):
    th = "".join(f"<th class='{'l' if i == 0 else 'r'}'>{c}</th>" for i, c in enumerate(列名))
    trs = []
    for 行 in 行们:
        粗 = str(行[0]).startswith("**")
        格 = "".join(f"<td class='{'b' if 粗 else ''} {'l' if i == 0 else 'r'}'>{str(v).replace('**', '')}</td>"
                    for i, v in enumerate(行))
        trs.append(f"<tr>{格}</tr>")
    return f"<div class='sheet'><div class='name'>{名}</div><table><tr>{th}</tr>{''.join(trs)}</table></div>"


def 画Excel(表们, 名):
    html = """<!doctype html><meta charset="utf-8"><style>
    body{margin:0;padding:20px;background:#f3f3f3;font-family:"Microsoft YaHei UI",sans-serif;font-size:13px}
    .sheet{background:#fff;border:1px solid #d0d0d0;margin-bottom:16px;padding:0 0 12px}
    .name{background:#e8e8e8;padding:4px 10px;font-weight:bold;border-bottom:1px solid #d0d0d0}
    table{border-collapse:collapse;margin:10px 0 0 10px}
    th,td{border:1px solid #d9d9d9;padding:3px 10px;font-weight:normal}
    th{background:#f2f2f2;text-align:center}
    td.l{text-align:left} td.r{text-align:right} td.b{font-weight:bold;background:#fff}
    </style>""" + "".join(表HTML(*t) for t in 表们)
    (出图 / f"{名}.html").write_text(html, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        器 = p.chromium.launch(channel="chrome", headless=True)
        页 = 器.new_page(viewport={"width": 1500, "height": 900})
        页.goto((出图 / f"{名}.html").as_uri())
        页.wait_for_timeout(300)
        页.screenshot(path=str(出图 / f"{名}.png"), full_page=True)
        器.close()
    print(f"  ✔ {名}.png")


画Excel(瑞江表, "06_Excel_瑞江")
画Excel(松户表, "07_Excel_松户")

# ---------------- 飞书卡片：两个折叠条里的文字表（不发飞书）----------------
def 飞书片段(组名, 区们):
    结果 = 造结果([(组名, 区们)], datetime(2026, 11, 1, 10, 12, 30))
    结果["拆分"] = 拆分([(组名, 区们)])
    段 = []
    for 类 in ("合箱增值", "单箱增值"):
        列2, 行2, _ = 待处理.做组表({**结果, "数据": 结果["拆分"]}, 组名, 区们, [类])
        段.append(f"【折叠条：**{类}**（平时收起，点开看这个）】\n" + 表格包.文字表格(列2, 行2))
    return "\n\n".join(段)


飞书文字 = ("飞书卡片里多出来的两个折叠条（主表不变；这里只贴折叠条里的内容）\n\n"
          + 飞书片段("瑞江仓库", ["D区", "E区"]) + "\n\n" + "=" * 60 + "\n\n"
          + 飞书片段("松户仓库", ["A区", "C区", "F区"]))
(出图 / "08_飞书折叠条.txt").write_text(飞书文字, encoding="utf-8")
print(飞书文字)

print(f"\n截图/文件都在：{出图}")
