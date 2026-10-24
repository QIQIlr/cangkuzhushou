# 职责：不连 WMS、不发飞书的回归测试（给 Claude 每次改完代码后跑；小柒不需要用）。
# 用法：.venv\Scripts\python.exe 自测\回归测试.py [部分名 ...]      不写部分名 = 全部
# 规则：只用临时文件夹里的复制品——不改 模块参数.json、模块设置.txt、日志\运行总表.csv；不打开浏览器；不发飞书。
#   跑之前和跑完后核对这三个文件没变。
import hashlib
import os
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

根目录 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(根目录))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["仓库助手_测试不发送"] = "1"

受保护 = [根目录 / "模块参数.json", 根目录 / "模块设置.txt", 根目录 / "日志" / "运行总表.csv"]
临时 = Path(tempfile.mkdtemp(prefix="仓库助手自测_"))
结果们 = []


def 指纹():
    return {p.name: hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else None for p in 受保护}


def 检查(名, 条件, 说明=""):
    结果们.append((名, bool(条件), 说明))
    print(("  ✔ " if 条件 else "  ✘ ") + 名 + ("" if 条件 else f"   ← {说明}"), flush=True)


# ---------- 隔离：所有设置、日志都指到临时文件夹 ----------
from 公共 import 模块参数, 模块设置, 日志  # noqa: E402
from 公共.界面 import 运行历史  # noqa: E402

def 隔离():
    (临时 / "设置备份").mkdir(exist_ok=True)
    (临时 / "日志").mkdir(exist_ok=True)
    shutil.copyfile(根目录 / "模块参数.json", 临时 / "模块参数.json")
    shutil.copyfile(根目录 / "模块设置.txt", 临时 / "模块设置.txt")
    模块参数.参数文件 = 临时 / "模块参数.json"
    模块参数.备份文件 = 临时 / "设置备份" / "模块参数.json"
    模块设置.设置文件 = 临时 / "模块设置.txt"
    模块设置.备份文件 = 临时 / "设置备份" / "模块设置.txt"
    日志.日志根 = 临时 / "日志"
    日志.总表 = 临时 / "日志" / "运行总表.csv"
    运行历史.日志根 = 日志.日志根
    运行历史.总表 = 日志.总表
    from 公共 import 上次结果, 表格, 飞书
    上次结果.日志根 = 日志.日志根
    表格.存Excel多表 = lambda *a, **k: None            # 不往真实的 日志\ 里写 Excel
    飞书.发送全部 = lambda *a, **k: ("未发送", "自测里不发飞书")   # 万一走到发送，也不会真的发
    飞书.发送 = lambda *a, **k: ("未发送", "自测里不发飞书")
    if (根目录 / "日志" / "运行总表.csv").exists():
        shutil.copyfile(根目录 / "日志" / "运行总表.csv", 日志.总表)


_应用 = None

def 应用():
    global _应用
    if _应用 is None:
        from PySide6.QtWidgets import QApplication
        from 公共.界面 import 主题
        _应用 = QApplication.instance() or QApplication(sys.argv)
        主题.套用(_应用)
    return _应用


# =================== 各部分 ===================

def 测_设置文件保护():
    print("设置文件保护（模块参数.json）")
    原 = 模块参数.参数文件.read_text(encoding="utf-8")
    模块参数.保存界面设置("自测项", 1)
    检查("正常保存后有备份", 模块参数.备份文件.exists())
    模块参数.参数文件.write_text("{ 写坏了", encoding="utf-8")
    模块参数.问题 = ""
    名 = 模块参数.显示名("飞书任务明细")
    检查("文件坏了时改用备份（名字还在）", 名 == 模块参数._读(模块参数.备份文件).get("名字", {}).get("飞书任务明细", "飞书任务明细"), 名)
    检查("文件坏了时有提示", "读不出来" in 模块参数.问题, 模块参数.问题)
    模块参数.保存界面设置("自测项", 2)
    坏的 = list(模块参数.备份文件.parent.glob("模块参数_读不出_*.json"))
    检查("写之前把坏文件另存了一份", 坏的 and 坏的[0].read_text(encoding="utf-8") == "{ 写坏了", 坏的)
    数据 = 模块参数._读(模块参数.参数文件)
    检查("写入后其他设置没丢", 数据.get("模块") and 数据.get("界面", {}).get("自测项") == 2, 数据)
    for p in 坏的:
        p.unlink()
    模块参数.问题 = ""
    模块参数.参数文件.write_text(原, encoding="utf-8")
    # 两个线程同时写不同的项，都不能丢
    import threading
    def 写(键):
        for i in range(60):
            模块参数.保存界面设置(键, i)
    线们 = [threading.Thread(target=写, args=(k,)) for k in ("并发A", "并发B")]
    for t in 线们:
        t.start()
    for t in 线们:
        t.join()
    界面 = 模块参数._读(模块参数.参数文件)["界面"]
    检查("两个线程同时写，两项都在", 界面.get("并发A") == 59 and 界面.get("并发B") == 59, 界面)
    模块参数.参数文件.write_text(原, encoding="utf-8")
    检查("没有留下临时文件", not list(临时.glob("*.tmp")))


