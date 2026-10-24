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


部分 = {"设置文件保护": 测_设置文件保护, "测试记录标记": 测_测试记录标记, "运行记录页": 测_运行记录页, "设置页文字": 测_设置页文字}


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
