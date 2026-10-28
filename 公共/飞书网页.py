# 职责：飞书网页版“任务 → 我负责的”的只读操作，所有飞书任务类模块共用：
#   打开列表、按顺序读全部标题、用网址打开一条任务、读描述和评论。
# 规则（小柒 2026-10-24 确认）：
#   - 只用网址打开页面；不点击、不打字、不按键。列表很长时只用鼠标滚轮往下滚。
#   - 遇到登录页、验证码、“访问频繁”之类的提示，或页面跳到了没预料的地方：立刻停下报错，绝不绕过。
#   - 页面加载慢：允许再打开一次；还不行就报错。
#   - 不伪装浏览器，照常运行。
# 输出：都是普通的 Python 数据（列表、字典），解析和出表在各模块里做。
import re
import time

from 公共.错误 import 自动化错误, 需要登录飞书, 飞书异常, 网络超时, 页面改版, 归类, 浏览器被关, 网络断开

任务列表网址 = "https://firstjoy.feishu.cn/next/task/my-tasks"
飞书登录网址 = "https://www.feishu.cn/messenger/"
异常词 = ("验证码", "安全验证", "人机验证", "访问频繁", "操作频繁", "请求过于频繁", "访问过于频繁", "异常访问", "请完成验证", "账号存在风险")

_检查JS = r"""(词们) => {
  const 看得见 = e => { const r = e.getBoundingClientRect(); return r.width > 2 && r.height > 2; };
  for (const f of document.querySelectorAll('iframe')) {
    if (/captcha|verify/i.test(f.src || '') && 看得见(f)) return '页面弹出了验证（验证码）窗口';
  }
  const 框们 = document.querySelectorAll('[role=dialog],[role=alertdialog],[class*=modal],[class*=Modal],[class*=toast],[class*=Toast],[class*=message],[class*=captcha],[class*=verify]');
  for (const e of 框们) {
    if (!看得见(e)) continue;
    const t = (e.innerText || '').slice(0, 300);
    for (const 词 of 词们) if (t.includes(词)) return '页面提示：' + t.replace(/\s+/g, ' ').slice(0, 80);
  }
  return '';
}"""

_分组JS = r"""() => {
  const 结果 = [];
  for (const s of document.querySelectorAll('svg[data-icon^="Expand"]')) {
    if (s.closest('[role=task-table-row]')) continue;
    let 头 = s.closest('span'); 头 = 头 && 头.parentElement && 头.parentElement.parentElement;
    if (!头) continue;
    const 字 = (头.innerText || '').trim().split(/\s*\n\s*/);
    if (字.length >= 2 && /^\d+$/.test(字[1])) 结果.push([字[0], parseInt(字[1]), 头.getBoundingClientRect().top]);
  }
  return 结果;
}"""

_行JS = r"""() => [...document.querySelectorAll('[role=task-table-row]')].map(e => {
  const 清 = s => (s || '').replace(/[​﻿]/g, '').replace(/ /g, ' ').replace(/\s+/g, ' ').trim();
  const 片 = e.querySelector('.rich-text-inline');
  let 标题 = 片 ? 清(片.parentElement.textContent) : 清((e.innerText || '').split('\n')[0]);
  const 图标 = e.querySelector('svg[data-icon="AddCommentOutlined"]');
  let 评论 = null;
  if (图标) { let d = 图标.closest('div'); const m = (d ? d.textContent : '').match(/\d+\+?/); 评论 = m ? m[0] : null; }
  return [e.getAttribute('data-row-id'), e.getBoundingClientRect().top, parseInt(e.getAttribute('data-row-depth') || '1'), 标题, 评论];
})"""

_筛选JS = r"""() => {
  for (const s of document.querySelectorAll('span')) {
    const t = (s.innerText || '').trim();
    if (['未完成', '已完成', '全部任务'].includes(t) && !s.closest('a') && !s.closest('[role=menu],[role=listbox],[class*=dropdown],[class*=popover]')) {
      const r = s.getBoundingClientRect(); if (r.width > 2) return t;
    }
  }
  return null;
}"""

