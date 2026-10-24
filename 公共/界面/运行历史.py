# 职责：读 日志\运行总表.csv（只读），给工作台“上次结果”和“运行记录”页用。
# 总表的“模块”一列写的是显示名；改过名时写成“新名字（原名）”。这里换回原名，方便对上模块。
# 最后一列“测试”= Claude 自测的运行：运行记录页灰色显示，工作台的“上次结果”不算它（2026-10-24 起才有这一列）。
import csv
import re
from datetime import datetime

from 公共.日志 import 日志根, 总表
from 公共.模块参数 import 显示名表


def 读全部(原名们=()):
    """返回每次运行一行的列表（新的在前）：{时间, 原名, 名字, 状态, 数量, 用时, 摘要, 文件夹, 测试}。
    “主控”（一次跑多个模块时的总记录）不列。读不了文件时返回空列表。"""
    原名们 = list(原名们)
    改名 = 显示名表()
    显示名到原名 = {改名.get(名, 名): 名 for 名 in 原名们}
    行们 = []
    try:
        with open(总表, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                名 = (r.get("模块") or "").strip()
                if not 名 or 名 == "主控":
                    continue
                m = re.match(r"^(.*)（(.+)）$", 名)
                原名 = m.group(2) if m and m.group(2) in 原名们 else 名
                if 原名 not in 原名们:
                    原名 = 显示名到原名.get(名, 原名)
                try:
                    时间 = datetime.strptime(r.get("时间", ""), "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
                多出 = r.get(None) or []          # 老表头没有“测试”这一列时，值在这里
                测试 = (r.get("测试") or (多出[0] if 多出 else "")).strip() == "测试"
                行们.append({"时间": 时间, "原名": 原名, "名字": m.group(1) if m else 名, "状态": r.get("状态", ""),
                           "数量": r.get("数量", ""), "用时": r.get("用时(秒)", ""), "摘要": r.get("错误摘要", ""),
                           "文件夹": r.get("日志文件夹", ""), "测试": 测试})
    except (OSError, csv.Error):
        return []
    行们.sort(key=lambda x: x["时间"], reverse=True)
    return 行们


def 上次结果们(原名们):
    """{原名: 最近一次正式运行（不算测试）的那一行}。没运行过的模块不在里面。"""
    最近 = {}
    for 行 in 读全部(原名们):
        if not 行["测试"]:
            最近.setdefault(行["原名"], 行)
    return 最近


def 日志文件夹(行):
    return 日志根 / 行["文件夹"] if 行.get("文件夹") else None