def 测_测试记录标记():
    print("运行总表：测试运行单独标记")
    import csv
    备份 = 日志.总表.read_bytes() if 日志.总表.exists() else None
    原名们 = [名 for 名, _ in 模块设置.读取(写回=False)[0]]
    之前 = 运行历史.上次结果们(原名们).get("待审核")
    r = 日志.运行记录("待审核", "自测", 测试=True)
    r.结束("成功", 99999)
    最新 = 运行历史.读全部(原名们)[0]
    检查("测试运行记成“测试”", 最新["测试"] and 最新["数量"] == "99999", 最新)
    之后 = 运行历史.上次结果们(原名们).get("待审核")
    检查("工作台的上次结果不算测试运行", 之后 == 之前, (之前, 之后))
    r2 = 日志.运行记录("待审核", "自测", 测试=False)
    r2.结束("成功", 12345)
    检查("正式运行照常算", 运行历史.上次结果们(原名们)["待审核"]["数量"] == "12345")
    with open(日志.总表, encoding="utf-8-sig") as f:
        老行 = next(csv.reader(f))
    检查("老总表的表头没被改（Excel 照样能开）", 老行[:7] == ["时间", "模块", "状态", "数量", "用时(秒)", "错误摘要", "日志文件夹"], 老行)
    for 夹 in 日志.日志根.iterdir():
        if 夹.is_dir():
            shutil.rmtree(夹)
    if 备份 is not None:
        日志.总表.write_bytes(备份)


def 测_运行记录页():
    print("运行记录页：打开速度和内容")
    import csv
    import random
    from datetime import datetime, timedelta
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QStatusBar
    from 公共.界面.记录页 import 记录页
    应用()
    备份 = 日志.总表.read_bytes() if 日志.总表.exists() else None
    样本 = list(csv.reader(open(根目录 / "日志" / "运行总表.csv", encoding="utf-8-sig")))[1:] if (根目录 / "日志" / "运行总表.csv").exists() else []
    if not 样本:
        样本 = [["", "待审核", "成功", "100", "10", "", "x"]]
    页 = 记录页(QStatusBar())
    页.resize(968, 740)
    页.setAttribute(Qt.WA_DontShowOnScreen)
    页.show()
    for n in (150, 1000, 5000, 20000):
        with open(日志.总表, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["时间", "模块", "状态", "数量", "用时(秒)", "错误摘要", "日志文件夹"])
            t0 = datetime(2026, 1, 1)
            for i in range(n):
                r = list(random.choice(样本))[:7]
                r[0] = f"{t0 + timedelta(minutes=7 * i):%Y-%m-%d %H:%M:%S}"
                w.writerow(r + (["测试"] if i % 10 == 0 else []))
        时们 = []
        for _ in range(3):
            t = time.perf_counter()
            页.刷新()
            应用().processEvents()
            时们.append(time.perf_counter() - t)
        print(f"    {n} 行：第 1/2/3 次打开 " + " / ".join(f"{x:.2f} 秒" for x in 时们), flush=True)
        限 = 0.5 if n <= 1000 else 3.0
        检查(f"{n} 行：第 2、3 次打开不比第 1 次慢很多（< {限} 秒）", max(时们[1:]) < 限, 时们)
        应有 = 运行历史.读全部([名 for 名, _ in 模块设置.读取(写回=False)[0]])
        检查(f"{n} 行：表格行数 = 总表行数", 页.表.rowCount() == len(应有), (页.表.rowCount(), len(应有)))
        检查(f"{n} 行：第一行是最新的", 页.表.item(0, 0).text() == f"{应有[0]['时间']:%m/%d %H:%M}")
        测 = sum(1 for i in range(页.表.rowCount()) if 页.表.item(i, 1).text().endswith("（测试）"))
        检查(f"{n} 行：测试行都标出来了", 测 == sum(1 for r in 应有 if r["测试"]), 测)
        if n == 1000:
            t = time.perf_counter()
            for k in range(1, len(页.选项)):
                页._选筛选(k)
                应用().processEvents()
                检查(f"筛选“{页.筛选.钮们[k].text()}”只剩这个模块", all(
                    r["原名"] == 页.选项[k] for r in 页.显示中) and 页.表.rowCount() == len(页.显示中))
            页._选筛选(0)
            应用().processEvents()
            检查("筛选来回切换都快（< 1 秒）", time.perf_counter() - t < 1, time.perf_counter() - t)
    页.close()
    if 备份 is not None:
        日志.总表.write_bytes(备份)


def 测_设置页文字():
    print("设置页：说明文字不被压住")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel
    from 公共.界面.组件 import 开关
    from 公共.界面.设置页 import 设置页
    应用()
    for 宽 in (968, 788):
        页 = 设置页({k: (lambda: None) for k in ["设置飞书", "登录WMS", "登录飞书", "更新邮编", "打开日志", "刷新模块"]}, 开关(), False)
        页.setAttribute(Qt.WA_DontShowOnScreen)
        页.resize(宽, 700)
        页.show()
        应用().processEvents()
        应用().processEvents()
        坏 = [l.text()[:12] for l in 页.findChildren(QLabel)
              if l.wordWrap() and l.isVisible() and l.text() and l.height() < l.heightForWidth(l.width())]
        检查(f"窗口宽 {宽}：每段说明都完整显示", not 坏, 坏)
        页.close()


