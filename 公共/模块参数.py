# 职责：每个模块自己的设置（查询区域、发到飞书 等），保存在 模块参数.json。
# 输入：模块名；模块文件里的 默认参数 字典。
# 输出：合并好的参数（文件里没有的项用模块默认值）。
# 窗口里每个模块的“设置”按钮改的就是这里。区域选项从 WMS 读取后缓存在同一个文件里。
import json
from pathlib import Path

根目录 = Path(__file__).resolve().parent.parent
参数文件 = 根目录 / "模块参数.json"
默认区域选项 = ["A区", "B区", "C区", "D区", "E区", "F区"]


def _读全部():
    try:
        return json.loads(参数文件.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _写全部(数据):
    参数文件.write_text(json.dumps(数据, ensure_ascii=False, indent=2), encoding="utf-8")


def 读取(模块名, 默认参数=None):
    参数 = dict(默认参数 or {})
    参数.setdefault("发到飞书", True)
    参数.update(_读全部().get("模块", {}).get(模块名, {}))
    return 参数


def 保存(模块名, 参数):
    数据 = _读全部()
    数据.setdefault("模块", {})[模块名] = 参数
    _写全部(数据)


def 区域选项():
    return _读全部().get("区域选项") or 默认区域选项


def 保存区域选项(选项):
    数据 = _读全部()
    数据["区域选项"] = sorted(选项)
    _写全部(数据)
