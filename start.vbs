' 桌面上班搭子（烟花筒）静默启动器
' 从本 vbs 所在目录找 desktop_work_buddy.py；pythonw 依赖 PATH，
' 如机器未配置 PATH，请把下面的 py 改为完整路径（如 C:\...\pythonw.exe）
Option Explicit
Dim fso, sh, dir, py, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
py  = "pythonw.exe"
cmd = """" & py & """ """ & fso.BuildPath(dir, "desktop_work_buddy.py") & """"
sh.Run cmd, 0, False
