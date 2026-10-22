# 职责：仓库助手菜单（双击 仓库助手.bat 打开）。
# 菜单：运行全部已启用模块 / 只运行一个 / 临时自选几个 / 调整顺序和开关 / 设置消息格式 / 设置飞书 / 登录 WMS
# 运行时：WMS 只打开一次，模块按顺序跑，一个失败不影响下一个，最后发一条飞书汇总。
import os
import re
import subprocess
import sys
from pathlib import Path

根目录 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(根目录))
from 公共 import 模块设置  # noqa: E402
from 公共.wms import WMS首页, 专用配置目录  # noqa: E402

PY = sys.executable
_原输入 = input


def input(提示=""):   # 去掉粘贴或管道带进来的看不见的字符
    return _原输入(提示).replace("\ufeff", "")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def 显示清单(清单):
    if not 清单:
        print("  （还没有模块）")
    for i, (名, 开) in enumerate(清单, 1):
        print(f"  {i}. {'✔ 启用' if 开 else '✖ 禁用'}  {名}")


def 解析编号(文字, 上限):
    编号 = [int(x) for x in re.split(r"[\s,，、]+", 文字.strip()) if x.isdigit()]
    if not 编号 or any(n < 1 or n > 上限 for n in 编号):
        return None
    return list(dict.fromkeys(编号))   # 去重，保留输入顺序


def 运行(名列表):
    if not 名列表:
        print("\n没有要运行的模块。")
        return
    print(f"\n将按顺序运行：{' → '.join(名列表)}")
    from 公共.运行 import 运行模块们
    try:
        # 环境变量 仓库助手_测试不发送=1 时不发飞书（只在测试时用）
        运行模块们(名列表, 发送=os.environ.get("仓库助手_测试不发送") != "1")
    except Exception as e:
        print(f"\n✘ 运行时出现意外错误：{type(e).__name__}: {e}")
        print("  请把这段文字发给 Claude。")


def 调整顺序(清单):
    while True:
        print("\n========== 调整模块顺序和开关 ==========")
        显示清单(清单)
        print("\n输入：关 2（禁用第2个）  开 2（启用）  2 上移  2 下移")
        print("      记事本（直接改设置文件）  直接按回车 = 返回主菜单")
        指令 = input("> ").strip().replace("　", " ")
        if not 指令:
            return 清单
        if 指令 == "记事本":
            subprocess.run(["notepad.exe", str(模块设置.设置文件)])
            清单, 提醒 = 模块设置.读取()
            print(f"\n⚠ {提醒}" if 提醒 else "\n✔ 已读取新设置。")
            continue
        m1 = re.fullmatch(r"(开|关)\s*(\d+)", 指令)
        m2 = re.fullmatch(r"(\d+)\s*(上移|下移)", 指令)
        if m1:
            n = int(m1.group(2))
            if 1 <= n <= len(清单):
                清单[n - 1][1] = m1.group(1) == "开"
                模块设置.保存(清单)
                print(f"✔ 已{'启用' if 清单[n - 1][1] else '禁用'}：{清单[n - 1][0]}")
                continue
        elif m2:
            n = int(m2.group(1))
            目标 = n - 1 if m2.group(2) == "上移" else n + 1
            if 1 <= n <= len(清单) and 1 <= 目标 <= len(清单):
                清单[n - 1], 清单[目标 - 1] = 清单[目标 - 1], 清单[n - 1]
                模块设置.保存(清单)
                print(f"✔ 已{m2.group(2)}：{清单[目标 - 1][0]}")
                continue
            if 1 <= n <= len(清单):
                print("已经在最" + ("上面" if m2.group(2) == "上移" else "下面") + "了。")
                continue
        print("没看懂，请按上面的写法输入（例如：关 2）。")


def 主菜单():
    while True:
        清单, 提醒 = 模块设置.读取()
        print("\n" + "=" * 40)
        print("            仓 库 助 手")
        print("=" * 40)
        print("当前模块（按运行顺序）：")
        显示清单(清单)
        if 提醒:
            print(f"\n⚠ {提醒}")
        print("-" * 40)
        print(" 1. 运行全部已启用模块（按顺序）")
        print(" 2. 只运行某一个模块")
        print(" 3. 这次临时自选几个（例如 1,3）")
        print(" 4. 调整模块顺序和开关")
        print(" 5. 设置消息格式")
        print(" 6. 设置飞书")
        print(" 7. 登录 WMS")
        print(" 0. 退出")
        选 = input("请输入数字，按回车：").strip()

        if 选 == "1":
            运行([名 for 名, 开 in 清单 if 开])
        elif 选 in ("2", "3"):
            if not 清单:
                continue
            提示 = "运行第几个？输入编号：" if 选 == "2" else "输入要运行的编号，按想要的顺序，用逗号隔开（例如 1,3）："
            编号 = 解析编号(input(提示), len(清单))
            if 编号 is None or (选 == "2" and len(编号) != 1):
                print("编号不对。")
                continue
            运行([清单[n - 1][0] for n in 编号])   # 临时自选时，禁用的模块也会运行
        elif 选 == "4":
            调整顺序(清单)
            continue
        elif 选 == "5":
            subprocess.run([PY, str(根目录 / "公共" / "设置消息格式.py")])
        elif 选 == "6":
            subprocess.run([PY, str(根目录 / "公共" / "设置飞书.py")])
        elif 选 == "7":
            subprocess.Popen([CHROME, f"--user-data-dir={专用配置目录}", "--no-first-run", "--new-window", WMS首页])
            print("\n已打开自动化专用 Chrome。请在里面登录 WMS（已登录就不用管），然后关掉那个 Chrome 窗口。")
        elif 选 == "0":
            return
        else:
            print("请输入菜单里的数字。")
            continue
        input("\n按回车返回菜单……")


if __name__ == "__main__":
    try:
        主菜单()
    except (KeyboardInterrupt, EOFError):
        pass
