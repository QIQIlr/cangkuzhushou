# 职责：每次运行的日志。所有模块共用。
# 每次运行在 日志\ 下建一个文件夹：YYYY-MM-DD_HHMMSS_模块名\（用窗口里改过的名字；改过名时运行记录里另记原名）
#   运行记录.txt   中文逐步记录 + 结尾结论
#   截图.png / 网页快照.html / 技术详情.txt   只在出错时保存，给 AI 定位问题用（网页快照只在“任务管理”这类只有数字的页面存）
#   发送内容.txt   飞书消息原文和发送结果
# 另有 日志\运行总表.csv：每次运行一行（Excel 可直接打开）。最后一列“测试”= Claude 自测的运行（2026-10-24 起才有这一列）。
# 安全：写入前会把 Webhook 地址、cookie、token、转运单号、电话号码之类的内容遮掉。日志保留 90 天。
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

from 公共.错误 import WMS提示错误, 归类, 技术原文, 立刻停下, 自动化错误

根目录 = Path(__file__).resolve().parent.parent
日志根 = 根目录 / "日志"
总表 = 日志根 / "运行总表.csv"
保留天数 = 90

_敏感 = [
    (re.compile(r"https://open\.(feishu\.cn|larksuite\.com)/open-apis/bot/v2/hook/[\w-]+"), "[飞书Webhook已隐藏]"),
    (re.compile(r"(?i)(cookie|token|authorization|password|密码)(\s*[:=]\s*)\S+"), r"\1\2[已隐藏]"),
    # 2026-10-29：转运单号（例如 261012-001766，只留前面的日期部分）、电话号码（日本、中国）
    (re.compile(r"(?<![\d-])(\d{6})-\d{5,6}(?![\d-])"), r"\1-******"),
    (re.compile(r"(?<![\d-])0\d{1,4}-\d{1,4}-\d{3,4}(?![\d-])"), "[电话已隐藏]"),
    (re.compile(r"\+81[\d\- ]{9,13}\d"), "[电话已隐藏]"),
    (re.compile(r"(?<!\d)(0[5789]0\d{8}|1[3-9]\d{9})(?!\d)"), "[电话已隐藏]"),
]

# 出错时只有这些页面才存“网页快照”（整页网页）：只有数字、没有客户信息（2026-10-29）。
# 包裹列表、转寄 / 飞书等可能有客户姓名、地址、电话的页面只存截图。
可存快照的网址 = ("/data-management/taskManager",)


def 可以存快照(网址):
    return any(x in (网址 or "") for x in 可存快照的网址)


def 遮掩(文字):
    for 规则, 替换 in _敏感:
        文字 = 规则.sub(替换, 文字)
    return 文字


class 运行记录:
    def __init__(self, 模块名, 运行方式="", 测试=False):
        from 公共.模块参数 import 显示名
        self.测试 = 测试                           # Claude 自测时为 True：运行总表里这一行标“测试”，工作台不算它
        self.模块名 = 模块名                       # 原名（固定）
        self.显示名 = 显示名(模块名)               # 窗口里改过的名字；没改过就是原名
        self.开始 = time.time()
        self.文件夹名 = f"{datetime.now():%Y-%m-%d_%H%M%S}_{self.显示名}"
        self.文件夹 = 日志根 / self.文件夹名
        self.文件夹.mkdir(parents=True, exist_ok=True)
        self.页面 = None        # 打开浏览器后由模块设置，出错时用来截图
        self.第几步 = 0
        self.出错过 = []         # 本次所有错误（自动化错误）
        _清理旧日志()
        self.写(f"模块：{self.显示名}" + (f"（原名：{模块名}）" if self.显示名 != 模块名 else ""))
        self.写(f"开始时间：{datetime.now():%Y-%m-%d %H:%M:%S}")
        if 运行方式:
            self.写(f"运行方式：{运行方式}")
        self.写("-" * 40)

    观察者 = None   # 窗口版设置一个函数，用来实时显示每一步
    正在 = None     # 正在跑的模块的记录（公共\运行.py 设）；运行中关窗口时给它补一行“被中止”
    本次主控 = None  # 一次跑多个模块时的“主控”记录

    def 中止(self, 原因):
        """运行中关窗口：在运行记录和运行总表里补一行“被中止”（已经写过结论的不再写）。"""
        if getattr(self, "已结束", False):
            return
        self.写(f"被中止：{原因}")
        self.结束("被中止", None, f"被中止（{原因}）")

    def 写(self, 文字):
        行 = f"[{datetime.now():%H:%M:%S}] {遮掩(str(文字))}"
        if 运行记录.观察者:
            try:
                运行记录.观察者(self.显示名, 遮掩(str(文字)))
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
            if not 错误.步骤 and 错误.类型 not in 立刻停下:
                # 体检 2026-10-28：WMS 弹出“账号已在其他地方登录!”之类的提示框挡住页面时，照原文报出、立刻停下
                提示 = self._WMS提示()
                if 提示:
                    错误 = WMS提示错误(提示)
            if not 错误.步骤:
                错误.步骤 = f"{编号} {名称}"
                self.写(f"    ✘ 失败（{time.time() - t:.1f} 秒）{错误.类型}：{错误.原因}")
                源 = 原始 if not isinstance(原始, 自动化错误) else (原始.__cause__ or 原始.__context__)
                if 源 is not None:       # 英文技术原文只放日志，界面上只写中文（体检 2026-10-28）
                    self.写(f"    技术原文：{技术原文(源)}")
                self.保存现场(原始)
                self.出错过.append(错误)
            if 错误 is 原始:
                raise
            raise 错误 from 原始
        else:
            self.写(f"    ✔ 完成（{time.time() - t:.1f} 秒）")

    def _WMS提示(self):
        if self.页面 is None:
            return ""
        try:
            from 公共.wms import 读系统提示
            字 = 读系统提示(self.页面)
            return 字 if isinstance(字, str) else ""
        except Exception:
            return ""

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
            if 可以存快照(网址):
                try:
                    (self.文件夹 / f"网页快照{后缀}.html").write_text(遮掩(self.页面.content()), encoding="utf-8")
                except Exception:
                    pass
            else:
                self.写("    （这一页可能有客户信息，只存截图、不存网页快照）")
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
        self.已结束 = True
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
                w.writerow(["时间", "模块", "状态", "数量", "用时(秒)", "错误摘要", "日志文件夹", "测试"])
            名 = self.显示名 + (f"（{self.模块名}）" if self.显示名 != self.模块名 else "")
            w.writerow([f"{datetime.now():%Y-%m-%d %H:%M:%S}", 名, 状态,
                        "" if 数量 is None else 数量, f"{用时:.0f}", 遮掩(错误摘要), self.文件夹名,
                        "测试" if self.测试 else ""])
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
