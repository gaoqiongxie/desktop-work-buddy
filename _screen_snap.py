# -*- coding: utf-8 -*-
"""全屏截图（BitBlt 屏幕 DC），用于验证全屏烟花层。"""
import sys, time
import ctypes
from ctypes import wintypes
import ctypes.wintypes as wt
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0
out = sys.argv[2] if len(sys.argv) > 2 else 'fullscreen_snap.png'
if delay:
    time.sleep(delay)

w = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
h = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
x0 = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
y0 = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
print(f'virtual screen: {w}x{h} at {x0},{y0}')

hdc = user32.GetDC(None)
hdc_mem = gdi32.CreateCompatibleDC(hdc)
hbmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
old = gdi32.SelectObject(hdc_mem, hbmp)
gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc, x0, y0, 0x00CC0020)  # SRCCOPY
gdi32.SelectObject(hdc_mem, old)

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', wt.DWORD), ('biWidth', wt.LONG), ('biHeight', wt.LONG),
                ('biPlanes', wt.WORD), ('biBitCount', wt.WORD),
                ('biCompression', wt.DWORD), ('biSizeImage', wt.DWORD),
                ('biXPelsPerMeter', wt.LONG), ('biYPelsPerMeter', wt.LONG),
                ('biClrUsed', wt.DWORD), ('biClrImportant', wt.DWORD)]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wt.DWORD)]

bmi = BITMAPINFO()
bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bmi.bmiHeader.biWidth = w
bmi.bmiHeader.biHeight = -h
bmi.bmiHeader.biPlanes = 1
bmi.bmiHeader.biBitCount = 32
buf = (ctypes.c_ubyte * (w * h * 4))()
gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)

gdi32.DeleteObject(hbmp)
gdi32.DeleteDC(hdc_mem)
user32.ReleaseDC(None, hdc)

img = Image.frombytes('RGBA', (w, h), bytes(buf), 'raw', 'BGRA')
img.save(out)
print('saved', out)
