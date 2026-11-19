# 桌面上班搭子 🎆

一只住在桌面右下角附近的**烟花筒桌面宠物**：默认乖乖待在固定位置（可解锁自由走动）、被点了会跳、会冒励志语录，最重要的是——**你的脚本 / bot / AI 助手干完活时，它放全屏烟花向你报喜**。

纯 Python + tkinter 实现，单文件，零配置，clone 下来就能跑。

## 功能一览

- **任务完成庆祝**：监听通知文件 `.buddy_notify`，收到消息后弹气泡；消息含「完成」时连发 6 发火箭，全屏炸开
- **11 种爆炸主题**：烟花、金币雨、爆米花、鸡腿、红包雨、彩纸屑、小星星、表情包、雪花、枫叶、随机（每发抽签）
- **桌宠互动**：
  - 点引线火花 → 手动放一发烟花 +「嗖——啪！」
  - 点身体 → 弹励志语录 + 跳一下
  - 它偶尔也会自己装死（彩蛋）
- **右键菜单**：切换爆炸主题、🎆 放烟花庆祝、固定/解除固定位置、缩放、退出
- **位置记忆**：拖拽后自动存档，重启从上次位置恢复
- **通知智能显示**：自动剥掉「xxx 已完成：」这类前缀、超长截断加省略号

## 环境要求

| 依赖 | 是否必需 | 说明 |
|------|:---:|------|
| Windows | ✅ | 用了 Windows 窗口 API 实现全屏烟花置顶与点击穿透 |
| Python 3.x（含 tkinter） | ✅ | 官方安装包默认自带，安装时勾选 tcl/tk |
| Pillow | 可选 | `pip install Pillow`；装了表情包主题是彩色的，没装自动回退单色，其余功能不受影响 |

## 最快接入：让 AI 帮你部署并接入流水线

把下面这段 prompt **原样**发给你常用的 AI 编码助手（Claude Code / Trae / Kimi / Cursor 均可），它会帮你把宠物跑起来并接入你现有的脚本 / bot：

```text
我要部署一只桌面宠物（任务完成时放烟花庆祝），仓库地址：
https://github.com/gaoqiongxie/desktop-work-buddy

请先通读该仓库的 README.md，然后帮我完成：

【部署（Windows）】
1. git clone 到一个固定目录（如 D:\tools\desktop-work-buddy），确认 python 可用且
   带 tkinter（python -c "import tkinter"）
2. 可选：pip install Pillow（表情包主题彩色化，不装也能跑）
3. 双击试跑 start.vbs（无黑窗静默启动），确认宠物出现在桌面右下角；
   如果没配 pythonw 的 PATH，帮我定位 pythonw.exe 完整路径改好 start.vbs
4. 帮我配开机自启：start.vbs 的快捷方式放进 shell:startup

【接入我的流水线（先问我有哪些脚本/bot 要接）】
5. 在需要通知的任务完成处加一行写入 .buddy_notify（含「完成」二字会触发烟花，
   可追加主题名如「报表完成：金币雨」，协议详见 README）：
   - Python: Path('.buddy_notify').write_text('构建完成', encoding='utf-8')
   - Shell:  echo 构建完成 > .buddy_notify
   - 其他 bot 的写入路径若不在本目录，配 BUDDY_NOTIFY_FILES 环境变量（分号分隔）
6. 验证：让我手动 echo 一条「测试完成」到 .buddy_notify，确认宠物弹气泡+放烟花

【红线】
- 写入路径必须用绝对路径或先确认工作目录，防止通知写到了别的 .buddy_notify
- 只加通知行，不顺手重构我的脚本
- 接入完成后给我一份清单：哪些文件加了通知行、写入的是哪个 .buddy_notify 路径
```

## 快速开始

```bash
git clone https://github.com/gaoqiongxie/desktop-work-buddy.git
cd desktop-work-buddy
python desktop_work_buddy.py
```

或用静默方式启动（不弹黑窗）：双击 `start.vbs`。
> start.vbs 默认依赖 `pythonw` 在 PATH 里；如果没配 PATH，右键编辑 start.vbs，把 `py = "pythonw.exe"` 改成完整路径（如 `C:\Users\你\AppData\Local\Programs\Python\Python312\pythonw.exe`）。

## 接入你的脚本 / bot（核心玩法）

**往 `.buddy_notify` 文件写一行文本即可**，宠物实时弹出：

```python
from pathlib import Path
Path('.buddy_notify').write_text('构建完成', encoding='utf-8')
```

```bash
# shell 也一样
echo "构建完成" > .buddy_notify
```

### 通知协议

| 消息内容 | 效果 |
|----------|------|
| 任意文本 | 弹气泡提醒 |
| 含「**完成**」 | 气泡 + **连发 6 发火箭**全屏庆祝 |
| 含主题名（如「金币雨」「雪花」） | 本次爆炸临时切换为该主题 |
| 以「xx 已完成：」开头 | 气泡显示时自动剥掉前缀，只留正文 |

> 机器人接入示例：CI 跑完写「构建完成」、定时任务写完写「报表完成：金币雨」（自动炸金币）、AI 助手干完活写「xxx 已完成：<摘要>」。

### 监听多个通知源

默认只监听**脚本所在目录**的 `.buddy_notify`。还想监听别的路径（比如其他 bot 的写入点），设环境变量即可，分号分隔：

```bash
set BUDDY_NOTIFY_FILES=D:\bots\.buddy_notify;E:\tmp\.buddy_notify
```

## 文件说明

| 文件 | 作用 |
|------|------|
| `desktop_work_buddy.py` | 宠物本体，单文件即全部功能 |
| `start.vbs` | Windows 静默启动器（pythonw，无黑窗） |
| `_pet_snap.py` | 开发辅助：PrintWindow 截取宠物窗口验证渲染 |
| `_screen_snap.py` / `_screen_snap_aware.py` | 开发辅助：全屏截图，验证烟花全屏层实际效果 |
| `.gitignore` | 忽略运行时文件（通知文件、位置存档、缓存） |

## 已知边界

- 只在 **Windows** 上运行；宠物活动范围限制在主显示器内（多显示器时不会跑到副屏）
- 表情包主题依赖 Windows 的 Segoe UI Emoji 字体（`C:\Windows\Fonts\seguiemj.ttf`），Windows 10/11 自带
- 全屏烟花层点击穿透，不会挡住你的桌面操作

## 打赏一只烟花筒 ⭐

如果它让你的打工生活快乐了一点，欢迎点个 Star～
