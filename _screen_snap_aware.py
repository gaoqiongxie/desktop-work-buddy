# -*- coding: utf-8 -*-
"""DPI 感知全屏截图：看用户真实所见（含分层窗口）。"""
import sys, time
import ctypes
import ctypes.wintypes as wt
from PIL import Image

delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0
out = sys.argv[2] if len(sys.argv) > 2 else 'aware_snap.png'
if delay:
    time.sleep(delay)
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()
w = user32.GetSystemMetrics(78); h = user32.GetSystemMetrics(79)
x0 = user32.GetSystemMetrics(76); y0 = user32.GetSystemMetrics(77)
hdc = user32.GetDC(None)
hmem = gdi32.CreateCompatibleDC(hdc)
hbmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
old = gdi32.SelectObject(hmem, hbmp)
gdi32.BitBlt(hmem, 0, 0, w, h, hdc, x0, y0, 0xCC0020)
gdi32.SelectObject(hmem, old)

class H(ctypes.Structure):
    _fields_ = [('biSize', wt.DWORD), ('biWidth', wt.LONG), ('biHeight', wt.LONG),
                ('biPlanes', wt.WORD), ('biBitCount', wt.WORD),
                ('biCompression', wt.DWORD), ('biSizeImage', wt.DWORD),
                ('biX', wt.LONG), ('biY', wt.LONG),
                ('biClrU', wt.DWORD), ('biClrI', wt.DWORD)]
class B(ctypes.Structure):
    _fields_ = [('h', H), ('c', wt.DWORD)]
bmi = B(); bmi.h.biSize = 40; bmi.h.biWidth = w; bmi.h.biHeight = -h
bmi.h.biPlanes = 1; bmi.h.biBitCount = 32
buf = (ctypes.c_ubyte * (w * h * 4))()
gdi32.GetDIBits(hmem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)
Image.frombytes('RGBA', (w, h), bytes(buf), 'raw', 'BGRA').save(out)
print('saved', out)
