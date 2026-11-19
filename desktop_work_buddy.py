"""
桌面上班搭子 - 烟花筒桌面宠物
功能：随机走动、点击互动、励志语录、右键菜单、装死彩蛋、缩放、任务完成放烟花庆祝
触发：.buddy_notify 写入含「完成」的通知时，弹气泡 + 连发烟花
作者：AI Assistant
"""

import sys

try:
    import tkinter as tk
except ImportError:
    print('错误：当前 Python 环境未安装 tkinter 模块。')
    print("请使用系统安装的 Python（安装时勾选 'tcl/tk and IDLE' 选项）运行本程序。")
    print('如果是 TRAE 内置 Python，请切换到本地安装的 Python 解释器。')
    sys.exit(1)

import random
import math
import os
import ctypes

QUOTES = [
    '加油！',
    '你可以！',
    '别放弃！',
    '继续冲！',
    '你最棒！',
    '向前看！',
    '保持热爱！',
    '相信自己！',
    '越来越好！',
    '未来可期！',
    '闪闪发光！',
    '全力以赴！',
    '无所畏惧！',
    '勇往直前！',
    '元气满满！',
    '积极向上！',
    '努力发光！',
    '今日加油！',
    '心怀希望！',
    '坚持到底！',
]

# 烟花配色
FIREWORK_COLORS = [
    '#FF6B6B', '#FFD166', '#06D6A0', '#4CC9F0',
    '#F72585', '#B5179E', '#FF9E00', '#FFF75E', '#8AFF80',
]

# 通知文件：AI / bot 完成任务时写入，宠物弹出气泡 + 放烟花庆祝
# 默认监听脚本所在目录的 .buddy_notify；用环境变量 BUDDY_NOTIFY_FILES 可追加更多路径（分号分隔）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WATCH_FILES = [os.path.join(BASE_DIR, '.buddy_notify')]
_extra = os.environ.get('BUDDY_NOTIFY_FILES')
if _extra:
    WATCH_FILES += [p for p in _extra.split(';') if p]

# 位置存档：拖拽后落盘，重启从上次位置恢复（存放在脚本所在目录）
POS_FILE = os.path.join(BASE_DIR, '.buddy_pos')

# 爆炸主题清单：「随机」时每发火箭随机抽一个
BURST_THEMES = ('烟花', '金币雨', '爆米花', '鸡腿', '红包雨', '彩纸屑', '小星星',
                '表情包', '雪花', '枫叶')
# 表情包主题用的 emoji 池（Windows 下 Segoe UI Emoji 渲染彩色字形）
EMOJI_SET = ('😂', '🤣', '😎', '🥳', '😭', '😱', '🤪', '😘',
             '👍', '👏', '🙌', '🫡', '🎉', '💰', '🔥', '💩',
             '🐟', '🍗', '❤️', '💯')
EMOJI_PX = 34          # 彩色 emoji 预渲染基准边长（PIL seguiemj.ttf + embedded_color）


