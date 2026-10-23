# 职责：读写 模块设置.txt（模块的运行顺序和开关）。
# 文件格式：一行一个模块，行的先后 = 运行顺序；行首写“开”或“关”，空一格再写模块名。
#   以 # 开头的行是说明。
# 写错时（模块名写错、重复、开关写错）：指出第几行，并沿用上一次能用的设置（设置备份\模块设置.txt）。
# 新模块（模块 文件夹里有、设置里没有）自动加在最后，状态为“关”，核对通过后再打开。
from pathlib import Path

根目录 = Path(__file__).resolve().parent.parent
设置文件 = 根目录 / "模块设置.txt"
备份文件 = 根目录 / "设置备份" / "模块设置.txt"
模块目录 = 根目录 / "模块"

说明 = """# ===== 模块设置：运行顺序和开关 =====
# 一行一个模块。上面的先运行，下面的后运行。
# 行首写“开”= 运行全部时会运行；写“关”= 跳过。开/关 后面空一格再写模块名。
# 一般不用手改这个文件：在仓库助手窗口里勾选、拖动，会自动保存到这里。
# 新加的模块会自动出现在最后，默认是“关”，确认好用后再打开。
"""


class 设置错误(Exception):
    pass


def 所有模块():
    """模块 文件夹里的模块名（文件名）。"""
    return sorted(p.stem for p in 模块目录.glob("*.py") if not p.stem.startswith("_"))


def 解析(文字):
    已有 = set(所有模块())
    清单, 见过 = [], set()
    for 行号, 行 in enumerate(文字.splitlines(), 1):
        s = 行.strip()
        if not s or s.startswith("#"):
            continue
        部分 = s.split(None, 1)
        if len(部分) != 2 or 部分[0] not in ("开", "关"):
            raise 设置错误(f"第 {行号} 行：要写成“开 模块名”或“关 模块名”，现在是：{s}")
        开关, 名 = 部分[0], 部分[1].strip()
        if 名 not in 已有:
            raise 设置错误(f"第 {行号} 行：没有叫“{名}”的模块（现有：{'、'.join(sorted(已有)) or '无'}）")
        if 名 in 见过:
            raise 设置错误(f"第 {行号} 行：“{名}”重复了")
        见过.add(名)
        清单.append([名, 开关 == "开"])
    return 清单


def 读取():
    """返回 (清单[[名, 是否启用], …], 提醒文字)。会自动补上新模块（关），并更新备份。"""
    提醒 = ""
    try:
        清单 = 解析(设置文件.read_text(encoding="utf-8-sig")) if 设置文件.exists() else []
    except 设置错误 as e:
        提醒 = f"模块设置.txt 写错了：{e}。这次沿用上一次能用的设置。"
        try:
            清单 = 解析(备份文件.read_text(encoding="utf-8"))
        except Exception:
            清单 = []
        已列 = {名 for 名, _ in 清单}
        清单 += [[名, False] for 名 in 所有模块() if 名 not in 已列]
        return 清单, 提醒
    已列 = {名 for 名, _ in 清单}
    新的 = [名 for 名 in 所有模块() if 名 not in 已列]
    if 新的 or not 设置文件.exists():
        清单 += [[名, False] for 名 in 新的]
        if 新的:
            提醒 = "发现新模块（已加在最后，默认关）：" + "、".join(新的)
    保存(清单)
    return 清单, 提醒


def 保存(清单):
    文字 = 说明 + "".join(f"{'开' if 开 else '关'} {名}\n" for 名, 开 in 清单)
    设置文件.write_text(文字, encoding="utf-8")
    备份文件.parent.mkdir(exist_ok=True)
    备份文件.write_text(文字, encoding="utf-8")