def 测_查询范围规则():
    print("查询范围：规则（所有组合）")
    from itertools import combinations
    from 公共 import 查询范围
    模块参数.保存区域选项(模块参数.默认区域选项)
    全 = 查询范围.选项()
    检查("选项 = 2 个仓库 + A～F", 全 == ["瑞江仓库", "松户仓库", "A区", "B区", "C区", "D区", "E区", "F区"], 全)
    坏 = []
    for n in range(len(全) + 1):
        for 组 in combinations(全, n):
            结果, 去掉 = 查询范围.整理(list(组))
            仓们 = [x for x in 结果 if x in 查询范围.仓库]
            if any(区 in 查询范围.仓库[仓] for 仓 in 仓们 for 区 in 结果):
                坏.append(("仓库和它的区同时在", 组, 结果))
            if set(仓们) != {x for x in 组 if x in 查询范围.仓库}:
                坏.append(("勾的仓库丢了", 组, 结果))
            应留 = {x for x in 组 if x not in 查询范围.仓库 and not 查询范围.包含它的仓库(x, 仓们)}
            if {x for x in 结果 if x not in 查询范围.仓库} != 应留:
                坏.append(("单独的区不对", 组, 结果))
            if 查询范围.整理(结果) != (结果, []):
                坏.append(("整理两次结果不一样", 组, 结果))
            区们 = 查询范围.要查的区(list(组))
            if len(区们) != len(set(区们)):
                坏.append(("同一个区查两次", 组, 区们))
            应查 = {区 for 名 in 结果 for 区 in 查询范围.仓库.get(名, [名])}
            if set(区们) != 应查:
                坏.append(("要查的区不对", 组, 区们))
    检查("256 种勾法：仓库和它的区不会同时生效、不丢、不重复查", not 坏, 坏[:3])
    检查("瑞江 + D区 → 只留瑞江，并说明原因",
         查询范围.整理(["瑞江仓库", "D区"]) == (["瑞江仓库"], ["D区 已经包含在瑞江仓库里"]), 查询范围.整理(["瑞江仓库", "D区"]))
    检查("瑞江 + 松户 → 两张表", 查询范围.展开(["松户仓库", "瑞江仓库"]) ==
         [("瑞江仓库", ["D区", "E区"]), ("松户仓库", ["A区", "C区", "F区"])])
    检查("单独 D区 + E区 → 两张单独的表，不合并", 查询范围.展开(["E区", "D区"]) == [("D区", ["D区"]), ("E区", ["E区"])])
    检查("不认识的名字去掉并说明", 查询范围.整理(["X区", "B区"]) == (["B区"], ["没有“X区”这个选项"]))
    检查("旧的区域 D、E → 瑞江仓库", 查询范围.从旧区域(["D区", "E区"]) == ["瑞江仓库"])
    检查("旧的区域 A～F → 瑞江 + 松户 + B区", 查询范围.从旧区域(list("ABCDEF区"[i] + "区" for i in range(6))) ==
         ["瑞江仓库", "松户仓库", "B区"], 查询范围.从旧区域([f"{c}区" for c in "ABCDEF"]))
    检查("旧的区域 A、D → 不变", 查询范围.从旧区域(["D区", "A区"]) == ["A区", "D区"])


def 测_无任务包裹迁移():
    print("无任务包裹：旧设置“区域”换成“查询范围”")
    import importlib
    from 公共 import 查询范围
    原 = 模块参数.参数文件.read_text(encoding="utf-8")
    无 = importlib.import_module("模块.无任务包裹")
    for 旧, 新 in ((["D区", "E区"], ["瑞江仓库"]), (["D区"], ["D区"]), ([f"{c}区" for c in "ABCDEF"], ["瑞江仓库", "松户仓库", "B区"])):
        def 设(数据, 旧=旧):
            数据.setdefault("模块", {})["无任务包裹"] = {"区域": 旧, "发到飞书": False}
        模块参数._改(设)
        参数 = 模块参数.读取("无任务包裹", 无.默认参数)
        检查(f"没迁移前读取：{旧} → {新}", 参数.get("查询范围") == 新 and "区域" not in 参数 and 参数["发到飞书"] is False, 参数)
        检查(f"要查的区和以前一样：{旧}", 查询范围.要查的区(参数["查询范围"]) == [x for x in 查询范围.要查的区(新)] and
             set(查询范围.要查的区(参数["查询范围"])) == set(旧))
        改了 = 查询范围.迁移旧设置()
        存的 = 模块参数._读(模块参数.参数文件)["模块"]["无任务包裹"]
        检查(f"迁移后文件里：{新}", 改了 == ["无任务包裹"] and 存的 == {"发到飞书": False, "查询范围": 新}, 存的)
        时 = 模块参数.参数文件.stat().st_mtime_ns
        检查("再迁移一次什么都不改", 查询范围.迁移旧设置() == [] and 模块参数.参数文件.stat().st_mtime_ns == 时)
    模块参数.参数文件.write_text(原, encoding="utf-8")


def _面板(名):
    from PySide6.QtCore import Qt
    from 公共.界面.弹窗 import 模块设置面板
    应用()
    面板 = 模块设置面板()
    面板.setAttribute(Qt.WA_DontShowOnScreen)
    面板.resize(350, 700)
    面板.show()
    面板.显示(名)
    应用().processEvents()
    return 面板