_详情JS = r"""() => {
  const 清 = s => (s || '').replace(/[​﻿]/g, '').replace(/ /g, ' ');
  const 描述框 = [...document.querySelectorAll('.task-limit-height')].find(e => e.querySelector('.ace-line'));
  const 描述行 = 描述框 ? [...描述框.querySelectorAll('.ace-line')].map(e => 清(e.innerText).replace(/\n+$/, '')) : [];
  const 描述图片 = 描述框 ? 描述框.querySelectorAll('img').length : 0;
  const 标题框 = [...document.querySelectorAll('.zone-container')].find(z => !z.closest('.task-limit-height') && !z.closest('[role=task-table-row]'));
  const 标题 = 标题框 ? 清(标题框.innerText).replace(/\s+/g, ' ').trim() : null;
  const h1 = [...document.querySelectorAll('h1')].find(e => e.innerText.trim() === '评论');
  let 评论 = null, 有更早 = false;
  if (h1) {
    const 区 = h1.parentElement;
    有更早 = (区.innerText || '').includes('显示更早的评论');
    评论 = [...区.querySelectorAll('.task-limit-height')].map(框 => {
      const 头 = 框.parentElement;
      const 名时 = 头 ? [...头.querySelectorAll(':scope > div > span')].map(s => 清(s.innerText).trim()).filter(Boolean) : [];
      return {人: 名时[0] || '', 时间: 名时[1] || '', 文: 清(框.innerText).trim(),
              图: 框.querySelectorAll('img:not(.larkw-emoji__img)').length};
    });
  }
  return {描述行, 描述图片, 标题, 评论, 有更早, 有评论区: !!h1, 有描述框: !!描述框};
}"""


def 不加载图片(页面):
    """图片、字体、视频不下载（我们只要文字）。返回一个函数，调用它就恢复。"""
    def 拦(route):
        if route.request.resource_type in ("image", "font", "media"):
            return route.abort()
        return route.continue_()
    页面.route("**/*", 拦)
    return lambda: 页面.unroute("**/*", 拦)


def 检查异常(页面, 应在网址=任务列表网址):
    """登录页、验证码、访问频繁、跳到别处：立刻报错。"""
    网址 = 页面.url
    if any(k in 网址 for k in ("accounts.feishu.cn", "passport.feishu.cn", "/login", "/accounts/page")):
        raise 自动化错误(需要登录飞书, "飞书网页版没有登录（或登录已过期），打开后跳到了登录页。")
    if not 网址.startswith(应在网址):
        raise 自动化错误(飞书异常, f"页面跳到了没预料的地方：{网址[:120]}")
    提示 = 页面.evaluate(_检查JS, list(异常词))
    if 提示:
        raise 自动化错误(飞书异常, 提示)


def _等(页面, 条件, 秒, 应在网址=任务列表网址):
    """每 0.5 秒检查一次异常和条件，条件满足返回 True，超时返回 False。"""
    到 = time.time() + 秒
    while time.time() < 到:
        检查异常(页面, 应在网址)
        if 条件():
            return True
        页面.wait_for_timeout(500)
    检查异常(页面, 应在网址)
    return False


def _打不开(e, 说):
    """打不开网页时如实说原因，只用中文；英文原文写进日志（体检 2026-10-28）。"""
    e2 = 归类(e)
    if e2.类型 == 浏览器被关:
        return e2
    if e2.类型 == 网络断开:
        return 自动化错误(网络断开, f"{说}：{e2.原因}")
    return 自动化错误(网络超时, f"{说}（两次各等了 60 秒，网速慢、网络断了或电脑睡着了）。")


