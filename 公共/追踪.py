# 职责：可追踪状态——快照 + 变化量（2026-11-01 新增，依据方案 可追踪状态_方案_2026-10-31.md v1）。
#   每次运行完一个数量模块，在 日志\快照\<模块原名>\<YYYY-MM-DD>.jsonl 追加一行（JSON Lines，一次运行一行）；
#   下次运行拿"这次"和"上次"比，算出每个日期、每个区变了多少，排成一行行字符串交给结果页直接画
#   （窗口只负责画，不重算、不读文件）。
#
# 三条老规矩照旧：
#   1) 只存数字，不存单号、地址、电话；快照里没有客户信息。
#   2) 变化永远不影响结果状态，也不发飞书（只在窗口里看）。
#   3) 不知道绝不当 0 算（查不到的格子一律"不知道"，显示"—"）。
#
# 和 公共\日志.py 的"网页快照.html"不是一回事：那个是出错时存的整页网页（给 AI 排错用，写入前已遮掩），
#   这里是"每次运行各日期各区多少单"的数字记录。两者互不相干，别混。
#
# 计算规则逐条照方案 §4.1–§4.7；和方案对不上的地方在改动报告里逐条写了。
import json
import os
import re
from datetime import date, datetime, timedelta

from 公共 import 日志, 模块参数

版本 = 1                       # 快照格式版本；以后改格式就 +1，读的时候不认识的版本整行跳过
根 = 日志.日志根 / "快照"       # 模块级变量（自测时可整体替换成临时文件夹）
保留天数 = 90                  # 和日志一样留 90 天
星期 = "一二三四五六日"
流程环节 = ("待审核", "待拣货", "待增值")   # 「流程一览」固定按这个顺序（审核 → 拣货 → 增值）
_清理过 = set()                # 每个快照根每次运行只清理一遍（键是根目录字符串）


# ---------------- 小工具 ----------------

def _记(记录, 句):
    """往这次运行记录里写一行；没有记录（自测）就什么也不做。写日志本身出错也不能影响别处。"""
    if 记录 is None:
        return
    try:
        记录.写(句)
    except Exception:
        pass


def _去粗(文字):
    return str(文字).replace("**", "")


def _号(数):
    """摘要句里的带符号数字：正 +N、负 −N（U+2212，只是显示用），不知道 —。"""
    if 数 is None:
        return "—"
    if 数 == 0:
        return "0"
    return f"+{数}" if 数 > 0 else f"−{-数}"


def _格(数):
    """表格格子里的变化：正 +N、负 -N（ASCII，方便复制进 Excel 当数字），没变 0，不知道 —。"""
    if 数 is None:
        return "—"
    if 数 == 0:
        return "0"
    return f"+{数}" if 数 > 0 else f"-{-数}"


def _数格(数):
    """「今天各次」里的普通格：那次的数；不知道写 —。"""
    return "—" if 数 is None else str(数)


def _日名(日, 今天):
    """行名：10/29 周四；今天那一行后面加（今天）。日 = "YYYY-MM-DD" 字符串。"""
    d = date.fromisoformat(日)
    return f"{d:%m/%d} 周{星期[d.weekday()]}" + ("（今天）" if 日 == 今天 else "")


def _标签(时间, 参照日):
    """摘要句括号里、表标题里怎么写时间：同一天只写 15:23，跨天写 10/30 17:22。"""
    return f"{时间:%H:%M}" if 时间.date() == 参照日 else f"{时间:%m/%d %H:%M}"


def _拆(格们):
    """模块.快照(结果) 的返回值 → (日期框, 格子列表)。
    通常是 dict {"日期框": …, "格们": [...]}（日期框 = 按哪个时间分日期；无任务包裹是空）；
    也认直接给的格子列表（这时日期框按空处理）。"""
    if isinstance(格们, dict):
        return 格们.get("日期框") or "", list(格们.get("格们") or [])
    return "", list(格们 or [])


# ---------------- 快照存盘 ----------------

_格字段 = ("类", "区", "查到", "全部", "天", "起点", "对上", "差", "查到日")


def _净格(格):
    """只留方案 §3.1 规定的字段（白名单，顺序也照它）。
    日志/快照 是“只存数字、不存单号”的硬规矩：以后谁新写的 快照() 顺手把单号塞进格子，也不会落盘。
    没有的键就不写（例如对上时没有“查到日”）。"""
    return {名: 格[名] for 名 in _格字段 if 名 in 格}


