# 职责：发飞书群机器人消息。所有模块共用。
# 输入：消息文字。设置从 密钥.env 读取（飞书Webhook、飞书关键词、飞书已测通）。
# 输出：(状态, 说明)  状态 = 成功 / 失败 / 未知
#   - 成功：飞书返回 code=0
#   - 失败：飞书明确拒绝（例如关键词不对），说明里写原因
#   - 未知：超时或断网，不知道发没发出去——不会自动重发，请到群里看一眼
# 安全：Webhook 地址只存在 密钥.env，绝不打印、不写日志。
import json
import socket
import urllib.error
import urllib.request
from pathlib import Path

根目录 = Path(__file__).resolve().parent.parent
密钥文件 = 根目录 / "密钥.env"

_错误码说明 = {
    19024: "消息里没有机器人的自定义关键词（关键词不对）",
    19021: "签名校验失败（机器人开了“签名校验”，本程序暂不支持）",
    19022: "IP 不在白名单（机器人开了“IP 白名单”）",
    9499: "消息格式不对",
    11232: "发送太频繁，被飞书限流",
    19001: "Webhook 地址无效（可能机器人已被删除）",
}


def 读设置():
    设置 = {}
    if 密钥文件.exists():
        for 行 in 密钥文件.read_text(encoding="utf-8").splitlines():
            if "=" in 行 and not 行.strip().startswith("#"):
                键, 值 = 行.split("=", 1)
                设置[键.strip()] = 值.strip()
    return 设置


def 写设置(新设置):
    设置 = 读设置()
    设置.update(新设置)
    文字 = "# 自动化用的密钥和设置。不要发给别人，不要发在聊天里。\n"
    文字 += "".join(f"{键}={值}\n" for 键, 值 in 设置.items())
    密钥文件.write_text(文字, encoding="utf-8")


def 可以发送():
    """设置飞书.bat 测试成功后才会自动发送。"""
    设置 = 读设置()
    return bool(设置.get("飞书Webhook")) and 设置.get("飞书已测通") == "是"


def 发送(消息, 网址=None, 关键词=None, 超时秒=10):
    设置 = 读设置()
    网址 = 网址 or 设置.get("飞书Webhook", "")
    关键词 = 设置.get("飞书关键词", "") if 关键词 is None else 关键词
    if not 网址:
        return "失败", "还没有设置飞书：请双击 设置飞书.bat"
    if 关键词 and 关键词 not in 消息:
        消息 = f"{消息}\n—— {关键词}"
    数据 = json.dumps({"msg_type": "text", "content": {"text": 消息}}, ensure_ascii=False).encode("utf-8")
    请求 = urllib.request.Request(网址, data=数据, headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(请求, timeout=超时秒) as 回应:
            内容 = 回应.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            内容 = e.read().decode("utf-8", "replace")
        except Exception:
            return "失败", f"飞书返回 HTTP {e.code}"
    except (socket.timeout, TimeoutError):
        return "未知", f"{超时秒} 秒没有回应，不确定是否发出，请到飞书群里看一眼（不会自动重发）"
    except urllib.error.URLError as e:
        if isinstance(e.reason, (socket.timeout, TimeoutError)):
            return "未知", f"{超时秒} 秒没有回应，不确定是否发出，请到飞书群里看一眼（不会自动重发）"
        return "失败", f"连不上飞书（网络问题）：{e.reason}"
    except ValueError:
        return "失败", "Webhook 地址格式不对，请重新运行 设置飞书.bat"
    try:
        结果 = json.loads(内容)
    except Exception:
        return "未知", "飞书返回的内容看不懂，请到飞书群里看一眼是否收到"
    码 = 结果.get("code", 结果.get("StatusCode"))
    if 码 == 0:
        return "成功", "飞书已收到"
    原因 = _错误码说明.get(码, 结果.get("msg") or 结果.get("StatusMessage") or "未知原因")
    return "失败", f"飞书拒绝（错误码 {码}）：{原因}"
