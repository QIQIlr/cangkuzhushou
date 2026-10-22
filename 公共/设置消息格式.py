# 职责：修改飞书消息格式（双击 设置消息格式.bat 运行）。
# 流程：选模块 → 用记事本打开格式文件 → 保存并关掉记事本 → 检查有没有写错 → 用最近一次查询结果预览
#       → 问要不要发一条【测试】预览到飞书群。
# 写错时：指出第几行错了，可以马上再改；不改的话，查询时继续用上一次能用的格式，查询不会失败。
import importlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

根目录 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(根目录))
from 公共 import 飞书  # noqa: E402
from 公共.消息格式 import 格式目录, 格式错误, 排版  # noqa: E402


def 问(提示):
    while True:
        答 = input(提示 + "（输入 Y 或 N，按回车）：").strip().upper()
        if 答 in ("Y", "N"):
            return 答 == "Y"


def 选模块():
    文件们 = sorted(p.stem for p in 格式目录.glob("*.txt"))
    if not 文件们:
        print("格式 文件夹里还没有格式文件。")
        return None
    if len(文件们) == 1:
        return 文件们[0]
    print("要改哪个模块的消息格式？")
    for i, 名 in enumerate(文件们, 1):
        print(f"  {i}. {名}")
    while True:
        答 = input("输入编号，按回车：").strip()
        if 答.isdigit() and 1 <= int(答) <= len(文件们):
            return 文件们[int(答) - 1]


def 最近结果(模块名):
    文件 = 根目录 / "日志" / f"最近结果_{模块名}.json"
    if 文件.exists():
        return json.loads(文件.read_text(encoding="utf-8")), "最近一次查询结果"
    示例 = {"状态": "成功", "数量": 2, "开始时间": datetime.now().isoformat(),
            "区域列表": [{"区域": "D区", "状态": "无数据", "数量": 0, "单号": []},
                         {"区域": "E区", "状态": "成功", "数量": 2, "单号": ["示例-000001", "示例-000002"]}]}
    return 示例, "示例数据（还没有查询记录）"


def 主程序():
    模块名 = sys.argv[1] if len(sys.argv) > 1 else 选模块()
    if not 模块名:
        return 1
    格式文件 = 格式目录 / f"{模块名}.txt"
    模块 = importlib.import_module(f"模块.{模块名}")

    while True:
        print(f"\n正在用记事本打开 格式\\{模块名}.txt ……改好后请保存（Ctrl+S），再关掉记事本。")
        subprocess.run(["notepad.exe", str(格式文件)])
        文字 = 格式文件.read_text(encoding="utf-8-sig")
        结果, 来源 = 最近结果(模块名)
        公共, 区域列表 = 模块.排版内容(结果, 用时=15)
        try:
            排版(文字, 公共, 区域列表)
        except 格式错误 as e:
            print(f"\n✘ 格式写错了：{e}")
            print("  不改的话，查询时会继续用上一次能用的格式，查询不会失败。")
            if 问("现在再打开改一下吗？"):
                continue
            return 1
        break

    消息, _ = 模块.组成消息(结果, "（预览）", 用时=15)   # 这一步也会把新格式存为“上次可用”
    print(f"\n✔ 格式没问题。下面是用{来源}排出来的样子：")
    print("-" * 40)
    print(消息)
    print("-" * 40)

    if not 飞书.可以发送():
        print("（飞书还没设置好，先不发预览。需要时双击 设置飞书.bat。）")
        return 0
    if 问("发一条【测试】预览到飞书群吗？"):
        状态, 说明 = 飞书.发送("【测试】格式预览\n" + 消息)
        print(f"飞书：{状态}（{说明}）")
    print("\n新格式已生效，下次查询就会用它。")
    return 0


if __name__ == "__main__":
    try:
        结果码 = 主程序()
    except (KeyboardInterrupt, EOFError):
        print("\n已取消。")
        结果码 = 1
    sys.exit(结果码)
