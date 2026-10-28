# 职责：运行期间告诉 Windows“正在忙，别自动睡眠、别自动关屏”（体检 2026-10-28：两次失败都是跑到一半电脑进入待机）。
# 用的是 Windows 官方接口 SetThreadExecutionState：
#   https://learn.microsoft.com/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate
# 说明：
#   - 只在仓库助手运行查询时有效，跑完（或出错）马上恢复；不改系统的电源设置。
#   - 这个请求跟着“调用它的线程”走，所以开和关要在同一个线程里（运行模块们 整个都在后台线程里跑）。
#   - 合盖、按电源键还是会睡，挡不住——所以窗口顶部会提醒“运行中请勿合盖”。
import ctypes
import sys
from contextlib import contextmanager

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


def _设(标志):
    if sys.platform != "win32":
        return 0
    try:
        return ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint(标志))
    except Exception:
        return 0


def 开始():
    """返回 True = Windows 接受了请求。"""
    return _设(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED) != 0


def 恢复():
    _设(ES_CONTINUOUS)


@contextmanager
def 运行中不睡眠():
    """用法：with 运行中不睡眠() as 好: ……  结束或出错时一定恢复。"""
    好 = 开始()
    try:
        yield 好
    finally:
        恢复()