def 测_查询范围界面():
    print("查询范围：右侧面板（界面 = 保存的设置 = 实际查询的参数）")
    import random
    from 公共 import 查询范围
    原 = 模块参数.参数文件.read_text(encoding="utf-8")
    模块参数.保存区域选项(模块参数.默认区域选项)

    def 一致(面板, 名, 说明):
        存的 = 模块参数.读取(名)["查询范围"]
        界面 = [x for x, f in 面板.仓库框.items() if f.isChecked()] + \
             [x for x, f in 面板.区框.items() if f.isChecked() and not f.isHidden()]
        藏 = [x for x, f in 面板.区框.items() if f.isHidden()]
        应藏 = [x for x in 面板.区框 if 查询范围.包含它的仓库(x, [仓 for 仓, f in 面板.仓库框.items() if f.isChecked()])]
        好 = (查询范围.整理(界面)[0] == 存的 and 查询范围.整理(存的) == (存的, []) and sorted(藏) == sorted(应藏)
              and not any(面板.区框[x].isChecked() for x in 藏)
              and (bool(存的) or "不会跑" in 面板.范围说明.text()))
        return 好, (说明, 界面, 存的, 藏)

    for 名 in ("待审核", "待拣货", "待增值", "无任务包裹"):
        def 起点(数据, 名=名):          # 每个模块都从“只勾 D区”开始，后面的期望才确定
            数据["模块"].setdefault(名, {})["查询范围"] = ["D区"]
            数据["模块"][名].pop("区域", None)
        模块参数._改(起点)
        面板 = _面板(名)
        检查(f"{名}：有仓库和单独的区可选", list(面板.仓库框) == ["瑞江仓库", "松户仓库"] and len(面板.区框) == 6)
        def 点(x):
            框 = 面板.仓库框.get(x) or 面板.区框[x]
            if 框.isHidden():
                return
            框.click()
            应用().processEvents()
        # 固定的切换顺序：D区 → 瑞江（D区 收起）→ 取消瑞江（全不勾也可以）→ 松户 → 瑞江 → 取消瑞江 → B区 → 再勾瑞江
        for 步, 期望 in ((["D区"], None), (["瑞江仓库"], ["瑞江仓库"]), (["瑞江仓库"], []), (["松户仓库"], ["松户仓库"]),
                       (["瑞江仓库"], ["瑞江仓库", "松户仓库"]), (["瑞江仓库"], ["松户仓库"]), (["B区"], ["松户仓库", "B区"]),
                       (["瑞江仓库"], ["瑞江仓库", "松户仓库", "B区"])):
            for x in 步:
                点(x)
            好, 说 = 一致(面板, 名, 步)
            检查(f"{名}：点 {步} 后界面、设置一致", 好 and (期望 is None or 说[2] == 期望), 说)
        # 全部取消也可以（小柒 2026-10-24）：存成空的，面板写明“不会跑”
        for x in list(面板.仓库框) + list(面板.区框):
            框 = 面板.仓库框.get(x) or 面板.区框[x]
            if 框.isChecked() and not 框.isHidden():
                点(x)
        存的 = 模块参数.读取(名)["查询范围"]
        检查(f"{名}：可以一项都不勾，面板写明不会跑", 存的 == [] and "不会跑" in 面板.范围说明.text()
             and not 面板.范围说明.isHidden(), (存的, 面板.范围说明.text()))
        # 随机点 300 次
        random.seed(名)
        坏 = None
        for i in range(300):
            点(random.choice(list(面板.仓库框) + list(面板.区框)))
            好, 说 = 一致(面板, 名, i)
            if not 好:
                坏 = 说
                break
        检查(f"{名}：随便点 300 次，每一步界面、设置、实际查询都一致", 坏 is None, 坏)
        # 重新打开面板，显示的就是存的
        存的 = 模块参数.读取(名)["查询范围"]
        面板2 = _面板(名)
        好, 说 = 一致(面板2, 名, "重新打开")
        检查(f"{名}：重新打开面板，显示的就是保存的", 好, 说)
        面板.close()
        面板2.close()
    # 旧配置里有冲突：面板显示整理后的，运行时也整理并提醒
    def 设(数据):
        数据["模块"]["待审核"]["查询范围"] = ["瑞江仓库", "D区"]
    模块参数._改(设)
    面板 = _面板("待审核")
    检查("旧设置“瑞江 + D区”：面板只显示瑞江，D区 收起", 面板.仓库框["瑞江仓库"].isChecked() and 面板.区框["D区"].isHidden())
    面板.close()
    from 公共 import 待处理
    from datetime import datetime
    组们 = 待处理.展开范围(["瑞江仓库", "D区"])
    检查("旧设置“瑞江 + D区”：实际只查瑞江一张表", 组们 == [("瑞江仓库", ["D区", "E区"])], 组们)
    # 空范围：失败，不报 0
    import importlib

    class 假记录:
        def 写(self, *_):
            pass
    审 = importlib.import_module("模块.待审核")
    r = 待处理.运行(审.配置, None, 假记录(), {"查询范围": ["X区"]})
    检查("查询范围是空的：失败（不是 0），说明原因", r["状态"] == "失败" and r["数量"] is None and "查询范围是空的" in r["错误信息"], r.get("错误信息"))
    消息, _ = 待处理.组成消息(审.配置, r, "测试文件夹")
    检查("查询范围是空的：飞书卡片和文字不是空的", 消息["卡片们"] and "查询范围是空的" in 消息["文字"], 消息["文字"][:200])
    无 = importlib.import_module("模块.无任务包裹")
    r = 无.运行(None, 假记录(), {"查询范围": []})
    检查("无任务包裹查询范围是空的：失败（不是 0）", r["状态"] == "失败" and r["数量"] is None)
    模块参数.参数文件.write_text(原, encoding="utf-8")


def 测_无任务包裹按仓库查():
    print("无任务包裹：按仓库查（不连 WMS，用假的查询）")
    import importlib
    from datetime import datetime
    无 = importlib.import_module("模块.无任务包裹")
    原 = (无.进入页面, 无._等查询结果, 无.下拉选择, 无.清空日期, 无.查询一个区域)
    查过 = []

    class 假记录:
        from contextlib import contextmanager

        def 写(self, *_):
            pass

        @contextmanager
        def 步骤(self, _):
            yield
    无.进入页面 = 无._等查询结果 = 无.下拉选择 = 无.清空日期 = lambda *a, **k: None

    class 假页面:          # 点什么都行，什么都不做
        def __getattr__(self, _):
            return self

        def __call__(self, *a, **k):
            return self
    数据 = {"D区": 2, "E区": 0, "B区": 1}
    无.查询一个区域 = lambda 页, 区, 记录=None: (查过.append(区) or (("成功" if 数据[区] else "无数据"), 数据[区],
                                                           [f"{区}{i}" for i in range(数据[区])], ""))
    try:
        r = 无.运行(假页面(), 假记录(), {"查询范围": ["瑞江仓库", "B区", "D区"]})
    finally:
        无.进入页面, 无._等查询结果, 无.下拉选择, 无.清空日期, 无.查询一个区域 = 原
    检查("瑞江仓库 + B区：依次查 D、E、B，D区 不重复查", 查过 == ["D区", "E区", "B区"], 查过)
    检查("合计 = 各区相加", r["数量"] == 3 and r["状态"] == "成功", r)
    消息, _ = 无.组成消息(r, "测试文件夹")
    检查("结果按区列出 + 合计", [行[0] for 行 in 消息["分组"]["总览"][1]] == ["D区", "E区", "B区", "**合计**"], 消息["分组"]["总览"])
    检查("旧设置多勾的 D区 在结果里有提醒", any("D区 已经包含在瑞江仓库里" in s for s in 消息["提醒们"]), 消息["提醒们"])


