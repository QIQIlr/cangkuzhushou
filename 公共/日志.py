# 职责：每次运行的日志。所有模块共用。
# 每次运行在 日志\ 下建一个文件夹：YYYY-MM-DD_HHMMSS_模块名\
#   运行记录.txt   中文逐步记录 + 结尾结论
#   截图.png / 网页快照.html / 技术详情.txt   只在出错时保存，给 AI 定位问题用
#   发送内容.txt   飞书消息原文和发送结果
# 另有 日志\运行总表.csv：每次运行一行（Excel 可直接打开）。
# 安全：写入前会把 Webhook 地址、cookie、token 之类的内容遮掉。日志保留 90 天。
import csv
import platform
import re
import shutil
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from 公共.错误 import 归类

根目录 = Path(__file__).resolve().parent.parent
日志根 = 根目录 / "日志"
总表 = 日志根 / "运行总表.csv"
保留天数 = 90

_敏感 = [
    (re.compile(r"https://open\.(feishu\.cn|larksuite\.com)/open-apis/bot/v2/hook/[\w-]+"), "[飞书Webhook已隐藏]"),
    (re.compile(r"(?i)(cookie|token|authorization|password|密码)(\s*[:=]\s*)\S+"), r"\1\2[已隐藏]"),
]


def 遮掩(文字):
    for 规则, 替换 in _敏感:
        文字 = 规则.sub(替换, 文字)
    return 文字


class 运行记录:
    def __init__(self, 模块名, 运行方式=""):
        self.模块名 = 模块名
        self.开始 = time.time()
        self.文件夹名 = f"{datetime.now():%Y-%m-%d_%H%M%S}_{模块名}"
        self.文件夹 = 日志根 / self.文件夹名
        self.文件夹.mkdir(parents=True, exist_ok=True)
        self.页面 = None        # 打开浏览器后由模块设置，出错时用来截图
        self.第几步 = 0
        self.出错过 = []         # 本次所有错误（自动化错误）
        _清理旧日志()
        self.写(f"模块：{模块名}")
        self.写(f"开始时间：{datetime.now():%Y-%m-%d %H:%M:%S}")
        if 运行方式:
            self.写(f"运行方式：{运行方式}")
        self.写("-" * 40)

    观察者 = None   # 窗口版设置一个函数，用来实时显示每一步

    def 写(self, 文字):
        行 = f"[{datetime.now():%H:%M:%S}] {遮掩(str(文字))}"
        if 运行记录.观察者:
            try:
                运行记录.观察者(self.模块名, 遮掩(str(文字)))
            except Exception:
                pass
        with open(self.文件夹 / "运行记录.txt", "a", encoding="utf-8") as f:
            f.write(行 + "\n")

    @contextmanager
    def 步骤(self, 名称):
        """用法：with 记录.步骤("点击已挂起"): ……
        成功记一行；失败时记录原因、保存现场，再把错误（已归类）抛给上层。"""
        self.第几步 += 1
        编号 = f"第{self.第几步}步"
        self.写(f"{编号} {名称} ……")
        t = time.time()
        try:
            yield
        except Exception as 原始:
            错误 = 归类(原始)
            if not 错误.步骤:
                错误.步骤 = f"{编号} {名称}"
                self.写(f"    ✘ 失败（{time.time() - t:.1f} 秒）{错误.类型}：{错误.原因}")
                self.保存现场(原始)
                self.出错过.append(错误)
            if 错误 is 原始:
                raise
            raise 错误 from 原始
        else:
            self.写(f"    ✔ 完成（{time.time() - t:.1f} 秒）")

    def 保存现场(self, 原始异常):
        """出错时保存：截图、网页快照、技术详情。每个文件单独保护，某个存不了不影响其他。"""
        后缀 = "" if not (self.文件夹 / "截图.png").exists() else f"_{self.第几步}"
        网址 = ""
        if self.页面 is not None:
            try:
                网址 = self.页面.url
                self.页面.screenshot(path=str(self.文件夹 / f"截图{后缀}.png"), full_page=True)
            except Exception:
                pass
            try:
                (self.文件夹 / f"网页快照{后缀}.html").write_text(遮掩(self.页面.content()), encoding="utf-8")
            except Exception:
                pass
        try:
            from importlib.metadata import version
            pw版本 = version("playwright")
        except Exception:
            pw版本 = "未知"
        浏览器版本 = "未知"
        if self.页面 is not None:
            try:
                浏览器版本 = self.页面.evaluate("navigator.userAgent")
            except Exception:
                pass
        详情 = [
            f"模块：{self.模块名}",
            f"出错步骤：第{self.第几步}步",
            f"时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
            f"页面网址：{网址 or '（还没打开页面）'}",
            f"Python：{sys.version.split()[0]}   Playwright：{pw版本}   系统：{platform.platform()}",
            f"浏览器：{浏览器版本}",
            "",
            "Python 报错原文：",
            "".join(traceback.format_exception(type(原始异常), 原始异常, 原始异常.__traceback__)),
        ]
        with open(self.文件夹 / f"技术详情{后缀}.txt", "w", encoding="utf-8") as f:
            f.write(遮掩("\n".join(详情)))

    def 保存发送内容(self, 消息, 发送结果):
        with open(self.文件夹 / "发送内容.txt", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%H:%M:%S}] 发送结果：{遮掩(发送结果)}\n消息原文：\n{遮掩(消息)}\n\n")

    def 结束(self, 状态, 数量=None, 错误摘要=""):
        用时 = time.time() - self.开始
        self.写("-" * 40)
        结论 = f"结论：{状态}" + (f"，数量 {数量}" if 数量 is not None else "") + f"，用时 {用时:.0f} 秒"
        if 错误摘要:
            结论 += f"。问题：{错误摘要}"
        self.写(结论)
        新文件 = not 总表.exists()
        with open(总表, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            if 新文件:
                w.writerow(["时间", "模块", "状态", "数量", "用时(秒)", "错误摘要", "日志文件夹"])
            w.writerow([f"{datetime.now():%Y-%m-%d %H:%M:%S}", self.模块名, 状态,
                        "" if 数量 is None else 数量, f"{用时:.0f}", 遮掩(错误摘要), self.文件夹名])
        return 用时


def _清理旧日志():
    """删除 90 天以前的运行文件夹（只删名字以日期开头的文件夹）。"""
    界限 = datetime.now() - timedelta(days=保留天数)
    if not 日志根.exists():
        return
    for 夹 in 日志根.iterdir():
        if 夹.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}_\d{6}_", 夹.name):
            try:
                if datetime.strptime(夹.name[:10], "%Y-%m-%d") < 界限:
                    shutil.rmtree(夹, ignore_errors=True)
            except ValueError:
                pass