def 打开列表(页面, 记录=None):
    """用网址打开“我负责的”，等任务行出现（或分组显示 0 条）。慢就再开一次。"""
    for 第几次 in (1, 2):
        try:
            页面.goto(任务列表网址, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            if 第几次 == 2:
                raise _打不开(e, "打不开飞书任务页面")
            continue
        if _等(页面, lambda: 页面.locator("[role=task-table-row]").count() > 0
               or (页面.evaluate(_分组JS) and all(n == 0 for _, n, _ in 页面.evaluate(_分组JS))), 60):
            页面.wait_for_timeout(1500)
            return
        if 记录:
            记录.写("    任务列表 60 秒没显示出来，再打开一次")
    raise 自动化错误(网络超时, "飞书任务列表打开两次都没有显示出来（每次等 60 秒）。")


def 读全部标题(页面, 记录=None):
    """按页面顺序读全部任务行（只读第一层任务，不含展开的子任务）。
    返回 {行们: [(编号, 标题, 评论数)], 分组: [(名, 条数)], 应有: 合计条数或 None, 筛选: “未完成”等}"""
    分组 = sorted(页面.evaluate(_分组JS), key=lambda x: x[2])
    分组 = [(名, n) for 名, n, _ in 分组]
    应有 = sum(n for _, n in 分组) if 分组 else None
    筛选 = 页面.evaluate(_筛选JS)
    行们, 已见 = [], set()

    def 收():
        新 = 0
        for 编号, _, 层, 标题, 评论 in sorted(页面.evaluate(_行JS), key=lambda x: x[1]):
            if 层 == 1 and 编号 and 编号 not in 已见:
                已见.add(编号)
                行们.append((编号, 标题, 评论))
                新 += 1
        return 新

    if 页面.locator("[role=task-table-row]").count() == 0:
        return {"行们": [], "分组": 分组, "应有": 应有, "筛选": 筛选}
    # 鼠标停在第一条可见的任务上（只停留，不点），再用滚轮先滚到顶、再一路往下
    视口高 = 页面.viewport_size["height"] if 页面.viewport_size else 800
    可见 = [b for e in 页面.locator("[role=task-table-row]").all()
          if (b := e.bounding_box()) and 0 < b["y"] < 视口高 - 60]
    if not 可见:
        raise 自动化错误(页面改版, "任务列表里找不到能放鼠标的位置（看不到任务行）。")
    页面.mouse.move(可见[0]["x"] + 300, 可见[0]["y"] + 10)
    for _ in range(20):
        页面.mouse.wheel(0, -1000)
        页面.wait_for_timeout(100)
    页面.wait_for_timeout(600)
    收()
    不变 = 0
    for _ in range(200):
        页面.mouse.wheel(0, 400)
        页面.wait_for_timeout(400)
        不变 = 0 if 收() else 不变 + 1
        if 不变 >= 5:
            break
    if 记录:
        记录.写(f"    读到 {len(行们)} 条；分组显示：" + ("、".join(f"{名} {n}" for 名, n in 分组) or "读不到"))
    return {"行们": 行们, "分组": 分组, "应有": 应有, "筛选": 筛选}


def 读任务(页面, 编号, 记录=None):
    """用网址打开一条任务的详情，读标题、描述每一行、评论。慢就再开一次。"""
    网址 = f"{任务列表网址}?task={编号}"
    for 第几次 in (1, 2):
        try:
            页面.goto(网址, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            if 第几次 == 2:
                raise _打不开(e, "打不开这条任务")
            continue
        if _等(页面, lambda: 页面.evaluate(_详情JS)["有评论区"], 40):
            页面.wait_for_timeout(1200)
            详情 = 页面.evaluate(_详情JS)
            if not 详情["有描述框"]:          # 描述有时比评论区晚一点出来
                页面.wait_for_timeout(2500)
                详情 = 页面.evaluate(_详情JS)
            if f"task={编号}" not in 页面.url:
                raise 自动化错误(飞书异常, f"打开任务后网址变了：{页面.url[:120]}")
            return 详情
        if 记录:
            记录.写("    这条任务 40 秒没打开，再打开一次")
    raise 自动化错误(网络超时, "这条任务打开两次都没有显示出来（每次等 40 秒）。")