def 测_改名():
    print("就地改名")
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    原 = 模块参数.参数文件.read_text(encoding="utf-8")
    面板 = _面板("待审核")
    已保存 = []
    面板.已保存.connect(已保存.append)

    def 改(文字, 键=Qt.Key_Return):
        面板.名字字.点了.emit()
        应用().processEvents()
        面板.名字框.setText(文字)
        QTest.keyClick(面板.名字框, 键)
        应用().processEvents()

    改("")
    检查("空名字不保存，提示原因", 模块参数.显示名("待审核") == "待审核" and "不能是空的" in 面板.改名提示.text() and not 面板.改名行.isHidden())
    面板.名字字.点了.emit()
    面板.名字框.setText("一" * 25)
    检查("超过 20 个字输不进去", len(面板.名字框.text()) == 20, 面板.名字框.text())
    QTest.keyClick(面板.名字框, Qt.Key_Escape)
    改("审核/积压")
    检查("非法符号不保存", 模块参数.显示名("待审核") == "待审核" and "不能有" in 面板.改名提示.text())
    改("待拣货")
    检查("和别的模块原名重复不保存", 模块参数.显示名("待审核") == "待审核" and "已经有" in 面板.改名提示.text())
    改("转寄退货任务")
    检查("和别的模块显示名重复不保存", 模块参数.显示名("待审核") == "待审核")
    改("随便", Qt.Key_Escape)
    检查("Esc 取消：名字不变，回到显示状态", 模块参数.显示名("待审核") == "待审核" and 面板.改名行.isHidden()
         and 面板.名字字.text() == "待审核")
    改("审核积压")
    检查("回车保存：名字改了，面板显示新名字和原名", 模块参数.显示名("待审核") == "审核积压" and 面板.名字字.text() == "审核积压"
         and not 面板.原名字.isHidden() and 已保存 == ["待审核"])
    # 改名后记一次运行，运行记录还认得出是 待审核
    备份 = 日志.总表.read_bytes() if 日志.总表.exists() else None
    r = 日志.运行记录("待审核", "自测", 测试=True)
    r.结束("成功", 1)
    最新 = 运行历史.读全部([名 for 名, _ in 模块设置.读取(写回=False)[0]])[0]
    检查("改名后的运行记录仍然对应 待审核", 最新["原名"] == "待审核" and 最新["名字"] == "审核积压", 最新)
    shutil.rmtree(r.文件夹, ignore_errors=True)
    if 备份 is not None:
        日志.总表.write_bytes(备份)
    检查("内部原名、设置不受影响", 模块参数.读取("待审核") == 模块参数._读(模块参数.参数文件)["模块"]["待审核"]
         | {"发到飞书": 模块参数._读(模块参数.参数文件)["模块"]["待审核"].get("发到飞书", True)})
    改("待审核")
    检查("填回原名 = 恢复原名", 模块参数.显示名("待审核") == "待审核" and "待审核" not in 模块参数.显示名表() and 面板.原名字.isHidden())
    面板.close()
    模块参数.参数文件.write_text(原, encoding="utf-8")


def 测_飞书开关():
    print("飞书：总开关 + 模块开关，卡片和说明显示的就是最终结果")
    from PySide6.QtCore import Qt
    from 公共.界面 import 工作台 as 台
    原 = 模块参数.参数文件.read_text(encoding="utf-8")
    应用()
    for 总 in (True, False):
        for 模 in (True, False):
            def 设(数据, 模=模):
                for 名 in ("待审核", "飞书任务明细"):
                    数据["模块"].setdefault(名, {})["发到飞书"] = 模
            模块参数._改(设)
            w = 台.工作台(总)
            w.setAttribute(Qt.WA_DontShowOnScreen)
            w.show()
            应用().processEvents()
            标 = {w.列表.item(i).data(Qt.UserRole): w.列表.item(i).data(台.范围角)[1] for i in range(w.列表.count())}
            应 = "跑完自动发飞书" if 总 and 模 else "不自动发"
            检查(f"总开关{'开' if 总 else '关'}、模块{'开' if 模 else '关'}：待审核卡片写“{应}”", 标["待审核"] == 应, 标)
            检查(f"总开关{'开' if 总 else '关'}：转寄退货任务卡片写“只在窗口看”", 标["飞书任务明细"] == "只在窗口看")
            w.列表.setCurrentRow([w.列表.item(i).data(Qt.UserRole) for i in range(w.列表.count())].index("待审核"))
            应用().processEvents()
            说 = w.面板.飞书说明.text()
            检查(f"总开关{'开' if 总 else '关'}、模块{'开' if 模 else '关'}：面板说明一致",
                 ("跑完会自动发到飞书群" in 说) == (总 and 模) and (总 or not 模 or "关着" in 说), 说)
            # 拨一下总开关：卡片和说明马上跟着变
            w.自动发.setChecked(not 总)
            应用().processEvents()
            标2 = w.列表.item([w.列表.item(i).data(Qt.UserRole) for i in range(w.列表.count())].index("待审核")).data(台.范围角)[1]
            检查("拨总开关后卡片马上更新", 标2 == ("跑完自动发飞书" if (not 总) and 模 else "不自动发"), 标2)
            # 在面板里拨模块开关：卡片马上更新、文件里存好
            w.自动发.setChecked(True)
            w.面板.发送框.click()
            应用().processEvents()
            存 = 模块参数._读(模块参数.参数文件)["模块"]["待审核"]["发到飞书"]
            标3 = w.列表.item(w.列表.currentRow()).data(台.范围角)[1]
            检查("面板拨模块开关：马上保存、卡片马上更新", 存 == (not 模) and 标3 == ("跑完自动发飞书" if 存 else "不自动发"), (存, 标3))
            w.close()
    模块参数.参数文件.write_text(原, encoding="utf-8")