def _行(模块名, 结果, 日期框, 格们, 记录):
    """拼一行快照（字段见方案 §3.1 / §2.3）。时间 = 结果["开始时间"]，日期 = 它的日期。"""
    时间 = 结果.get("开始时间") or datetime.now()
    格们 = [_净格(g) for g in 格们 if isinstance(g, dict)]     # 白名单，多余的键丢掉
    组们 = 结果.get("组们") or []
    if not 组们:      # 无任务包裹这类没有“组”的结果：所有区当一组（组名用显示名，摘要句才读得通）
        区们 = list(dict.fromkeys(g["区"] for g in 格们 if g.get("区")))
        组们 = [(模块参数.显示名(模块名), 区们)]
    return {"版本": 版本, "模块": 模块名,
            "时间": 时间.isoformat(timespec="seconds"), "日期": f"{时间:%Y-%m-%d}",
            "日志文件夹": getattr(记录, "文件夹名", "") or "", "状态": 结果.get("状态", ""),
            "日期框": 日期框 or "", "组们": [[名, list(区们)] for 名, 区们 in 组们],
            "格们": 格们}


def 记快照(快照行, 测试=False, 记录=None):
    """把这一行追加到 日志/快照/<模块原名>/<日期>.jsonl。返回 True = 真写进去了。
    测试=True（Claude 自测）不写文件（和 上次结果.json 同一条规矩）。写失败只写日志，不影响这次结果。"""
    if not 快照行:
        return False
    if 测试:
        _记(记录, "自测（测试=True）：这次不写快照文件")
        return False
    try:
        夹 = 根 / 快照行["模块"]
        夹.mkdir(parents=True, exist_ok=True)
        路径 = 夹 / f"{快照行['日期']}.jsonl"
        with open(路径, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(快照行, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())          # 真的落到硬盘上，突然关机也不会丢这一行
        if str(根) not in _清理过:
            _清理过.add(str(根))
            _清理(记录)
        return True
    except Exception as e:
        _记(记录, f"快照没存上：{type(e).__name__}: {e}（不影响这次结果）")
        return False


def _清理(记录=None):
    """删掉 90 天以前的快照文件。只删文件名像 2026-10-30.jsonl 的，别的一律不碰。"""
    界限 = datetime.now() - timedelta(days=保留天数)
    try:
        if not 根.exists():
            return
        夹们 = [x for x in 根.iterdir() if x.is_dir()]
    except Exception as e:
        _记(记录, f"快照文件夹读不了：{type(e).__name__}: {e}（当作第一次记录）")
        return
    删了 = 0
    for 夹 in 夹们:
        try:
            文件们 = list(夹.iterdir())
        except Exception:
            continue
        for f in 文件们:
            if not re.match(r"^\d{4}-\d{2}-\d{2}\.jsonl$", f.name):
                continue
            try:
                if datetime.strptime(f.name[:10], "%Y-%m-%d") < 界限:
                    f.unlink()
                    删了 += 1
            except Exception:
                pass
    if 删了:
        _记(记录, f"快照清理：删了 {删了} 个 {保留天数} 天以前的文件")


# ---------------- 读旧快照 ----------------

def _读文件(路径, 记录):
    """逐行读一个 .jsonl。坏行、版本不认识的行跳过并写一行日志；整个文件读不了也写一行。"""
    好们 = []
    try:
        with open(路径, encoding="utf-8") as f:
            行们 = f.readlines()
    except Exception as e:
        _记(记录, f"快照 {路径.name} 读不了：{type(e).__name__}: {e}（当作没有以前的记录）")
        return 好们
    for 序号, 原文 in enumerate(行们, 1):
        原文 = 原文.strip()
        if not 原文:
            continue
        try:
            快照 = json.loads(原文)
        except Exception:
            _记(记录, f"快照 {路径.name} 第 {序号} 行读不出，已跳过")
            continue
        if not isinstance(快照, dict) or 快照.get("版本") != 版本:
            _记(记录, f"快照 {路径.name} 第 {序号} 行版本不认识，已跳过")
            continue
        try:
            快照["时间"] = datetime.fromisoformat(快照["时间"])
            if not 快照.get("模块") or not 快照.get("日期"):
                raise ValueError("缺模块或日期")
        except Exception:
            _记(记录, f"快照 {路径.name} 第 {序号} 行读不出，已跳过")
            continue
        快照["索引"] = _索(快照)
        好们.append(快照)
    return 好们


def _索(快照):
    """{(区, 类): 格}：一个快照里所有格子，方便按 类×区 找。"""
    return {(g.get("区"), g.get("类")): g for g in (快照.get("格们") or []) if isinstance(g, dict)}


def _读模块(模块名, 记录, 早于=None, 今天字=None):
    """读这个模块的快照，按时间从新到旧返回（每个快照带 "索引"）。
    早于：只要 时间 < 早于 的（防止电脑时间被调回去后拿"未来"的快照来比）；
    今天字：只读那一天的文件（找"今天各次"用）。"""
    夹 = 根 / 模块名
    if not 夹.exists():      # 文件夹被删了 / 第一次运行：当作没有以前的记录（方案 §6 E19）
        _记(记录, f"快照文件夹 {模块名} 不存在，当作第一次记录")
        return []
    try:
        文件们 = sorted((x for x in 夹.iterdir() if re.match(r"^\d{4}-\d{2}-\d{2}\.jsonl$", x.name)), reverse=True)
    except Exception as e:
        _记(记录, f"快照文件夹 {模块名} 读不了：{type(e).__name__}: {e}（当作第一次记录）")
        return []
    if 今天字:
        文件们 = [x for x in 文件们 if x.name[:10] == 今天字]
    else:
        文件们 = 文件们[:90]       # 找"上次"时最多往前看 90 个文件
    快照们 = []
    for 文件 in 文件们:
        快照们 += _读文件(文件, 记录)
    if 早于 is not None and not 今天字:
        快照们 = [s for s in 快照们 if s["时间"] < 早于]
    快照们.sort(key=lambda s: s["时间"], reverse=True)
    return 快照们


# ---------------- 取值（方案 §4.1 / §4.3） ----------------

def _和(数们):
    """几格相加。有一格不知道 → 不知道（绝不当 0）。"""
    if any(v is None for v in 数们):
        return None
    return sum(数们)


def _值(索引, 类, 区, 日):
    """某一格某一天的数（日是 "YYYY-MM-DD"）。没查到 → 不知道；查过就用查到的；
    没查过但这个格对上了（各天之和 = 总数）→ 0；没对上 → 不知道。"""
    格 = 索引.get((区, 类))
    if 格 is None or not 格.get("查到"):
        return None
    天 = 格.get("天") or {}
    if 日 in 天:
        return 天[日]
    return 0 if 格.get("对上") else None


def _组值(索引, 类们, 区, 日):
    """组值：这个视图里各类相加；任何一个不知道 → 不知道。"""
    return _和([_值(索引, 类, 区, 日) for 类 in 类们])


def _列(索引, 类们, 区们, 日):
    """组合计列（某一天的合计）：各区相加；任何一个不知道 → 不知道。"""
    return _和([_组值(索引, 类们, 区, 日) for 区 in 区们])


def _合计(索引, 类们, 区):
    """合计行某一格：这个视图里各类的“全部”相加（用总数，所以没对上时也知道）。"""
    格们 = [索引.get((区, 类)) for 类 in 类们]
    if any(g is None or not g.get("查到") or g.get("全部") is None for g in 格们):
        return None
    return sum(g["全部"] for g in 格们)


def _合计总(索引, 类们, 区们):
    return _和([_合计(索引, 类们, 区) for 区 in 区们])


def _之前(索引, 类们, 区们, 今天字):
    """之前日期的 = 合计行的组合计 − 组合计列(今天)。“今天”永远是这次运行的日期。"""
    今 = _列(索引, 类们, 区们, 今天字)
    总 = _合计总(索引, 类们, 区们)
    return None if 今 is None or 总 is None else 总 - 今


def _更早格(格):
    """「更早（没对上）」用这个格：没对上且差 > 0 → 差；对上了 → 0；没查到 → 不知道。"""
    if 格 is None or not 格.get("查到"):
        return None
    if not 格.get("对上") and (格.get("差") or 0) > 0:
        return 格["差"]
    return 0


def _更早(索引, 类们, 区):
    return _和([_更早格(索引.get((区, 类))) for 类 in 类们])


def _更早变化(这格, 上格):
    """「更早（没对上）」那一行的变化：两次都对上了、或两次的“查到日”相同，才算得出来。"""
    if 这格 is None or 上格 is None or not 这格.get("查到") or not 上格.get("查到"):
        return None
    if 这格.get("对上") and 上格.get("对上"):
        return 0
    甲, 乙 = 这格.get("查到日"), 上格.get("查到日")
    if 甲 and 乙 and 甲 == 乙:
        return _更早格(这格) - _更早格(上格)
    return None


def _有更早(索引, 类们, 区们):
    """这张表要不要“更早（没对上）”那一行：有 对上=false 且 差>0 的格才要。"""
    for 类 in 类们:
        for 区 in 区们:
            格 = 索引.get((区, 类))
            if 格 is not None and 格.get("查到") and not 格.get("对上") and (格.get("差") or 0) > 0:
                return True
    return False


def _有数(v):
    """这一格算不算“不是 0”：不知道也算（不然会把不知道的日期藏起来）。"""
    return v is None or v != 0


# ---------------- 「和上次比」 ----------------

def _候选日(这次索引, 上次索引, 类们, 区们, 今天字):
    """这次和上次出现过的所有日期（含今天），从早到晚。"""
    日们 = {今天字}
    for 索引 in (这次索引, 上次索引):
        if 索引 is None:
            continue
        for (区, 类), 格 in 索引.items():
            if 区 in 区们 and 类 in 类们:
                日们 |= set((格.get("天") or {}).keys())
    return sorted(日们)


def _比较(组名, 区们, 视图类们们, 这次索引, 上次, 今天字):
    """[(视图名, 列名, 行们)] + [每个视图一份提示们]。上次 = 上次那份快照（首次时是 None）。
    行里的格子已经是 “+N”/“-N”/“0”/“—” 字符串（方案 §5.4）。
    视图类们们 = [(视图名, [类…]), …]，第一个是「合计」。"""
    上次索引 = 上次["索引"] if 上次 is not None else None
    多区 = len(区们) > 1
    合列名 = f"{组名.replace('仓库', '')}合计"
    全类 = 视图类们们[0][1]
    要更早 = _有更早(这次索引, 全类, 区们) or (上次索引 is not None and _有更早(上次索引, 全类, 区们))
    视图们, 提示们们 = [], []
    for 视图名, 类们 in 视图类们们:
        列名 = ["日期"] + 区们 + ([合列名] if 多区 else [])
        提示们 = {}
        行们 = []
        if 要更早:
            差们 = [_和([_更早变化(这次索引.get((区, 类)), (上次索引 or {}).get((区, 类))) for 类 in 类们])
                    for 区 in 区们]
            行们.append(["更早（没对上）"] + [_格(v) for v in 差们] + ([_格(_和(差们))] if 多区 else []))
        for 日 in _候选日(这次索引, 上次索引, 类们, 区们, 今天字):
            这 = _列(这次索引, 类们, 区们, 日)
            上 = _列(上次索引, 类们, 区们, 日) if 上次索引 is not None else None
            if not _有数(这) and not _有数(上):
                continue
            名 = _日名(日, 今天字)
            if 上次索引 is not None and 上 not in (None, 0) and 这 == 0:
                名 += "（清零了）"
            if 日 == 今天字 and 上次 is not None and 上次["日期"] < 今天字 and 这 not in (None, 0):
                名 += "（新的一天）"
            短 = f"{日[5:7]}/{日[8:10]}"
            差们 = []
            for 区 in 区们:
                甲 = _组值(这次索引, 类们, 区, 日)
                乙 = _组值(上次索引, 类们, 区, 日) if 上次索引 is not None else None
                差们.append(None if 甲 is None or 乙 is None else 甲 - 乙)
                if 上次索引 is not None:
                    提示们[f"{名}|{区}"] = (f"{区} {短}：这次没查到，没法比" if 甲 is None or 乙 is None
                                          else f"{区} {短}：上次 {乙} → 这次 {甲}（{_格(甲 - 乙)}）")
            行们.append([名] + [_格(v) for v in 差们] + ([_格(_和(差们))] if 多区 else []))
        总们 = []
        for 区 in 区们:
            甲 = _合计(这次索引, 类们, 区)
            乙 = _合计(上次索引, 类们, 区) if 上次索引 is not None else None
            总们.append(None if 甲 is None or 乙 is None else 甲 - 乙)
        行们.append(["**合计**"] + [f"**{_格(v)}**" for v in 总们] + ([f"**{_格(_和(总们))}**"] if 多区 else []))
        视图们.append((视图名, 列名, 行们))
        提示们们.append(提示们)
    return 视图们, 提示们们


# ---------------- 摘要句（方案 §4.7） ----------------

def _摘要(组名, 类们, 区们, 这次索引, 上次, 今天字):
    """结论条下面那一行灰字里的一个组。多个组用“；”连起来（调用方拼）。"""
    上次索引 = 上次["索引"]
    标签 = _标签(上次["时间"], date.fromisoformat(今天字))
    这次总 = _合计总(这次索引, 类们, 区们)
    上次总 = _合计总(上次索引, 类们, 区们)
    if 这次总 is None or 上次总 is None:
        return f"{组名}：这次有区没查到，没法和上次比"
    差 = 这次总 - 上次总
    甲 = _之前(这次索引, 类们, 区们, 今天字)
    乙 = _之前(上次索引, 类们, 区们, 今天字)
    之前差 = None if 甲 is None or 乙 is None else 甲 - 乙
    丙 = _列(这次索引, 类们, 区们, 今天字)
    丁 = _列(上次索引, 类们, 区们, 今天字)
    今差 = None if 丙 is None or 丁 is None else 丙 - 丁
    缺 = "（有格子没查到）" if (之前差 is None or 今差 is None) else ""
    if 差 == 0:
        if 之前差 == 0 and 今差 == 0:
            return f"{组名}和上次（{标签}）完全一样"
        return f"{组名}合计和上次（{标签}）一样，{这次总} 单：之前日期的 {_号(之前差)}，今天的 {_号(今差)}{缺}"
    方向 = "多" if 差 > 0 else "少"
    return f"{组名}比上次（{标签}）{方向} {abs(差)} 单：之前日期的 {_号(之前差)}，今天的 {_号(今差)}{缺}"


# ---------------- 表下面的灰字（方案 §4.6 第 2 条） ----------------

def _灰字(模块名, 日期框, 类们, 区们, 这次索引, 上次, 今天字):
    """有旧日期比上次多了才写一句。只说明，不报警、不改状态（小柒 2026-11-01 确认）。"""
    if 上次 is None:
        return None
    上次索引 = 上次["索引"]
    多们 = []
    for 日 in _候选日(这次索引, 上次索引, 类们, 区们, 今天字):
        if 日 >= 今天字:
            continue
        这 = _列(这次索引, 类们, 区们, 日)
        上 = _列(上次索引, 类们, 区们, 日)
        if 这 is None or 上 is None:
            continue
        if 这 - 上 > 0:
            多们.append((日, 这 - 上))
    if not 多们:
        return None
    例 = "、".join(f"{d[5:7]}/{d[8:10]} +{n}" for d, n in 多们[:2])      # 最多举 2 个例子
    if "增值" in (日期框 or ""):
        后 = f"{模块参数.显示名(模块名)}按‘{日期框}’分日期，旧日期变多可能是正常的（未验证）。"
    else:
        后 = "请到 WMS 看一下是不是任务被退回。"
    return f"有 {len(多们)} 个之前的日期比上次多了（如 {例}）。{后}"


# ---------------- 「今天各次」（方案 §4.5） ----------------

def _全在(索引, 类们, 区们):
    """这一组的每个 类×区 都在这份快照里（查到没查到都算在里面）。"""
    return all((区, 类) in 索引 for 类 in 类们 for 区 in 区们)


def _全查到(索引, 类们, 区们):
    """这一组的每个 类×区 都查到了。"""
    for 类 in 类们:
        for 区 in 区们:
            格 = 索引.get((区, 类))
            if 格 is None or not 格.get("查到"):
                return False
    return True


def _更早组(索引, 类们, 区们):
    return _和([_更早(索引, 类们, 区) for 区 in 区们])


def _时刻名们(全部们, 显示们):
    """列名：HH:MM；今天有两列 HH:MM 一样时这两列都写 HH:MM:SS；最后一列（这次）后面加“（这次）”。"""
    粗们 = [f"{s['时间']:%H:%M}" for s in 全部们]
    名们 = [f"{s['时间']:%H:%M:%S}" if 粗们.count(f"{s['时间']:%H:%M}") > 1 else f"{s['时间']:%H:%M}"
            for s in 显示们]
    if 名们:
        名们[-1] += "（这次）"
    return 名们


def _今天表(类们, 区们, 全部们, 显示们, 今天字):
    """(列名, 行们)。全部们 = 今天所有快照（决定哪些日期要显示）；显示们 = 真正画的几列，从早到晚，最后一个是这次。
    格子里是那一次的“组合计列”（§4.3 的定义），不知道写 “—”。"""
    要变化 = len(全部们) > 1
    初 = next((s for s in 全部们 if _全查到(s["索引"], 类们, 区们)), None)
    列名 = ["日期"] + _时刻名们(全部们, 显示们) + (["今天变化"] if 要变化 else [])
    要更早 = any((g := (s["索引"].get((区, 类)))) is not None and g.get("查到") and not g.get("对上")
              and (g.get("差") or 0) > 0 for s in 全部们 for 类 in 类们 for 区 in 区们)
    候选 = {今天字}
    for s in 全部们:
        for (区, 类), 格 in s["索引"].items():
            if 区 in 区们 and 类 in 类们:
                候选 |= set((格.get("天") or {}).keys())
    行们 = []
    if 要更早:
        行 = ["更早（没对上）"] + [_数格(_更早组(s["索引"], 类们, 区们)) for s in 显示们]
        if 要变化:
            行.append(_格(None if 初 is None else _更早组(显示们[-1]["索引"], 类们, 区们) - _更早组(初["索引"], 类们, 区们)))
        行们.append(行)
    末 = 显示们[-1]["索引"]
    for 日 in sorted(候选):
        各列 = [_列(s["索引"], 类们, 区们, 日) for s in 全部们]
        if not any(_有数(v) for v in 各列):
            continue
        行 = [_日名(日, 今天字)] + [_数格(_列(s["索引"], 类们, 区们, 日)) for s in 显示们]
        if 要变化:
            甲, 乙 = _列(末, 类们, 区们, 日), (None if 初 is None else _列(初["索引"], 类们, 区们, 日))
            行.append(_格(None if 甲 is None or 乙 is None else 甲 - 乙))
        行们.append(行)
    总们 = [_合计总(s["索引"], 类们, 区们) for s in 显示们]
    合计行 = ["**合计**"] + [f"**{_数格(v)}**" for v in 总们]
    if 要变化:
        甲, 乙 = _合计总(末, 类们, 区们), (None if 初 is None else _合计总(初["索引"], 类们, 区们))
        合计行.append(f"**{_格(None if 甲 is None or 乙 is None else 甲 - 乙)}**")
    行们.append(合计行)
    return 列名, 行们


def _今天各次(类们, 区们, 列们, 今天字, 最多列=6):
    """返回 (今天各次, 全部各次)。列们 已按时间从早到晚，最后一个必须是这次。
    今天各次最多 6 列（第一次 + 最近 5 次）；全部各次不限列，只给 Excel 用。"""
    if not 列们:
        return {}, {}
    全部列名, 全部行们 = _今天表(类们, 区们, 列们, 列们, 今天字)
    总次 = len(列们)
    显示们, 灰字 = 列们, None
    if 总次 > 最多列:
        显示们 = [列们[0]] + 列们[-(最多列 - 1):]
        灰字 = f"今天一共运行了 {总次} 次，中间 {总次 - 最多列} 次没列出来；Excel 里有全部"
    列名, 行们 = _今天表(类们, 区们, 列们, 显示们, 今天字)
    今天 = {"次数": 总次, "列名": 列名, "行们": 行们}
    if 灰字:
        今天["灰字"] = 灰字
    elif 总次 == 1:
        今天["灰字"] = "今天只运行了一次，再运行一次就能看到变化"
    return 今天, {"次数": 总次, "列名": 全部列名, "行们": 全部行们}


# ---------------- 无日期模块（无任务包裹）：只有区、没有日期 ----------------

def _比较无日期(组名, 类们, 区们, 这次索引, 上次):
    """列 = 区域 | 上次 | 这次 | 变化；行 = 各区 + 合计。返回 ([(视图名, 列名, 行们)], [提示们])。"""
    上次索引 = 上次["索引"] if 上次 is not None else None
    提示们 = {}
    行们 = []
    for 区 in 区们:
        甲 = _合计(这次索引, 类们, 区)
        乙 = _合计(上次索引, 类们, 区) if 上次索引 is not None else None
        行们.append([区, _数格(乙), _数格(甲), _格(None if 甲 is None or 乙 is None else 甲 - 乙)])
        if 上次索引 is not None:
            提示们[f"{区}|变化"] = (f"{区}：这次没查到，没法比" if 甲 is None or 乙 is None
                                 else f"{区}：上次 {乙} → 这次 {甲}（{_格(甲 - 乙)}）")
    甲 = _合计总(这次索引, 类们, 区们)
    乙 = _合计总(上次索引, 类们, 区们) if 上次索引 is not None else None
    行们.append(["**合计**", f"**{_数格(乙)}**", f"**{_数格(甲)}**",
               f"**{_格(None if 甲 is None or 乙 is None else 甲 - 乙)}**"])
    return [("合计", ["区域", "上次", "这次", "变化"], 行们)], [提示们]


def _摘要无日期(组名, 类们, 区们, 这次索引, 上次, 今天字):
    上次索引 = 上次["索引"]
    标签 = _标签(上次["时间"], date.fromisoformat(今天字))
    甲 = _合计总(这次索引, 类们, 区们)
    乙 = _合计总(上次索引, 类们, 区们)
    if 甲 is None or 乙 is None:
        return f"{组名}：这次有区没查到，没法和上次比"
    if 甲 == 乙:
        return f"{组名}和上次（{标签}）一样，{甲} 个"
    return f"{组名}比上次（{标签}）{'多' if 甲 > 乙 else '少'} {abs(甲 - 乙)} 个"


def _今天各次无日期(类们, 区们, 列们, 今天字, 最多列=6):
    """无日期模块的「今天各次」：行 = 各区，列 = 各次时间（+ 今天变化）。返回 (今天各次, 全部各次)。"""
    if not 列们:
        return {}, {}
    要变化 = len(列们) > 1
    初 = next((s for s in 列们 if _全查到(s["索引"], 类们, 区们)), None)

    def 表(显):
        列名 = ["区域"] + _时刻名们(列们, 显) + (["今天变化"] if 要变化 else [])
        行们 = []
        for 区 in 区们:
            行 = [区] + [_数格(_合计(s["索引"], 类们, 区)) for s in 显]
            if 要变化:
                甲 = _合计(显[-1]["索引"], 类们, 区)
                乙 = None if 初 is None else _合计(初["索引"], 类们, 区)
                行.append(_格(None if 甲 is None or 乙 is None else 甲 - 乙))
            行们.append(行)
        合计行 = ["**合计**"] + [f"**{_数格(_合计总(s["索引"], 类们, 区们))}**" for s in 显]
        if 要变化:
            甲 = _合计总(显[-1]["索引"], 类们, 区们)
            乙 = None if 初 is None else _合计总(初["索引"], 类们, 区们)
            合计行.append(f"**{_格(None if 甲 is None or 乙 is None else 甲 - 乙)}**")
        行们.append(合计行)
        return 列名, 行们

    总次 = len(列们)
    显, 灰字 = 列们, None
    if 总次 > 最多列:
        显 = [列们[0]] + 列们[-(最多列 - 1):]
        灰字 = f"今天一共运行了 {总次} 次，中间 {总次 - 最多列} 次没列出来；Excel 里有全部"
    列名, 行们 = 表(显)
    今天 = {"次数": 总次, "列名": 列名, "行们": 行们}
    if 灰字:
        今天["灰字"] = 灰字
    elif 总次 == 1:
        今天["灰字"] = "今天只运行了一次，再运行一次就能看到变化"
    全列名, 全行们 = 表(列们)
    return 今天, {"次数": 总次, "列名": 全列名, "行们": 全行们}


# ---------------- 流程一览（方案 §4.6，只对待审核 / 待拣货 / 待增值） ----------------

def _组格(快照, 组名):
    """这份快照里有没有这个组：有就返回 (区们, 类们)，没有返回 ([], [])。"""
    for 名, 区们 in 快照.get("组们") or []:
        if 名 == 组名:
            类们 = list(dict.fromkeys(类 for (区, 类) in 快照["索引"] if 区 in 区们))
            return list(区们), (类们 or [""])
    return [], []


def _流程(模块名, 组名区们, 这次折, 记录, 今天字):
    """每组一张「流程一览」：三行固定 待审核 → 待拣货 → 待增值，只并排看，不做加减核对。"""
    列名 = ["环节", "最近一次", "之前日期的", "今天的", "合计", "比今天第一次"]
    出 = []
    for 组名, _ in 组名区们:
        行们 = []
        for 名 in 流程环节:
            候选 = _读模块(名, 记录, 今天字=今天字)
            if 名 == 模块名:
                候选 = [s for s in 候选 if s["时间"] < 这次折["时间"]]
                候选.append(这次折)
            候选.sort(key=lambda s: s["时间"])
            好们 = []
            for s in 候选:
                区们, 类们 = _组格(s, 组名)
                if 区们 and _全查到(s["索引"], 类们, 区们):
                    好们.append((s, 区们, 类们))
            行首 = 模块参数.显示名(名) + ("（本页）" if 名 == 模块名 else "")
            if not 好们:
                行们.append([行首, "今天还没查", "—", "—", "—", "—"])
                continue
            末, 区们, 类们 = 好们[-1]
            总 = _合计总(末["索引"], 类们, 区们)
            今 = _列(末["索引"], 类们, 区们, 今天字)
            之 = None if 总 is None or 今 is None else 总 - 今
            初总 = _合计总(好们[0][0]["索引"], 类们, 区们)
            比 = 0 if len(好们) == 1 else (None if 总 is None or 初总 is None else 总 - 初总)
            行们.append([行首, f"{末['时间']:%H:%M}", _数格(之), _数格(今), _数格(总), _格(比)])
        出.append({"组": 组名, "列名": 列名, "行们": 行们})
    return 出


# ---------------- 选“上次”（方案 §4.2） ----------------

def _选上次(旧们, 类们, 区们):
    """同模块、时间最新、且这一组这次要比的每个 类×区 在那份里都“查到”。找不到 → None（按首次处理）。
    查询范围改过（例如上次只查了瑞江）时，别的组照常比。"""
    for 快照 in 旧们:            # 已经按时间从新到旧
        if _全查到(快照["索引"], 类们, 区们):
            return 快照
    return None


# ---------------- 对外主函数 ----------------

def 算变化(模块名, 结果, 格们, 记录=None):
    """算这次和上次的变化。返回 (变化 dict, 快照行 dict)：
    一个“查到”的格都没有（登录失败、还没开始查就出错）→ (None, None)：不记快照、不算变化。
    变化 里只有排好的字符串（要进 上次结果.json，必须是纯 JSON，不能出现 date / datetime）。"""
    日期框, 格们 = _拆(格们)
    if not any(isinstance(g, dict) and g.get("查到") for g in 格们):
        _记(记录, "这次一个格都没查到：不记快照、不算变化")
        return None, None
    快照行 = _行(模块名, 结果, 日期框, 格们, 记录)
    现在 = datetime.fromisoformat(快照行["时间"])
    今天字 = 快照行["日期"]
    这次索引 = _索(快照行)
    有日期 = any(isinstance(g.get("天"), dict) for g in 格们)
    旧们 = _读模块(模块名, 记录, 早于=现在)
    今天们 = [s for s in _读模块(模块名, 记录, 今天字=今天字) if s["时间"] <= 现在]
    今天们.sort(key=lambda s: s["时间"])
    这次折 = {"时间": 现在, "日期": 今天字, "索引": 这次索引, "组们": 快照行["组们"]}
    变化 = {"版本": 版本, "摘要": "", "组们": [], "流程": []}
    句们 = []
    for 组名, 区们 in 快照行["组们"]:
        区们 = list(区们)
        类们 = list(dict.fromkeys(类 for (区, 类) in 这次索引 if 区 in 区们)) or [""]
        上次 = _选上次(旧们, 类们, 区们)
        组 = {"名": 组名, "上次标签": None, "标题": "", "空状态": None,
              "比较": {}, "今天各次": {}, "全部各次": {}, "灰字": None}
        if 上次 is None:
            组["空状态"] = "下次运行后就能比较"
            句们.append(f"{组名}：这是第一次记录，下次运行后就能比较")
        else:
            标签 = _标签(上次["时间"], date.fromisoformat(今天字))
            组["上次标签"] = 标签
            组["标题"] = f"上次 {标签} → 这次 {_标签(现在, 上次['时间'].date())}"
            if 有日期:
                if len(类们) > 1:
                    视图类们们 = [("合计", 类们)] + [(类, [类]) for 类 in 类们]
                else:
                    视图类们们 = [("合计", 类们)]
                视图们, 提示们们 = _比较(组名, 区们, 视图类们们, 这次索引, 上次, 今天字)
                组["比较"] = {"视图们": 视图们, "提示们": 提示们们}
                组["灰字"] = _灰字(模块名, 日期框, 类们, 区们, 这次索引, 上次, 今天字)
                句们.append(_摘要(组名, 类们, 区们, 这次索引, 上次, 今天字))
            else:
                视图们, 提示们们 = _比较无日期(组名, 类们, 区们, 这次索引, 上次)
                组["比较"] = {"视图们": 视图们, "提示们": 提示们们}
                句们.append(_摘要无日期(组名, 类们, 区们, 这次索引, 上次, 今天字))
        列们 = [s for s in 今天们 if _全在(s["索引"], 类们, 区们)]
        列们.append(这次折)
        列们.sort(key=lambda s: s["时间"])
        if 有日期:
            组["今天各次"], 组["全部各次"] = _今天各次(类们, 区们, 列们, 今天字)
        else:
            组["今天各次"], 组["全部各次"] = _今天各次无日期(类们, 区们, 列们, 今天字)
        变化["组们"].append(组)
    变化["摘要"] = "；".join(句们)
    if 模块名 in 流程环节:
        变化["流程"] = _流程(模块名, 快照行["组们"], 这次折, 记录, 今天字)
    return 变化, 快照行


# ---------------- 追加 Excel 两张表（方案 §5.5） ----------------

def _写块(表, 标题, 列名, 行们, 灰字=None):
    """在一个工作表里追加一块：标题（加粗 13px）→ 空行 → 表头（加粗 + 灰底）→ 行（合计行加粗）→ 灰字。"""
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    表.append([标题])
    表.cell(表.max_row, 1).font = Font(bold=True, size=13)
    表.append([])
    表.append(list(列名))
    for 格 in 表[表.max_row]:
        格.font = Font(bold=True)
        格.fill = PatternFill("solid", fgColor="DDDDDD")
        格.alignment = Alignment(horizontal="center")
    for 行 in 行们:
        表.append([_去粗(x) for x in 行])
        if str(行[0]).startswith("**"):
            for 格 in 表[表.max_row]:
                格.font = Font(bold=True)
    if 灰字:
        表.append([])
        表.append([灰字])
    for i, 名 in enumerate(列名, 1):
        表.column_dimensions[get_column_letter(i)].width = max(8, min(40, len(str(名)) * 2 + 4))
    表.append([])


def 追Excel(附件, 变化, 记录=None):
    """在原来的 Excel 里追加「和上次比」「今天各次」两张表（今天各次列今天全部次数），
    原来的表一格不动。附件不存在 / 存不进去 → 只写一行日志，不影响别的。"""
    if not 附件 or not 变化:
        return
    try:
        from openpyxl import load_workbook
        簿 = load_workbook(附件)
    except Exception as e:
        _记(记录, f"Excel 追加变化表没成功：{type(e).__name__}: {e}")
        return
    try:
        from openpyxl.styles import Font
        for 名 in ("和上次比", "今天各次"):
            if 名 in 簿.sheetnames:
                del 簿[名]
        比表 = 簿.create_sheet("和上次比")
        for 组 in 变化.get("组们") or []:
            比 = 组.get("比较") or {}
            if not 比.get("视图们"):
                比表.append([f"{组.get('名', '')}：{组.get('空状态') or '这次没有可比较的数'}"])
                比表.cell(比表.max_row, 1).font = Font(bold=True, size=13)
                continue
            for 视图名, 列名, 行们 in 比["视图们"]:
                标题 = f"{组.get('名', '')} · {组.get('标题') or ''} · {视图名}".strip(" ·")
                _写块(比表, 标题, 列名, 行们, 组.get("灰字"))
        各次表 = 簿.create_sheet("今天各次")
        for 组 in 变化.get("组们") or []:
            各 = 组.get("全部各次") or {}
            if not 各.get("列名"):
                continue
            _写块(各次表, f"{组.get('名', '')} · 今天 {各.get('次数', 1)} 次（全部）", 各["列名"], 各.get("行们") or [])
            灰 = ((组.get("今天各次") or {}).get("灰字"))
            if 灰:
                各次表.append([灰])
                各次表.append([])
        簿.save(附件)
    except Exception as e:
        _记(记录, f"Excel 追加变化表没成功：{type(e).__name__}: {e}")
