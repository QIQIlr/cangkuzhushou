# 职责：每个模块自己的设置（查询区域、发到飞书 等），保存在 模块参数.json。
# 输入：模块名；模块文件里的 默认参数 字典。
# 输出：合并好的参数（文件里没有的项用模块默认值）。
# 窗口里每个模块的“设置”按钮改的就是这里。区域选项从 WMS 读取后缓存在同一个文件里。
# 保护（2026-10-24）：文件读不出来时不当成空的覆盖掉——改用 设置备份\模块参数.json，并把读不出的原文件另存一份；
#   每次写入先写临时文件再替换（写到一半断电也不会坏），写好后更新备份。窗口和后台运行同时写时排队。
import json
import os
import shutil
import threading
from datetime import datetime
from pathlib import Path

根目录 = Path(__file__).resolve().parent.parent
参数文件 = 根目录 / "模块参数.json"
备份文件 = 根目录 / "设置备份" / "模块参数.json"
默认区域选项 = ["A区", "B区", "C区", "D区", "E区", "F区"]
_锁 = threading.RLock()
问题 = ""          # 读不出设置文件时的说明，工作台会显示出来


def _读(路径):
    return json.loads(路径.read_text(encoding="utf-8"))


def _读全部():
    global 问题
    with _锁:
        if not 参数文件.exists():
            return {}
        try:
            数据 = _读(参数文件)
            if not isinstance(数据, dict):
                raise ValueError("内容不是设置")
            return 数据
        except Exception as e:
            try:
                数据 = _读(备份文件)
            except Exception:
                数据 = None
            问题 = (f"模块参数.json 读不出来（{type(e).__name__}）。"
                    + ("这次用的是上一次的备份；" if 数据 is not None else "备份也读不出来，这次用默认设置；")
                    + "原文件没有删，请告诉 Claude。")
            return 数据 if isinstance(数据, dict) else {}


def _写全部(数据):
    with _锁:
        if 参数文件.exists():
            try:
                _读(参数文件)
            except Exception:   # 原文件是坏的：先另存一份，不直接盖掉
                坏 = 备份文件.parent / f"模块参数_读不出_{datetime.now():%Y%m%d_%H%M%S}.json"
                坏.parent.mkdir(exist_ok=True)
                shutil.copyfile(参数文件, 坏)
        临时 = 参数文件.with_suffix(".json.tmp")
        临时.write_text(json.dumps(数据, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(临时, 参数文件)
        备份文件.parent.mkdir(exist_ok=True)
        shutil.copyfile(参数文件, 备份文件)


def 读取(模块名, 默认参数=None):
    参数 = dict(默认参数 or {})
    参数.setdefault("发到飞书", True)
    参数.update(_读全部().get("模块", {}).get(模块名, {}))
    return 参数


def _改(动作):
    """读 → 改 → 写，整个过程排队，避免窗口和后台运行同时写时互相覆盖。"""
    with _锁:
        数据 = _读全部()
        动作(数据)
        _写全部(数据)


def 保存(模块名, 参数):
    _改(lambda 数据: 数据.setdefault("模块", {}).__setitem__(模块名, 参数))


def 区域选项():
    return _读全部().get("区域选项") or 默认区域选项


def 保存区域选项(选项):
    _改(lambda 数据: 数据.__setitem__("区域选项", sorted(选项)))


# —— 模块的名字：原名 = 模块文件名（固定，程序内部靠它认模块）；显示名 = 小柒在窗口里改的名字 ——
不能用的符号 = '\\/:*?"<>|'
最长 = 20


def 显示名(原名):
    """窗口、飞书卡片、Excel、日志里用的名字。没改过就是原名。"""
    return _读全部().get("名字", {}).get(原名) or 原名


def 显示名表():
    """{原名: 改过的名字}，一次读完（运行记录页这类要查很多次的地方用）。"""
    return dict(_读全部().get("名字", {}))


def 检查名字(原名, 新名, 所有原名):
    """新名字能不能用。能用返回 ""，不能用返回一句原因。"""
    if not 新名:
        return "名字不能是空的。"
    if len(新名) > 最长:
        return f"名字最多 {最长} 个字，现在是 {len(新名)} 个。"
    坏 = [c for c in 新名 if c in 不能用的符号]
    if 坏:
        return f"名字里不能有这些符号：{' '.join(不能用的符号)}（现在有 {' '.join(dict.fromkeys(坏))}）。"
    for 别的 in 所有原名:
        if 别的 != 原名 and 新名 in (别的, 显示名(别的)):
            return f"已经有一个模块叫“{新名}”了，换一个名字吧。"
    return ""


def 保存显示名(原名, 新名):
    """新名 和原名一样（或空）= 恢复原名。"""
    def 动作(数据):
        名字 = 数据.setdefault("名字", {})
        if not 新名 or 新名 == 原名:
            名字.pop(原名, None)
        else:
            名字[原名] = 新名
    _改(动作)


def 界面设置(名, 默认=None):
    """窗口自己的小设置（例如“运行完自动发到飞书”）。"""
    return _读全部().get("界面", {}).get(名, 默认)


def 保存界面设置(名, 值):
    _改(lambda 数据: 数据.setdefault("界面", {}).__setitem__(名, 值))