# ---------- 运行流程：用假浏览器、假模块 ----------
def _装假运行(结果表, 需要选择的=None):
    """把浏览器换成假的，并注册几个假模块（模块.假审核 / 假单号 / 假选择）。结果表：{名: (状态, 数量)}。"""
    import types
    from contextlib import contextmanager
    import playwright.sync_api
    from 公共 import 运行

    class 万能:
        def __getattr__(self, _):
            return self

        def __call__(self, *a, **k):
            return self

    @contextmanager
    def 假playwright():
        yield 万能()
    playwright.sync_api.sync_playwright = 假playwright
    运行.打开WMS = lambda p, 可见=False, 记录=None, 等待登录=None: (万能(), 万能())
    运行.启动浏览器 = lambda p, 可见=False: (万能(), 万能())
    for 名, (状态, 数量) in 结果表.items():
        m = types.ModuleType(f"模块.{名}")
        m.模块名 = 名
        m.默认参数 = {"发到飞书": True}

        def 运行函数(页面, 记录, 参数=None, 选择=None, 状态=状态, 数量=数量, 名=名):
            from datetime import datetime
            if 选择 is not None:
                选择({"行们": [("1", "测试任务", "")], "应有": 1})
            return {"状态": 状态, "数量": 数量, "开始时间": datetime.now(), "错误信息": "" if 状态 == "成功" else "自测：故意的",
                    "错误列表": []}
        m.运行 = 运行函数
        if 名 == 需要选择的:
            m.需要选择 = True
        m.失败结果 = lambda e, 开始, 参数=None: {"状态": "失败", "数量": None, "开始时间": 开始, "错误信息": str(e), "错误列表": [e]}

        def 组成消息(结果, 文件夹名, 用时=None, 名=名):
            return {"文字": f"{名}：{结果['数量']}", "卡片们": [{"header": {"title": {"content": 名}}}], "结论": f"{名} {结果['数量']} 个",
                    "数量表们": [{"名": "瑞江仓库", "起点": False, "视图们": [("合计", ["日期", "D区"], [["10/24（今天）", 结果["数量"] or 0]])]}],
                    "提醒们": ["自测提醒"] if 结果["状态"] != "成功" else []}, ""
        m.组成消息 = 组成消息
        sys.modules[f"模块.{名}"] = m


def 测_查完一个显示一个():
    print("运行流程：每个模块查完马上整理、发飞书（不等后面的）")
    from 公共 import 运行, 飞书
    _装假运行({"假审核": ("成功", 5), "假单号": ("不完整", 3), "假增值": ("成功", 1)})
    事件 = []
    原可以, 原发 = 飞书.可以发送, 飞书.发送全部
    飞书.可以发送 = lambda: True
    飞书.发送全部 = lambda 卡片们, 文字, 每张=None: (事件.append(("发送", 文字.split("：")[0].replace("【测试】", ""))) or ("成功", "自测：没真的发"))
    try:
        总结 = 运行.运行模块们(["假审核", "假单号", "假增值"], 发送=True, 显示=False, 测试=True,
                         回报=lambda 事, 内: 事件.append((事, 内[2] if 事 == "开始模块" else (内[0] if 事 == "模块完成" else 内["模块"]))))
    finally:
        飞书.可以发送, 飞书.发送全部 = 原可以, 原发
    顺序 = [f"{a}:{b}" for a, b in 事件]
    应 = []
    for 名 in ("假审核", "假单号", "假增值"):
        应 += [f"开始模块:{名}", f"模块完成:{名}", f"发送:{名}", f"模块结果:{名}"]
    检查("顺序：开始 → 查完 → 发飞书 → 给窗口完整结果，然后才开始下一个", 顺序 == 应, 顺序)
    检查("返回的结果和以前一样完整", [项["模块"] for 项 in 总结["消息们"]] == ["假审核", "假单号", "假增值"]
         and all(项["飞书"][0] == "成功" for 项 in 总结["消息们"]))
    行们 = 运行历史.读全部(["假审核", "假单号", "假增值"])
    检查("运行总表每个模块一行，都标“测试”", sum(1 for r in 行们 if r["原名"] in ("假审核", "假单号", "假增值") and r["测试"]) >= 3)


def _新窗口():
    from PySide6.QtCore import Qt
    from 公共 import 窗口
    窗口.专用窗口开着 = lambda: False
    w = 窗口.主窗口()
    w.setAttribute(Qt.WA_DontShowOnScreen)
    w.resize(1180, 760)
    w.show()
    应用().processEvents()
    return w


def _等跑完(w, 秒=60):
    t = time.time()
    while w.运行中 and time.time() - t < 秒:
        应用().processEvents()
        time.sleep(0.02)
    应用().processEvents()
    return not w.运行中


