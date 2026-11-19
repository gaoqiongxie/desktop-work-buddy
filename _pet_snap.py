# -*- coding: utf-8 -*-
"""截图验证：PrintWindow flags=2，python 与宠物同为 DPI 非感知，坐标系天然一致"""
import ctypes
from ctypes import wintypes
import sys

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

user32.FindWindowW.restype = wintypes.HWND
hwnd = user32.FindWindowW(None, '上班搭子')
if not hwnd:
    # 按进程找主窗口兜底
    import subprocess
    print('FindWindow failed'); sys.exit(1)

class RECT(ctypes.Structure):
    _fields_ = [('l', wintypes.LONG), ('t', wintypes.LONG),
                ('r', wintypes.LONG), ('b', wintypes.LONG)]
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
w, h = rect.r - rect.l, rect.b - rect.t
print(f'window {w}x{h} at {rect.l},{rect.t}')

hdc_win = user32.GetWindowDC(hwnd)
hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
hbmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
gdi32.SelectObject(hdc_mem, hbmp)
PW_RENDERFULLCONTENT = 2
ok = user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)
print('PrintWindow:', ok)

# GetDIBits BGRA
class BMIH(ctypes.Structure):
    _fields_ = [('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG), ('biHeight', wintypes.LONG),
                ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD),
                ('biCompression', wintypes.DWORD), ('biSizeImage', wintypes.DWORD),
                ('biXPels', wintypes.LONG), ('biYPels', wintypes.LONG),
                ('biClrUsed', wintypes.DWORD), ('biClrImportant', wintypes.DWORD)]
class BMI(ctypes.Structure):
    _fields_ = [('h', BMIH), ('colors', wintypes.DWORD)]
bmi = BMI()
bmi.h.biSize = 40
bmi.h.biWidth = w
bmi.h.biHeight = -h
bmi.h.biPlanes = 1
bmi.h.biBitCount = 32
buf = (ctypes.c_ubyte * (w * h * 4))()
gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)

# 统计非零像素
nonzero = sum(1 for i in range(0, len(buf), 997) if buf[i] or buf[i+1] or buf[i+2])
print('sampled nonzero px:', nonzero)
# BGRA -> 保存 PNG（优先 PIL，无则写原始 BMP）
out = sys.argv[1] if len(sys.argv) > 1 else 'buddy_pw_py.png'
try:
    from PIL import Image
    img = Image.frombytes('RGBA', (w, h), bytes(buf), 'raw', 'BGRA')
    # biHeight 为负，GetDIBits 已返回自上而下的行，无需翻转
    img.save(out)
    print('saved via PIL ->', out)
except ImportError:
    print('no PIL, raw stats only')