def _load_emoji_images():
    """把 EMOJI_SET 预渲染成彩色 PhotoImage 缓存。

    tkinter 画布 text 走 GDI 只能画单色 emoji 轮廓，必须用 PIL
    （seguiemj.ttf + embedded_color=True）预先渲染成图片再贴。
    返回 {字符: (大图, 小图)}；任何一步失败返回 {}，由调用方回退单色文本。"""
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageTk
        font_path = r'C:\Windows\Fonts\seguiemj.ttf'
        out = {}
        for ch in EMOJI_SET:
            pair = []
            for px in (EMOJI_PX, EMOJI_PX // 2 + 2):
                font = ImageFont.truetype(font_path, px)
                img = Image.new('RGBA', (px + 10, px + 10), (0, 0, 0, 0))
                dr = ImageDraw.Draw(img)
                dr.text((5, 5), ch, font=font, embedded_color=True)
                pair.append(ImageTk.PhotoImage(img))
            out[ch] = tuple(pair)
        return out
    except Exception:
        return {}

# 彩纸屑配色
CONFETTI_COLORS = ['#FF6B6B', '#FFD166', '#06D6A0', '#4CC9F0',
                   '#F72585', '#B5179E', '#FF9E00', '#8AFF80', '#C8B6FF']

DEAD_MS = 5000  # 装死持续时间


def _primary_monitor():
    """取主显示器真实矩形（多显示器布局中虚拟桌面可能包含空隙，须避免）"""
    from ctypes import wintypes as wt
    user32 = ctypes.windll.user32

    class MONITORINFO(ctypes.Structure):
        _fields_ = [('cbSize', wt.DWORD), ('rcMonitor', wt.RECT),
                    ('rcWork', wt.RECT), ('dwFlags', wt.DWORD)]

    result = []

    @ctypes.WINFUNCTYPE(wt.INT, wt.HMONITOR, wt.HDC,
                        ctypes.POINTER(wt.RECT), wt.LPARAM)
    def _cb(hmon, hdc, prc, lparam):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            result.append((mi.dwFlags, mi.rcMonitor.left, mi.rcMonitor.top,
                           mi.rcMonitor.right, mi.rcMonitor.bottom))
        return 1

    user32.EnumDisplayMonitors(None, None, _cb, 0)
    for flags, l, t, r, b in result:
        if flags & 1:  # MONITORINFOF_PRIMARY
            return l, t, r, b
    if result:
        _, l, t, r, b = result[0]
        return l, t, r, b
    return 0, 0, 1440, 900


def _load_pos():
    """读取上次保存的位置，无记录或非法返回 None"""
    try:
        with open(POS_FILE, encoding='ascii') as fh:
            x, y = (int(v) for v in fh.read().strip().split(','))
        return x, y
    except Exception:
        return None


def _clamp_to_primary(x, y, size):
    """把窗口位置夹回主显示器可见区域（防止显示器布局变化后落在屏外/空隙）"""
    pl, pt, pr, pb = _primary_monitor()
    x = max(pl, min(x, pr - size))
    y = max(pt, min(y, pb - size))
    return x, y


class DesktopBuddy:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('上班搭子')
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', 'SystemButtonFace')

        self.base_size = 120
        self.base_bubble_area = 75
        self.scale = 1.0
        self.size = int(self.base_size * self.scale)
        self.bubble_area = int(self.base_bubble_area * self.scale)
        # 烟花筒配色
        self.body_fill = '#D64545'     # 筒身红
        self.body_dark = '#8E2F2F'     # 筒身轮廓
        self.gold = '#F2C14E'          # 金色条纹/口沿
        self.gold_dark = '#B8860B'

        self.screen_w = self.root.winfo_vrootwidth()
        self.screen_h = self.root.winfo_vrootheight()
        # 出生点：优先恢复上次拖拽保存的位置，否则主显示器底部居中
        saved = _load_pos()
        if saved is not None:
            self.x, self.y = _clamp_to_primary(saved[0], saved[1], self.size)
        else:
            pl, pt, pr, pb = _primary_monitor()
            self.x = (pl + pr) // 2 - self.size // 2
            self.y = pb - self.size - 80
        self.target_x = self.x
        self.target_y = self.y

        self.speed = 2
        self.idle_chance = 0.02
        self.is_moving = False
        self.blinking = False
        self.mouth_open = False
        self.dead = False
        self.pinned = True   # 固定位置：不随机乱跑（右键菜单可解除）
        self.burst_theme = '烟花'   # 爆炸主题：烟花/金币雨/爆米花/鸡腿（右键菜单切换）

        self.bubble_id = None
        self.bubble_text_id = None
        self.triangle = None

        # 烟花状态：火箭上升中 / 爆炸粒子
        self.rockets = []
        self.sparks = []

        # 通知文件监听初始 mtime
        self.mtimes = {}
        for f in WATCH_FILES:
            try:
                self.mtimes[f] = os.path.getmtime(f)
            except OSError:
                self.mtimes[f] = None

        self.canvas = tk.Canvas(self.root,
                                width=self.size,
                                height=self.size + 40 + self.bubble_area,
                                bg='SystemButtonFace',
                                highlightthickness=0)
        self.canvas.pack()

        # 全屏烟花层：透明背景 + 点击穿透，烟花铺满整个虚拟桌面（多显示器全覆盖）
        self.fw_root = tk.Toplevel(self.root)
        self.fw_root.overrideredirect(True)
        self.fw_root.attributes('-topmost', True)
        self.fw_root.attributes('-transparentcolor', 'SystemButtonFace')
        self.fw_root.config(bg='SystemButtonFace')
        self.fw_root.geometry(f'{self.screen_w}x{self.screen_h}+0+0')
        self.fw_canvas = tk.Canvas(self.fw_root,
                                   width=self.screen_w,
                                   height=self.screen_h,
                                   bg='SystemButtonFace',
                                   highlightthickness=0)
        self.fw_canvas.pack()
        self.fw_root.update_idletasks()
        # WS_EX_TRANSPARENT：鼠标点击穿透烟花层，不挡住桌面和其他窗口
        try:
            user32 = ctypes.windll.user32
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            for hwnd in (self.fw_root.winfo_id(),
                         user32.GetParent(self.fw_root.winfo_id())):
                if hwnd:
                    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                          style | WS_EX_TRANSPARENT)
        except Exception:
            pass

        # 绘制形象
        self.draw_tube()

        # 事件绑定
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<Button-3>', self.show_menu)
        self.canvas.bind('<Enter>', self.on_hover)
        self.canvas.bind('<Leave>', self.on_leave)

        # 右键菜单
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label='放烟花庆祝', command=lambda: self.celebrate(6))
        self.menu.add_command(label='对我说句话', command=self.show_quote)
        self.menu.add_command(label='休息一下', command=self.take_break)
        self.menu.add_command(label='装死', command=self.play_dead)
        # 爆炸主题子菜单（插在装死后，注意保持下方 entryconfig 索引同步）
        self.theme_var = tk.StringVar(value=self.burst_theme)
        theme_menu = tk.Menu(self.menu, tearoff=0)
        for t in BURST_THEMES + ('随机',):
            theme_menu.add_radiobutton(label=t, variable=self.theme_var,
                                       value=t, command=self._on_theme_change)
        self.menu.add_cascade(label='🎆 爆炸主题', menu=theme_menu)
        self.menu.add_separator()
        self.menu.add_command(label='解除固定', command=self.toggle_pin)
        self.menu.add_command(label='放大', command=self.zoom_in)
        self.menu.add_command(label='缩小', command=self.zoom_out)
        self.menu.add_separator()
        self.menu.add_command(label='退出', command=self.exit_app)

        self.animate()
        self.random_blink()
        self.random_move()
        self.random_quote()
        self._tick_notify()

        self.root.geometry(
            f'{self.size}x{self.size + 40 + self.bubble_area}+{self.x}+{self.y}')
        self.root.mainloop()

    # ---------- 几何 ----------
    def _geo(self):
        """烟花筒各部位基准坐标（正常朝向，v 值为未镜像的纵向坐标）"""
        s = self.size
        off = self.bubble_area
        cx = s // 2
        y_top = off + 40            # 筒口中心 y
        y_bot = off + s + 14        # 筒底 y
        return s, off, cx, y_top, y_bot

    # ---------- 绘制 ----------
    def draw_tube(self):
        """绘制卡通烟花筒：红金筒身、筒口、引线火花、笑脸、小手小脚

        装死状态（self.dead）时整体上下镜像：筒口朝下放躺平。
        """
        s, off, cx, y_top, y_bot = self._geo()
        body = self.body_fill
        body_dark = self.body_dark
        gold = self.gold
        pink = '#F7B8C4'

        if self.dead:
            # 上下镜像：筒口朝下躺平装死
            H = s + 40 + self.bubble_area
            Y = lambda v: H - v
            EXT = -1  # 弧形角度取反（垂直镜像）
        else:
            Y = lambda v: v
            EXT = 1
        self._Y = Y
        self._EXT = EXT

        # 引线（从筒口引出，装死时自然跟着镜像到下方）
        self.canvas.create_line(cx, Y(y_top - 6), cx, Y(y_top - 20),
                                fill='#7A5230', width=2, capstyle='round')
        # 引线火花（小十字星光，动画里闪）
        self.spark_star = self.canvas.create_line(
            cx - 4, Y(y_top - 20), cx + 4, Y(y_top - 20),
            fill='#FFE66D', width=2, capstyle='round')
        self.spark_star2 = self.canvas.create_line(
            cx, Y(y_top - 24), cx, Y(y_top - 16),
            fill='#FFF3B0', width=2, capstyle='round')

        # 筒身（上窄下宽的梯形圆筒）
        self.body = self.canvas.create_polygon(
            cx - 28, Y(y_top), cx + 28, Y(y_top),
            cx + 36, Y(y_bot), cx - 36, Y(y_bot),
            fill=body, outline=body_dark, width=3, joinstyle='round')

        # 金色斜条纹（两条斜切 band）
        for yy in (y_top + 16, y_top + 40, y_top + 64):
            if yy + 10 > y_bot - 6:
                continue
            self.canvas.create_polygon(
                cx - 31, Y(yy), cx + 31, Y(yy),
                cx + 30, Y(yy + 10), cx - 30, Y(yy + 10),
                fill=gold, outline=self.gold_dark, width=1, joinstyle='round')

        # 筒口（金色口沿 + 深色炮膛）
        self.canvas.create_oval(cx - 30, Y(y_top - 9),
                                cx + 30, Y(y_top + 9),
                                fill=gold, outline=self.gold_dark, width=2)
        self.canvas.create_oval(cx - 23, Y(y_top - 6),
                                cx + 23, Y(y_top + 6),
                                fill='#4A2525', outline='')

        # 眼睛
        ey = y_top + 34
        self.eye_l = self.canvas.create_oval(cx - 22, Y(ey),
                                             cx - 8, Y(ey + 14),
                                             fill='white', outline=body_dark,
                                             width=2)
        self.eye_r = self.canvas.create_oval(cx + 8, Y(ey),
                                             cx + 22, Y(ey + 14),
                                             fill='white', outline=body_dark,
                                             width=2)
        self.pupil_l = self.canvas.create_oval(cx - 17, Y(ey + 5),
                                               cx - 11, Y(ey + 11),
                                               fill='#2B2B2B', outline='')
        self.pupil_r = self.canvas.create_oval(cx + 11, Y(ey + 5),
                                               cx + 17, Y(ey + 11),
                                               fill='#2B2B2B', outline='')
        self.lashes = []

        # 腮红
        self.canvas.create_oval(cx - 30, Y(ey + 16), cx - 20, Y(ey + 24),
                                fill=pink, outline='')
        self.canvas.create_oval(cx + 20, Y(ey + 16), cx + 30, Y(ey + 24),
                                fill=pink, outline='')

        # 嘴巴（微笑弧线；张嘴说话时用 pieslice 重绘）
        mb1 = Y(ey + 18)
        mb2 = Y(ey + 32)
        self.mouth_top = min(mb1, mb2)
        self.mouth_bottom = max(mb1, mb2)
        self.mouth_box = (cx - 12, self.mouth_top, cx + 12, self.mouth_bottom)
        self.mouth = self.canvas.create_arc(*self.mouth_box,
                                            start=0, extent=180 * EXT,
                                            style='arc', outline='#5C1F1F',
                                            width=2)

        # 小手
        self.arm_l = self.canvas.create_line(cx - 30, Y(y_top + 46),
                                             cx - 44, Y(y_top + 58),
                                             fill=body_dark, width=5,
                                             capstyle='round')
        self.arm_r = self.canvas.create_line(cx + 30, Y(y_top + 46),
                                             cx + 44, Y(y_top + 58),
                                             fill=body_dark, width=5,
                                             capstyle='round')

        # 小脚
        self.shoe_l = self.canvas.create_oval(cx - 30, Y(y_bot - 2),
                                              cx - 8, Y(y_bot + 10),
                                              fill=body_dark, outline='#5C1F1F')
        self.shoe_r = self.canvas.create_oval(cx + 8, Y(y_bot - 2),
                                              cx + 30, Y(y_bot + 10),
                                              fill=body_dark, outline='#5C1F1F')
        # 脚 leg 引用（走路摆动用）
        self.leg_l = self.arm_l  # 占位：烟花筒无腿，走路摆脚即可
        self.leg_r = self.arm_r

    def redraw(self):
        """清空并按当前状态（正常/装死）重绘"""
        self.canvas.delete('all')
        self.rockets.clear()
        self.sparks.clear()
        if hasattr(self, 'fw_canvas'):
            self.fw_canvas.delete('all')
        self.draw_tube()

    # ---------- 烟花（全屏层） ----------
    def _raise_fw(self):
        """烟花层重新置顶：Windows 会在新应用窗口激活时把全屏层压到普通窗口之下，
        发射前与动画期间周期性重设 HWND_TOPMOST 拉回最顶"""
        try:
            self.fw_root.lift()
            self.fw_root.attributes('-topmost', True)
        except Exception:
            pass
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(self.fw_root.winfo_id()) or self.fw_root.winfo_id()
            if hwnd:
                # HWND_TOPMOST=-1, SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE
                user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
        except Exception:
            pass

    def celebrate(self, n=6):
        """放烟花庆祝：连发 n 发（右键菜单与任务完成通知共用）"""
        if self.dead or n <= 0:
            return
        self._launch_rocket()
        self.root.after(random.randint(180, 450),
                        lambda: self.celebrate(n - 1))

    def _launch_rocket(self):
        """从筒口点燃一发升空火箭，飞往全屏随机顶点"""
        if self.dead:
            return
        self._raise_fw()
        s, off, cx, y_top, y_bot = self._geo()
        # 屏幕坐标：筒口正上方
        sx = self.x + cx + random.randint(-6, 6)
        sy = self.y + y_top - 20
        color = random.choice(FIREWORK_COLORS)
        rid = self.fw_canvas.create_oval(sx - 3, sy - 3, sx + 3, sy + 3,
                                         fill='#FFF6C9', outline='')
        # 爆炸顶点：主显示器内随机，保证每发都落在可见屏幕上
        pl, pt, pr, pb = _primary_monitor()
        apex_x = random.randint(pl + 60, pr - 60)
        apex_y = random.randint(pt + 60, max(pt + 120, int(pb * 0.45)))
        speed = random.uniform(11.0, 15.0)      # 每帧上升速度
        frames = max(10, int((sy - apex_y) / speed))
        vx = (apex_x - sx) / frames
        vy = -speed
        self.rockets.append({
            'id': rid, 'x': sx, 'y': sy,
            'vx': vx, 'vy': vy,
            'target_y': apex_y,
            'color': color,
        })
        # 发射后坐力：窗口快速下顿一下
        self.root.geometry(f'+{self.x}+{self.y + 5}')
        self.root.after(90,
                        lambda: self.root.geometry(f'+{self.x}+{self.y}'))

    def _explode(self, rocket):
        """火箭到顶爆炸：按当前主题生成粒子（「随机」主题每发抽签）
        一次绽放开 3~4 个爆点铺满主显示器，不再只开一个点"""
        self.fw_canvas.delete(rocket['id'])
        x, y = rocket['x'], rocket['y']
        theme = getattr(self, 'burst_theme', '烟花')
        if theme == '随机':
            theme = random.choice(BURST_THEMES)
        # 爆点散布：火箭顶点 + 主显示器内 2~3 个随机点
        pl, pt, pr, pb = _primary_monitor()
        centers = [(x, y)]
        for _ in range(random.randint(2, 3)):
            centers.append((random.randint(pl + 100, pr - 100),
                            random.randint(pt + 80, max(pt + 160,
                                                        int(pb * 0.6)))))
        for cx, cy in centers:
            self._burst_at(theme, cx, cy, rocket.get('color'))

    def _burst_at(self, theme, x, y, color=None):
        """在指定爆点按主题生成一波粒子"""
        if theme == '金币雨':
            for _ in range(random.randint(18, 26)):
                self._spawn_coin(x, y)
        elif theme == '爆米花':
            for _ in range(random.randint(22, 32)):
                self._spawn_popcorn(x, y)
        elif theme == '鸡腿':
            for _ in range(random.randint(10, 15)):
                self._spawn_drumstick(x, y)
        elif theme == '红包雨':
            for _ in range(random.randint(13, 18)):
                self._spawn_redpacket(x, y)
        elif theme == '彩纸屑':
            for _ in range(random.randint(30, 42)):
                self._spawn_confetti(x, y)
        elif theme == '小星星':
            for _ in range(random.randint(18, 26)):
                self._spawn_star(x, y)
        elif theme == '表情包':
            for _ in range(random.randint(14, 20)):
                self._spawn_emoji(x, y)
        elif theme == '雪花':
            for _ in range(random.randint(24, 34)):
                self._spawn_snowflake(x, y)
        elif theme == '枫叶':
            for _ in range(random.randint(14, 20)):
                self._spawn_mapleleaf(x, y)
        else:  # 烟花：放射状彩光粒子
            n = random.randint(32, 42)
            for i in range(n):
                ang = 2 * math.pi * i / n + random.uniform(-0.15, 0.15)
                spd = random.uniform(2.5, 7.2)
                r = random.uniform(2.0, 4.0)
                sid = self.fw_canvas.create_oval(x - r, y - r, x + r, y + r,
                                                 fill=(color or '#FF6B6B')
                                                 if random.random() > 0.25
                                                 else '#FFFFFF',
                                                 outline='')
                self.sparks.append({
                    'kind': 'spark', 'items': [sid], 'x': x, 'y': y,
                    'vx': math.cos(ang) * spd,
                    'vy': math.sin(ang) * spd,
                    'life': random.randint(40, 60),
                    'max_life': 60,
                    'r': r,
                })

    # ---------- 各主题粒子生成 ----------
    def _spawn_coin(self, x, y):
        """金币：向上喷 fountain，重下落、旋转翻面、落地淡化"""
        ang = -math.pi / 2 + random.uniform(-0.95, 0.95)
        spd = random.uniform(3.0, 7.0)
        r = random.uniform(4.0, 6.0)
        gold = random.random() > 0.2
        fill, outline = ('#FFD700', '#DAA520') if gold else ('#E8E8E8', '#A9A9A9')
        iid = self.fw_canvas.create_oval(x - r, y - r, x + r, y + r,
                                         fill=fill, outline=outline)
        self.sparks.append({
            'kind': 'coin', 'items': [iid], 'x': x, 'y': y,
            'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd,
            'life': random.randint(70, 110), 'max_life': 110,
            'r': r, 'angle': random.uniform(0, math.pi),
            'spin': random.uniform(0.12, 0.3),
        })

    def _spawn_popcorn(self, x, y):
        """爆米花：轻盈 radial 爆开，高阻力+横向飘摆"""
        ang = random.uniform(0, 2 * math.pi)
        spd = random.uniform(2.0, 5.5)
        r = random.uniform(2.5, 4.5)
        body = self.fw_canvas.create_oval(x - r, y - r, x + r, y + r,
                                          fill='#FFFDF3', outline='#EADFC2')
        butter = self.fw_canvas.create_oval(x - r * 0.4, y - r * 0.4,
                                            x + r * 0.4, y + r * 0.4,
                                            fill='#FFE08A', outline='')
        self.sparks.append({
            'kind': 'popcorn', 'items': [body, butter], 'x': x, 'y': y,
            'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd - 1.0,
            'life': random.randint(50, 80), 'max_life': 80,
            'r': r, 'phase': random.uniform(0, math.pi),
        })

    def _spawn_drumstick(self, x, y):
        """炸鸡腿：肉球+骨棒组合体，边飞边旋转"""
        ang = random.uniform(0, 2 * math.pi)
        spd = random.uniform(2.5, 6.5)
        r = random.uniform(5.0, 8.0)
        meat = self.fw_canvas.create_oval(x - r, y - r, x + r, y + r,
                                          fill='#E8A25E', outline='#B0713A')
        shaft = self.fw_canvas.create_line(x, y, x + r + 5, y,
                                           fill='#FFF8DC', width=3)
        knob = self.fw_canvas.create_oval(x + r + 3, y - 2.5, x + r + 7, y + 2.5,
                                          fill='#FFF8DC', outline='')
        self.sparks.append({
            'kind': 'drumstick', 'items': [meat, shaft, knob], 'x': x, 'y': y,
            'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd - 1.5,
            'life': random.randint(45, 70), 'max_life': 70,
            'r': r, 'angle': random.uniform(0, 2 * math.pi),
            'spin': random.uniform(0.12, 0.28) * random.choice([-1, 1]),
        })

    def _spawn_redpacket(self, x, y):
        """红包：红色信封上喷后摇摆下落，金色福字封印"""
        ang = -math.pi / 2 + random.uniform(-0.85, 0.85)
        spd = random.uniform(3.0, 7.0)
        r = random.uniform(6.0, 9.0)          # 半宽基准
        body = self.fw_canvas.create_rectangle(
            x - r * 0.75, y - r, x + r * 0.75, y + r,
            fill='#E03131', outline='#B02525')
        seal = self.fw_canvas.create_oval(
            x - r * 0.28, y - r * 0.28, x + r * 0.28, y + r * 0.28,
            fill='#F2C14E', outline='#B8860B')
        self.sparks.append({
            'kind': 'redpacket', 'items': [body, seal], 'x': x, 'y': y,
            'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd,
            'life': random.randint(70, 110), 'max_life': 110,
            'r': r, 'angle': 0.0,
            'phase': random.uniform(0, math.pi),
        })

    def _spawn_confetti(self, x, y):
        """彩纸屑：彩色小纸片 radial 爆开，旋转翻飞"""
        ang = random.uniform(0, 2 * math.pi)
        spd = random.uniform(1.5, 4.5)
        color = random.choice(CONFETTI_COLORS)
        pid = self.fw_canvas.create_polygon(x, y, x, y, x, y, x, y,
                                            fill=color, outline='')
        self.sparks.append({
            'kind': 'confetti', 'items': [pid], 'x': x, 'y': y,
            'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd - 1.2,
            'life': random.randint(50, 85), 'max_life': 85,
            'w': random.uniform(2.5, 4.0), 'h': random.uniform(4.0, 7.0),
            'r': 0.0,
            'angle': random.uniform(0, 2 * math.pi),
            'spin': random.uniform(0.15, 0.35) * random.choice([-1, 1]),
            'phase': random.uniform(0, math.pi),
        })

    def _spawn_star(self, x, y):
        """小星星：五角星金光放射，缓缓旋转+眨眼闪烁"""
        ang = random.uniform(0, 2 * math.pi)
        spd = random.uniform(2.0, 5.2)
        color = random.choice(['#FFD700', '#FFF7AE', '#FFDD44', '#FFE66D'])
        sid = self.fw_canvas.create_polygon(*([x, y] * 10), fill=color,
                                            outline='#DAA520')
        self.sparks.append({
            'kind': 'star', 'items': [sid], 'x': x, 'y': y,
            'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd - 1.0,
            'life': random.randint(45, 75), 'max_life': 75,
            'r': random.uniform(4.0, 8.0),
            'angle': random.uniform(0, 2 * math.pi),
            'spin': random.uniform(0.05, 0.15) * random.choice([-1, 1]),
            'phase': random.uniform(0, math.pi),
        })

    def _spawn_emoji(self, x, y):
        """表情包：emoji 上喷后摇摆飘落。优先贴 PIL 预渲染的彩色图；
        无 PIL/字体时回退画布 text（单色轮廓）。text 图元不能旋转，用缩放代偿"""
        ang = -math.pi / 2 + random.uniform(-0.9, 0.9)
        spd = random.uniform(3.0, 6.5)
        cache = getattr(self, '_emoji_cache', None)
        if cache is None:
            cache = self._emoji_cache = _load_emoji_images()
        if cache:
            big, small = random.choice(list(cache.values()))
            iid = self.fw_canvas.create_image(x, y, image=big, anchor='center')
            self.sparks.append({
                'kind': 'emoji', 'items': [iid], 'x': x, 'y': y,
                'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd,
                'life': random.randint(60, 95), 'max_life': 95,
                'r': 0.0, 'img_big': big, 'img_small': small,
                '_small': False,
                'phase': random.uniform(0, math.pi),
            })
            return
        size = random.randint(16, 28)
        ch = random.choice(EMOJI_SET)
        iid = self.fw_canvas.create_text(
            x, y, text=ch, font=('Segoe UI Emoji', size), anchor='center')
        self.sparks.append({
            'kind': 'emoji', 'items': [iid], 'x': x, 'y': y,
            'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd,
            'life': random.randint(60, 95), 'max_life': 95,
            'r': 0.0, 'size': size,
            'phase': random.uniform(0, math.pi),
        })

    def _spawn_snowflake(self, x, y):
        """雪花：六芒星细线，轻喷后极慢飘落、大幅摇摆（重力≈无的高阻力）"""
        ang = random.uniform(0, 2 * math.pi)
        spd = random.uniform(0.8, 2.8)
        r = random.uniform(4.0, 9.0)
        color = random.choice(['#FFFFFF', '#EAF6FF', '#D6ECFF', '#F4FAFF'])
        items = []
        for k in range(3):      # 3 条过中心直线 = 六角雪花
            a = k * math.pi / 3
            ca, sa = math.cos(a), math.sin(a)
            items.append(self.fw_canvas.create_line(
                x - r * ca, y - r * sa, x + r * ca, y + r * sa,
                fill=color, width=1))
        self.sparks.append({
            'kind': 'snowflake', 'items': items, 'x': x, 'y': y,
            'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd - 0.6,
            'life': random.randint(110, 160), 'max_life': 160,
            'r': r, 'angle': random.uniform(0, math.pi),
            'spin': random.uniform(0.01, 0.04) * random.choice([-1, 1]),
            'phase': random.uniform(0, math.pi),
        })

    def _spawn_mapleleaf(self, x, y):
        """枫叶：五角尖裂片+小梗，翻旋飘落（秋色）"""
        ang = random.uniform(0, 2 * math.pi)
        spd = random.uniform(1.2, 3.6)
        r = random.uniform(6.0, 11.0)
        color = random.choice(['#E74C3C', '#D35400', '#E67E22',
                               '#F39C12', '#C0392B'])
        pts = []
        for k in range(5):
            ao = k * 2 * math.pi / 5 - math.pi / 2
            ai = ao + math.pi / 5
            pts += [r * math.cos(ao), r * 1.25 * math.sin(ao),
                    r * 0.5 * math.cos(ai), r * 0.62 * math.sin(ai)]
        body = self.fw_canvas.create_polygon(
            *[p + c for p, c in zip(pts, [x, y] * 10)], fill=color, outline='')
        stem = self.fw_canvas.create_line(x, y, x, y + r * 1.5,
                                          fill='#8B5A2B', width=2)
        self.sparks.append({
            'kind': 'mapleleaf', 'items': [body, stem], 'x': x, 'y': y,
            'vx': math.cos(ang) * spd, 'vy': math.sin(ang) * spd - 0.8,
            'life': random.randint(90, 130), 'max_life': 130,
            'r': r, 'angle': random.uniform(0, 2 * math.pi),
            'spin': random.uniform(0.05, 0.12) * random.choice([-1, 1]),
            'phase': random.uniform(0, math.pi),
        })

    # ---------- 粒子每帧姿态更新 ----------
    def _layout_particle(self, sp):
        """按 kind 重算粒子各图元坐标"""
        x, y = sp['x'], sp['y']
        r = sp.get('r', 0)          # 部分主题（彩纸屑）不用 r
        fw = self.fw_canvas
        kind = sp['kind']
        if kind == 'spark':
            fw.coords(sp['items'][0], x - r, y - r, x + r, y + r)
        elif kind == 'coin':
            # 旋转翻面：横向半径随 cos 收缩，模拟硬币翻转
            rx = max(0.6, r * abs(math.cos(sp['angle'])))
            fw.coords(sp['items'][0], x - rx, y - r, x + rx, y + r)
        elif kind == 'popcorn':
            fw.coords(sp['items'][0], x - r, y - r, x + r, y + r)
            fw.coords(sp['items'][1], x - r * 0.4, y - r * 0.4,
                      x + r * 0.4, y + r * 0.4)
        elif kind == 'drumstick':
            a = sp['angle']
            ca, sa = math.cos(a), math.sin(a)
            bx, by = x + ca * (r + 5), y + sa * (r + 5)
            ex, ey = x + ca * (r - 1), y + sa * (r - 1)
            fw.coords(sp['items'][0], x - r, y - r, x + r, y + r)
            fw.coords(sp['items'][1], ex, ey, bx, by)
            fw.coords(sp['items'][2], bx - 2, by - 2, bx + 2, by + 2)
        elif kind == 'redpacket':
            w, h = r * 0.75, r
            fw.coords(sp['items'][0], x - w, y - h, x + w, y + h)
            fw.coords(sp['items'][1], x - r * 0.28, y - r * 0.28,
                      x + r * 0.28, y + r * 0.28)
        elif kind == 'confetti':
            a, w, h = sp['angle'], sp['w'], sp['h']
            ca, sa = math.cos(a), math.sin(a)
            pts = []
            for ox, oy in ((-w, -h), (w, -h), (w, h), (-w, h)):
                pts += [x + ox * ca - oy * sa, y + ox * sa + oy * ca]
            fw.coords(sp['items'][0], *pts)
        elif kind == 'star':
            # 五角星：外圈 5 顶点 + 内圈 5 顶点，带眨眼缩放
            tw = 0.85 + 0.2 * math.sin(sp['phase'])
            a, r = sp['angle'], sp['r'] * tw
            pts = []
            for k in range(5):
                ao = a + k * 2 * math.pi / 5
                ai = ao + math.pi / 5
                pts += [x + r * math.cos(ao), y + r * math.sin(ao),
                        x + r * 0.45 * math.cos(ai), y + r * 0.45 * math.sin(ai)]
            fw.coords(sp['items'][0], *pts)
        elif kind == 'emoji':
            # 图片/文字都只跟随坐标；尾段缩小模拟淡出
            fw.coords(sp['items'][0], x, y)
            if 'img_small' in sp:
                if not sp['_small'] and sp['life'] < sp['max_life'] * 0.35:
                    sp['_small'] = True
                    fw.itemconfig(sp['items'][0], image=sp['img_small'])
            else:
                k = sp['life'] / sp['max_life']
                if k < 0.45:
                    shrink = 8 + int(sp['size'] * k / 0.45)
                    if shrink != sp.get('_last_font', 0):
                        sp['_last_font'] = shrink
                        fw.itemconfig(sp['items'][0],
                                      font=('Segoe UI Emoji', max(8, shrink)))
        elif kind == 'snowflake':
            # 六角雪花：3 条直线随角度旋转
            a, r = sp['angle'], sp['r']
            ca, sa = math.cos(a), math.sin(a)
            for k in range(3):
                ak = a + k * math.pi / 3
                cak, sak = math.cos(ak), math.sin(ak)
                fw.coords(sp['items'][k],
                          x - r * cak, y - r * sak,
                          x + r * cak, y + r * sak)
        elif kind == 'mapleleaf':
            # 五角裂片（纵向拉长 1.25 倍更似叶）+ 底部小梗，整体随角度旋转
            a, r = sp['angle'], sp['r']
            ca, sa = math.cos(a), math.sin(a)
            pts = []
            for k in range(5):
                ao = k * 2 * math.pi / 5 - math.pi / 2
                ai = ao + math.pi / 5
                for ang_, rr, st in ((ao, r, 1.25), (ai, r * 0.5, 1.25)):
                    px, py = rr * math.cos(ang_), rr * st * math.sin(ang_)
                    pts += [x + px * ca - py * sa, y + px * sa + py * ca]
            fw.coords(sp['items'][0], *pts)
            sx, sy = -r * 1.5 * sa, r * 1.5 * ca     # 梗：叶尖反方向
            fw.coords(sp['items'][1], x, y, x + sx, y + sy)

    def _tick_fireworks(self):
        """每帧推进火箭与粒子（全屏坐标）"""
        # 动画期间周期性重置顶（约每 0.5s），防止播放中途被新打开的应用窗遮盖
        if (self.rockets or self.sparks):
            self._fw_frame = getattr(self, '_fw_frame', 0) + 1
            if self._fw_frame % 15 == 0:
                self._raise_fw()
        # 火箭上升（斜线轨迹飘向全屏顶点）
        for rk in list(self.rockets):
            rk['x'] += rk['vx']
            rk['y'] += rk['vy']
            self.fw_canvas.coords(rk['id'],
                                  rk['x'] - 3, rk['y'] - 3,
                                  rk['x'] + 3, rk['y'] + 3)
            if rk['y'] <= rk['target_y']:
                self.rockets.remove(rk)
                self._explode(rk)
        # 爆炸粒子：按主题物理推进 + 消亡
        _, _, _, pb = _primary_monitor()
        ground = pb - 30
        for sp in list(self.sparks):
            sp['x'] += sp['vx']
            sp['y'] += sp['vy']
            sp['life'] -= 1
            kind = sp['kind']
            if kind == 'spark':
                sp['vy'] += 0.09          # 重力
                sp['vx'] *= 0.985         # 空气阻力
                k = sp['life'] / sp['max_life']
                sp['r'] = max(0.5, sp['r'] * 0.985) if k > 0.3 else max(0.4, sp['r'] * k)
            elif kind == 'coin':
                sp['vy'] += 0.22          # 金币更重
                sp['vx'] *= 0.995
                sp['angle'] += sp['spin']
                if sp['y'] >= ground:     # 落地：停住并快速淡出
                    sp['y'] = ground
                    sp['vy'] = 0
                    sp['vx'] *= 0.85
                    sp['life'] = min(sp['life'], 12)
            elif kind == 'popcorn':
                sp['vy'] += 0.055         # 很轻，飘
                sp['vx'] *= 0.96
                sp['phase'] += 0.15
                sp['vx'] += math.sin(sp['phase']) * 0.08
            elif kind == 'drumstick':
                sp['vy'] += 0.13
                sp['vx'] *= 0.99
                sp['angle'] += sp['spin']
            elif kind == 'redpacket':
                sp['vy'] += 0.20          # 红包飘落感
                sp['vx'] *= 0.99
                sp['phase'] += 0.10
                sp['vx'] += math.sin(sp['phase']) * 0.06
                if sp['y'] >= ground:     # 落地淡出（同金币）
                    sp['y'] = ground
                    sp['vy'] = 0
                    sp['vx'] *= 0.85
                    sp['life'] = min(sp['life'], 12)
            elif kind == 'confetti':
                sp['vy'] += 0.05          # 纸片很轻
                sp['vx'] *= 0.95
                sp['phase'] += 0.20
                sp['vx'] += math.sin(sp['phase']) * 0.10
                sp['angle'] += sp['spin']
            elif kind == 'star':
                sp['vy'] += 0.07
                sp['vx'] *= 0.98
                sp['angle'] += sp['spin']
                sp['phase'] += 0.30       # 眨眼频率
            elif kind == 'emoji':
                sp['vy'] += 0.15          # 比红包轻一点
                sp['vx'] *= 0.985
                sp['phase'] += 0.12
                sp['vx'] += math.sin(sp['phase']) * 0.10   # 摇摆飘感
                if sp['y'] >= ground:     # 落地淡出（同金币）
                    sp['y'] = ground
                    sp['vy'] = 0
                    sp['vx'] *= 0.85
                    sp['life'] = min(sp['life'], 12)
            elif kind == 'snowflake':
                sp['vy'] += 0.025         # 几乎没有重力，缓缓下沉
                sp['vx'] *= 0.94          # 高阻力
                sp['phase'] += 0.10
                sp['vx'] += math.sin(sp['phase']) * 0.14   # 大幅横摆
                sp['angle'] += sp['spin'] # 缓慢自转
                if sp['vy'] > 1.2:        # 落速上限，保持飘感
                    sp['vy'] = 1.2
                if sp['y'] >= ground:
                    sp['y'] = ground
                    sp['vy'] = 0
                    sp['life'] = min(sp['life'], 10)
            elif kind == 'mapleleaf':
                sp['vy'] += 0.06          # 落叶：轻重力
                sp['vx'] *= 0.955
                sp['phase'] += 0.14
                sp['vx'] += math.sin(sp['phase']) * 0.12   # 左右飘荡
                sp['angle'] += sp['spin'] # 翻旋
                if sp['vy'] > 2.0:
                    sp['vy'] = 2.0
                if sp['y'] >= ground:
                    sp['y'] = ground
                    sp['vy'] = 0
                    sp['vx'] *= 0.8
                    sp['life'] = min(sp['life'], 12)
            if sp['life'] <= 0:
                for iid in sp['items']:
                    self.fw_canvas.delete(iid)
                self.sparks.remove(sp)
                continue
            self._layout_particle(sp)

    def _tick_sparkler(self):
        """引线火花闪烁"""
        if not hasattr(self, 'spark_star'):
            return
        cx = self.size // 2
        _, off, _, y_top, _ = self._geo()
        Y = self._Y
        flick = random.choice([-2, -1, 0, 1, 2])
        self.canvas.coords(self.spark_star,
                           cx - 4 + flick, Y(y_top - 20),
                           cx + 4 - flick, Y(y_top - 20))
        self.canvas.itemconfig(self.spark_star,
                               fill=random.choice(['#FFE66D', '#FFF3B0',
                                                   '#FFBF00', '#FFFFFF']))
        show = random.random() > 0.25
        self.canvas.itemconfig(self.spark_star2,
                               state='normal' if show else 'hidden')

    # ---------- 动画循环 ----------
    def animate(self):
        """动画循环：移动、眨眼、嘴巴动作、引线火花、烟花推进、装死抽搐
        整帧 try/except 保险：任何异常不得杀死循环（否则粒子冻结、点击无响应）"""
        try:
            if not self.dead:
                if self.is_moving:
                    dx = self.target_x - self.x
                    dy = self.target_y - self.y
                    dist = math.hypot(dx, dy)
                    if dist > self.speed:
                        move_x = int(dx / dist * self.speed)
                        move_y = int(dy / dist * self.speed)
                        self.x += move_x
                        self.y += move_y
                        self.root.geometry(f'+{self.x}+{self.y}')
                        self.animate_feet()
                    else:
                        self.is_moving = False
                elif not getattr(self, 'pinned', False) \
                        and random.random() < self.idle_chance:
                    self.pick_new_target()

                # 随机张嘴（说话动作）
                if random.random() < 0.05 and hasattr(self, 'mouth'):
                    self.mouth_open = not self.mouth_open
                    self._redraw_mouth(self.mouth_open)

                self._tick_sparkler()
            else:
                # 装死中：偶尔小脚抽搐一下
                if random.random() < 0.08:
                    self.animate_feet()

            self._tick_fireworks()
        except Exception:
            pass
        finally:
            self.root.after(30, self.animate)

    def _redraw_mouth(self, open_):
        """重绘嘴巴：微笑弧线 / 张嘴"""
        self.canvas.delete(self.mouth)
        cx = self.size // 2
        ext = getattr(self, '_EXT', 1)
        if open_:
            self.mouth = self.canvas.create_arc(
                self.get_mouth_box(),
                start=0, extent=180 * ext,
                style='pieslice', fill='#8E2F2F',
                outline='#5C1F1F', width=2)
        else:
            self.mouth = self.canvas.create_arc(
                self.get_mouth_box(),
                start=0, extent=180 * ext,
                style='arc', outline='#5C1F1F', width=2)

    def get_mouth_box(self):
        """获取嘴巴的边界框坐标"""
        if getattr(self, 'mouth_box', None):
            return self.mouth_box
        return (self.size // 2 - 12, self.mouth_top,
                self.size // 2 + 12, self.mouth_bottom)

    def animate_feet(self):
        """走路时小脚摆动（烟花筒用摆脚代替迈步）"""
        offset = random.choice([-3, 3])
        s, off, cx, y_top, y_bot = self._geo()
        Y = self._Y
        self.canvas.coords(self.shoe_l, cx - 30 + offset, Y(y_bot - 2),
                           cx - 8 + offset, Y(y_bot + 10))
        self.canvas.coords(self.shoe_r, cx + 8 - offset, Y(y_bot - 2),
                           cx + 30 - offset, Y(y_bot + 10))

    def pick_new_target(self):
        """随机选择新目标位置（限制在主显示器内活动，避免跨屏/落进空隙）"""
        pl, pt, pr, pb = _primary_monitor()
        margin = 50

        max_dx = 400
        max_dy = 250
        min_x = max(pl + margin, self.x - max_dx)
        max_x = min(pr - self.size - margin, self.x + max_dx)
        min_y = max(pt + margin, self.y - max_dy)
        max_y = min(pb - self.size - margin, self.y + max_dy)

        if min_x >= max_x:
            min_x, max_x = pl + margin, max(pl + margin + 1,
                                            pr - self.size - margin)
        if min_y >= max_y:
            min_y, max_y = pt + margin, max(pt + margin + 1,
                                            pb - self.size - margin)

        self.target_x = random.randint(min_x, max_x)
        self.target_y = random.randint(min_y, max_y)
        self.is_moving = True
        self.speed = random.randint(2, 5)

    def random_move(self):
        """定期随机移动（固定模式下不移动）"""
        if not self.dead and not getattr(self, 'pinned', False) \
                and random.random() < 0.3:
            self.pick_new_target()
        self.root.after(random.randint(3000, 8000), self.random_move)

    def toggle_pin(self):
        """切换固定/自由移动"""
        self.pinned = not getattr(self, 'pinned', False)
        if self.pinned:
            self.is_moving = False
        self.menu.entryconfig(6,
                              label='解除固定' if self.pinned else '固定位置')
        self.show_quote('已固定' if self.pinned else '自由移动')

    def _on_theme_change(self):
        """切换爆炸主题"""
        self.burst_theme = self.theme_var.get()
        self.show_quote(f'爆炸主题：{self.burst_theme}')

    def random_blink(self):
        """随机眨眼"""
        if not self.dead and not self.blinking and random.random() < 0.3:
            self.blink()
        self.root.after(random.randint(2000, 5000), self.random_blink)

    def blink(self):
        """眨眼动画"""
        self.blinking = True
        self.canvas.itemconfig(self.eye_l, fill=self.body_fill)
        self.canvas.itemconfig(self.eye_r, fill=self.body_fill)
        self.canvas.itemconfig(self.pupil_l, state='hidden')
        self.canvas.itemconfig(self.pupil_r, state='hidden')
        for l in self.lashes:
            self.canvas.itemconfig(l, state='hidden')
        self.root.after(200, self.open_eyes)

    def open_eyes(self):
        """睁开眼睛"""
        self.canvas.itemconfig(self.eye_l, fill='white')
        self.canvas.itemconfig(self.eye_r, fill='white')
        self.canvas.itemconfig(self.pupil_l, state='normal')
        self.canvas.itemconfig(self.pupil_r, state='normal')
        for l in self.lashes:
            self.canvas.itemconfig(l, state='normal')
        self.blinking = False

    def random_quote(self):
        """随机显示语录"""
        if random.random() < 0.6:
            self.show_quote()
        self.root.after(random.randint(10000, 20000), self.random_quote)

    # ---------- 气泡 ----------
    def show_quote(self, text=None):
        """显示气泡语录（固定宽度自动换行，避免过大）
        2026-11-06 防遮挡优化：剥掉"xx 已完成："类前缀、只取首行、超长截断加省略号，
        气泡始终保持一行小尺寸，字数再多也不遮挡桌面"""
        self.hide_quote()
        quote = text or random.choice(QUOTES)

        # 通知类长文本瘦身：去前缀 → 取首行 → 14 字截断
        display = quote.strip()
        for prefix in ('bot 已完成：', 'Claude 已完成：', '已完成：', '完成：', 'bot 已完成:', 'Claude 已完成:'):
            if display.startswith(prefix):
                display = display[len(prefix):].strip()
                break
        display = display.split('\n')[0].strip()
        if len(display) > 14:
            display = display[:13] + '…'
        if display:
            quote = display

        bubble_w = 240
        text_width = bubble_w - 24
        bx = self.size // 2 - bubble_w // 2
        by = 5

        # 先创建临时文字测量高度
        temp_text = self.canvas.create_text(0, 0,
                                            text=quote,
                                            fill='#333333',
                                            font=('Microsoft YaHei', 11, 'bold'),
                                            width=text_width,
                                            anchor='nw')
        bbox = self.canvas.bbox(temp_text)
        text_h = bbox[3] - bbox[1]
        self.canvas.delete(temp_text)

        bubble_h = min(80, max(45, text_h + 22))  # 2026-11-06 高度封顶防遮挡
        tip_y = by + bubble_h

        # 气泡
        self.bubble_id = self.canvas.create_oval(bx, by,
                                                 bx + bubble_w, by + bubble_h,
                                                 fill='white', outline='#E03131',
                                                 width=2)
        # 气泡尖角
        self.triangle = self.canvas.create_polygon(self.size // 2 - 8, tip_y,
                                                   self.size // 2 + 8, tip_y,
                                                   self.size // 2, tip_y + 8,
                                                   fill='white', outline='#E03131',
                                                   width=2)
        # 文字
        self.bubble_text_id = self.canvas.create_text(bx + bubble_w // 2,
                                                      by + bubble_h // 2,
                                                      text=quote,
                                                      fill='#333333',
                                                      font=('Microsoft YaHei', 11, 'bold'),
                                                      width=text_width)

        # 3.5 秒后自动隐藏
        self.root.after(3500, self.hide_quote)

    def hide_quote(self):
        """隐藏气泡"""
        if self.bubble_id:
            self.canvas.delete(self.bubble_id)
            self.bubble_id = None
        if self.bubble_text_id:
            self.canvas.delete(self.bubble_text_id)
            self.bubble_text_id = None
        if hasattr(self, 'triangle') and self.triangle:
            self.canvas.delete(self.triangle)
            self.triangle = None

    # ---------- 行为 ----------
    def take_break(self):
        """休息模式：坐到主显示器底部居中（避开多屏空隙）"""
        pl, pt, pr, pb = _primary_monitor()
        self.target_x = (pl + pr) // 2 - self.size // 2
        self.target_y = pb - self.size - 20
        self.is_moving = True
        self.show_quote()

    def play_dead(self):
        """装死：筒口朝下放躺平几秒再复活"""
        if self.dead:
            return
        self.dead = True
        self.is_moving = False
        self.mouth_open = False
        self.redraw()
        self.show_quote('我蔫了…我装的！')
        self.root.after(DEAD_MS, self.revive)

    def revive(self):
        """复活"""
        if not self.dead:
            return
        self.dead = False
        self.redraw()
        self.show_quote('复活！继续干活')

    def on_click(self, event):
        """点击互动：点到引线火花=点火放烟花；装死中被点到会提前复活；其他位置弹语录+跳"""
        if self.dead:
            self.revive()
            return
        if self._hit_spark(event.x, event.y):
            self._launch_rocket()
            self.show_quote(random.choice(['嗖——啪！', '点火！', '咻——🎆',
                                           '一发入魂！']))
            return
        self.show_quote()
        self.jump()

    def _hit_spark(self, x, y):
        """判断点击坐标是否命中引线火花（命中半径 16px）"""
        if not hasattr(self, 'spark_star'):
            return False
        try:
            coords = self.canvas.coords(self.spark_star)
            if not coords:
                return False
            cx = (coords[0] + coords[2]) / 2
            cy = (coords[1] + coords[3]) / 2
        except Exception:
            return False
        return math.hypot(x - cx, y - cy) <= 16

    def jump(self):
        """跳动动画"""
        original_y = self.y
        for i in range(10):
            offset = -10 if i % 2 == 0 else 0
            self.root.geometry(f'+{self.x}+{original_y + offset}')
            self.root.update()
            self.root.after(80)
        self.root.geometry(f'+{self.x}+{original_y}')

    def on_drag(self, event):
        """拖动宠物（松手即落盘位置，重启后从此处复活）"""
        self.x = self.root.winfo_pointerx() - self.size // 2
        self.y = self.root.winfo_pointery() - self.size // 2
        self.target_x = self.x
        self.target_y = self.y
        self.root.geometry(f'+{self.x}+{self.y}')
        self._save_pos()

    def _save_pos(self):
        """位置落盘（写失败静默忽略）"""
        try:
            with open(POS_FILE, 'w', encoding='ascii') as fh:
                fh.write(f'{self.x},{self.y}')
        except Exception:
            pass

    def on_hover(self, event):
        """鼠标悬停：举起小手"""
        if self.dead:
            return
        s, off, cx, y_top, y_bot = self._geo()
        Y = self._Y
        self.canvas.coords(self.arm_l, cx - 30, Y(y_top + 46),
                           cx - 46, Y(y_top + 34))
        self.canvas.coords(self.arm_r, cx + 30, Y(y_top + 46),
                           cx + 46, Y(y_top + 34))

    def on_leave(self, event):
        """鼠标离开：放下手"""
        if self.dead:
            return
        s, off, cx, y_top, y_bot = self._geo()
        Y = self._Y
        self.canvas.coords(self.arm_l, cx - 30, Y(y_top + 46),
                           cx - 44, Y(y_top + 58))
        self.canvas.coords(self.arm_r, cx + 30, Y(y_top + 46),
                           cx + 44, Y(y_top + 58))

    def show_menu(self, event):
        """右键菜单"""
        self.menu.post(event.x_root, event.y_root)

    def zoom_in(self):
        """放大"""
        if self.scale < 1.5:
            self.scale = round(self.scale + 0.1, 1)
            self.apply_zoom()

    def zoom_out(self):
        """缩小"""
        if self.scale > 0.6:
            self.scale = round(self.scale - 0.1, 1)
            self.apply_zoom()

    def apply_zoom(self):
        """应用缩放：清空画布并按新尺寸重绘"""
        self.canvas.delete('all')
        self.size = int(self.base_size * self.scale)
        self.bubble_area = int(self.base_bubble_area * self.scale)
        self.canvas.config(width=self.size,
                           height=self.size + 40 + self.bubble_area)
        self.draw_tube()
        self.root.geometry(
            f'{self.size}x{self.size + 40 + self.bubble_area}+{self.x}+{self.y}')

    def _tick_notify(self):
        """监听通知文件变化（AI / bot 任务完成提醒）"""
        for f in WATCH_FILES:
            try:
                mt = os.path.getmtime(f)
            except OSError:
                mt = None
            if (mt is not None and self.mtimes.get(f) is not None
                    and mt > self.mtimes[f]):
                self.mtimes[f] = mt
                self._notify(f)
            else:
                self.mtimes[f] = mt
        self.root.after(400, self._tick_notify)

    def _notify(self, path):
        """读取通知内容：弹气泡提醒；含「完成」时放烟花庆祝
        通知里带主题名（金币雨/爆米花/鸡腿）时临时切换爆炸主题"""
        try:
            with open(path, encoding='utf-8', errors='replace') as fh:
                text = fh.read().strip()
        except OSError:
            text = ''
        for t in BURST_THEMES + ('随机',):
            if t in text:
                self.burst_theme = t
                self.theme_var.set(t)
                break
        self.show_quote(text or None)
        self.jump()
        if '完成' in text:
            self.celebrate(6)

    def exit_app(self):
        """退出应用（保存位置）"""
        self._save_pos()
        self.root.destroy()
        sys.exit(0)


if __name__ == '__main__':
    try:
        DesktopBuddy()
    except Exception as e:
        print(f'程序运行出错: {e}')