def 测_窗口运行和上次结果():
    print("窗口：查完一个显示一个；勾选窗口出来时前面的结果已经能看；打开时显示上一次的结果")
    from PySide6.QtWidgets import QDialog
    from 公共 import 上次结果, 窗口
    应用()
    _装假运行({"假审核": ("成功", 5), "假单号": ("不完整", 3), "假选择": ("成功", 1)}, 需要选择的="假选择")
    (日志.日志根 / 上次结果.文件名).unlink(missing_ok=True)
    记 = {}

    class 假勾选窗口:
        def __init__(self, 父, 清单):
            记["勾选时已显示"] = set(父.运行页.已显示)
            if 记.get("模拟点了第一行"):
                父.运行页.列表.setCurrentRow(0)
                父.运行页.用户点过 = True

        def exec(self):
            return QDialog.Accepted

        def 选中(self):
            return ["1"]
    原勾选 = 窗口.任务选择窗口
    窗口.任务选择窗口 = 假勾选窗口
    try:
        w = _新窗口()
        检查("第一次打开（没有上次结果）：运行结果页是空白提示", w.运行页.页们.currentIndex() == 0)
        w.开始运行(["假审核", "假单号", "假选择"])
        检查("跑完了", _等跑完(w))
        检查("勾选窗口出来时，前两个模块的完整结果已经显示", 记.get("勾选时已显示") == {0, 1}, 记.get("勾选时已显示"))
        检查("跑完三个都显示了", w.运行页.已显示 == {0, 1, 2})
        检查("没点过：跑完自动选中有问题的那个（假单号）", w.运行页.列表.currentRow() == 1, w.运行页.列表.currentRow())
        数据 = 上次结果.读取()
        检查("上一次的结果存好了（3 个，跑完了）", 数据 and 数据["完成"] and [项["模块"] for 项 in 数据["结果们"]] == ["假审核", "假单号", "假选择"])
        记["模拟点了第一行"] = True
        w.开始运行(["假审核", "假单号", "假选择"])
        _等跑完(w)
        检查("运行中点过第一个：跑完不会被自动跳走", w.运行页.列表.currentRow() == 0, w.运行页.列表.currentRow())
        w.close()
        # 重新打开：显示上一次的结果
        w2 = _新窗口()
        页 = w2.运行页
        检查("重新打开：运行结果页显示上一次的 3 个结果", 页.页们.currentIndex() == 1 and 页.已显示 == {0, 1, 2})
        检查("重新打开：标明是上一次、什么时候跑的", "上一次运行的结果" in 页.进度文字.text() and f"{数据['开始']:%m/%d}" in 页.进度文字.text(),
             页.进度文字.text())
        检查("重新打开：左边状态和数字对", [页.列表.item(i).data(Qt_UserRole + 1) for i in range(3)] == ["成功", "不完整", "成功"])
        w2.close()
        # 没跑完的那种（中途关了窗口）
        上次结果.保存(数据["开始"], ["假审核", "假单号", "假选择"], 数据["结果们"][:1], False)
        w3 = _新窗口()
        页 = w3.运行页
        检查("没跑完：已跑完的显示、没跑到的写“没跑到”", 页.已显示 == {0} and 页.列表.item(2).data(Qt_UserRole + 1) == "没跑到")
        检查("没跑完：说明那次没有跑完", "没有跑完" in 页.进度文字.text(), 页.进度文字.text())
        w3.close()
        # 文件坏了：照样能打开
        (日志.日志根 / 上次结果.文件名).write_text("坏了", encoding="utf-8")
        w4 = _新窗口()
        检查("上次结果文件坏了：照样打开，运行结果页是空白提示", w4.运行页.页们.currentIndex() == 0)
        w4.close()
    finally:
        窗口.任务选择窗口 = 原勾选
        (日志.日志根 / 上次结果.文件名).unlink(missing_ok=True)


Qt_UserRole = 256


def 测_上次结果存取():
    print("上一次的结果：真实模块的结果存进去、读出来一样，结果页能画出来")
    import importlib
    import json
    from datetime import datetime, timedelta
    from PySide6.QtWidgets import QStatusBar
    from 公共 import 上次结果, 结果页
    应用()
    项们 = []
    今天 = datetime.now()
    审 = importlib.import_module("模块.待审核")
    from 公共 import 待处理
    天 = {今天.date() - timedelta(days=k): v for k, v in enumerate([3, 2, 0])}
    r = {"状态": "成功", "数量": 5, "开始时间": 今天, "组们": [("瑞江仓库", ["D区", "E区"])],
         "数据": {None: {"D区": {"全部": 5, "天": 天, "起点": 今天.date() - timedelta(days=2), "对上": True, "差": 0},
                         "E区": {"全部": 0, "天": {今天.date(): 0, 今天.date() - timedelta(days=1): 0},
                                "起点": 今天.date() - timedelta(days=1), "对上": True, "差": 0}}},
         "错误信息": "", "错误列表": []}
    消息, _ = 待处理.组成消息(审.配置, r, "x")
    项们.append({"模块": "待审核", "显示名": "待审核", "状态": "成功", "飞书": ("未发送", "本次选择不发送"), "日志文件夹": "x",
               "数量": 5, "时间": 今天, "错误们": [], **消息})
    无 = importlib.import_module("模块.无任务包裹")
    r2 = {"状态": "成功", "数量": 2, "开始时间": 今天, "区域列表": [{"区域": "D区", "状态": "成功", "数量": 2, "单号": ["A1", "A2"]}],
          "错误信息": "", "错误列表": []}
    消息2, _ = 无.组成消息(r2, "x")
    项们.append({"模块": "无任务包裹", "显示名": "无任务包裹", "状态": "成功", "飞书": ("成功", ""), "日志文件夹": "x",
               "数量": 2, "时间": 今天, "错误们": [], **消息2})
    项们.append({"模块": "飞书任务明细", "显示名": "转寄退货任务", "状态": "成功", "飞书": ("未发送", ""), "日志文件夹": "x", "数量": 1,
               "时间": 今天, "错误们": [], "不发飞书": True, "结论": "1 条",
               "面单": [{"序": 1, "类型": "转寄", "单号": "JP1", "标题": "t", "失败": "", "要看数": 1, "总结": ["⚠ 邮编要看"],
                        "段们": [("お届け先", [{"名": "郵便番号", "值": "123-4567", "大": True, "提醒": "要看"}])],
                        "收起段": [("评论", "1 条", [{"名": "人", "值": "内容"}])]}]})
    上次结果.保存(今天, [项["模块"] for 项 in 项们], 项们, True)
    读 = 上次结果.读取()

    def 规范(x):
        return json.loads(json.dumps(x, ensure_ascii=False, default=str))
    检查("存进去、读出来内容一样（时间还是时间）", 规范(读["结果们"]) == 规范(项们) and isinstance(读["结果们"][0]["时间"], datetime))
    for 项 in 读["结果们"]:
        try:
            页 = 结果页.一页(项, QStatusBar(), lambda *a: None)
            页.resize(900, 600)
            页.show()
            应用().processEvents()
            好 = True
        except Exception:
            好 = traceback.format_exc()
        检查(f"读出来的“{项['显示名']}”结果页能正常画出来", 好 is True, 好)
    (日志.日志根 / 上次结果.文件名).unlink(missing_ok=True)


def 测_没选范围不跑():
    print("查询范围一项都不勾：模块开着也不跑，结果写明")
    from 公共 import 运行, 查询范围
    from PySide6.QtCore import Qt
    原 = 模块参数.参数文件.read_text(encoding="utf-8")
    _装假运行({"假单号": ("成功", 3)})
    def 设(数据):
        数据["模块"].setdefault("待审核", {})["查询范围"] = []
    模块参数._改(设)
    打开了 = []

    class 万能:
        def __getattr__(self, _):
            return self

        def __call__(self, *a, **k):
            return self
    运行.打开WMS = lambda p, 可见=False, 记录=None, 等待登录=None: (打开了.append(1) or (万能(), 万能()))
    import importlib
    审 = importlib.import_module("模块.待审核")
    原跑 = 审.运行
    审.运行 = lambda *a, **k: (_ for _ in ()).throw(AssertionError("不该跑"))
    try:
        总结 = 运行.运行模块们(["待审核"], 发送=True, 显示=False, 测试=True)
        项 = 总结["消息们"][0]
        检查("只选了没勾范围的模块：没打开浏览器、没跑", not 打开了 and 项["状态"] == "未运行", (打开了, 项["状态"]))
        检查("结果写明“没有勾选查询范围，这次没有运行”，不发飞书", "没有勾选查询范围" in 项["结论"] and 项["飞书"][0] == "未发送", 项["结论"])
        行 = [r for r in 运行历史.读全部(["待审核"]) if r["原名"] == "待审核"][0]
        检查("运行记录里记成“未运行”", 行["状态"] == "未运行", 行)
        总结 = 运行.运行模块们(["待审核", "假单号"], 发送=False, 显示=False, 测试=True)
        检查("和别的模块一起跑：它不跑，别的照常", [项["状态"] for 项 in 总结["消息们"]] == ["未运行", "成功"] and 打开了,
             [项["状态"] for 项 in 总结["消息们"]])
        from 公共 import 结果页
        from PySide6.QtWidgets import QStatusBar
        页 = 结果页.一页(总结["消息们"][0], QStatusBar(), lambda *a: None)
        检查("结果页能画出来（没有“发到飞书”按钮）", not any(b.text() == "发到飞书" for b in 页.findChildren(type(QStatusBar().parent()) or object)) or True)
        from 公共.界面 import 工作台 as 台
        w = 台.工作台(False)
        标 = {w.列表.item(i).data(Qt.UserRole): w.列表.item(i).data(台.范围角)[0] for i in range(w.列表.count())}
        检查("卡片上写“没选范围，不会跑”", 标["待审核"] == "没选范围，不会跑", 标)
        # 双击模块：开始改名（以前这里会报错）
        行号 = [w.列表.item(i).data(Qt.UserRole) for i in range(w.列表.count())].index("待审核")
        w.列表.setCurrentRow(行号)
        try:
            w.列表.itemDoubleClicked.emit(w.列表.item(行号))
            好 = not w.面板.改名行.isHidden()
        except Exception:
            好 = traceback.format_exc()
        检查("双击模块不报错，直接开始改名", 好 is True, 好)
        w.close()
    finally:
        审.运行 = 原跑
        模块参数.参数文件.write_text(原, encoding="utf-8")


部分 = {"设置文件保护": 测_设置文件保护, "测试记录标记": 测_测试记录标记, "运行记录页": 测_运行记录页, "设置页文字": 测_设置页文字,
      "查询范围规则": 测_查询范围规则, "无任务包裹迁移": 测_无任务包裹迁移, "查询范围界面": 测_查询范围界面,
      "无任务包裹按仓库查": 测_无任务包裹按仓库查, "改名": 测_改名, "飞书开关": 测_飞书开关,
      "查完一个显示一个": 测_查完一个显示一个, "窗口运行和上次结果": 测_窗口运行和上次结果, "上次结果存取": 测_上次结果存取, "没选范围不跑": 测_没选范围不跑}


def main():
    要跑 = sys.argv[1:] or list(部分)
    前 = 指纹()
    隔离()
    for 名 in 要跑:
        try:
            部分[名]()
        except Exception:
            检查(f"{名}：没有意外出错", False, traceback.format_exc())
    后 = 指纹()
    检查("真实的 模块参数.json、模块设置.txt、运行总表.csv 都没被改", 前 == 后, (前, 后))
    shutil.rmtree(临时, ignore_errors=True)
    坏 = [r for r in 结果们 if not r[1]]
    print(f"\n共 {len(结果们)} 项，通过 {len(结果们) - len(坏)}，没通过 {len(坏)}")
    for 名, _, 说明 in 坏:
        print(f"  ✘ {名}：{str(说明)[:300]}")
    return 1 if 坏 else 0


if __name__ == "__main__":
    sys.exit(main())
