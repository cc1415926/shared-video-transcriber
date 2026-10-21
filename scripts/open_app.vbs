Option Explicit
' Desktop launcher: reuse a healthy instance, or start one and wait for readiness.

Dim shell, fso, here, root, pythonw, launcher, url, logPath, deadline

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

here = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(here)
pythonw = fso.BuildPath(root, ".venv\Scripts\pythonw.exe")
launcher = fso.BuildPath(root, "launcher.py")
logPath = RuntimeLogPath()

url = FindService()
If url = "" Then
    If Not fso.FileExists(pythonw) Then
        MsgBox "找不到项目运行环境。" & vbCrLf & _
               "请先双击 run_web.bat 完成安装。", vbCritical, "视频收件箱"
        WScript.Quit 1
    End If
    shell.CurrentDirectory = root
    shell.Run """" & pythonw & """ """ & launcher & """ --no-browser", 0, False
    deadline = DateAdd("s", 45, Now)
    Do
        WScript.Sleep 350
        url = FindService()
        If url <> "" Then Exit Do
    Loop While Now < deadline
End If

If url = "" Then
    MsgBox "本地服务未能在 45 秒内启动。" & vbCrLf & _
           "请双击 run_web.bat 查看即时错误，或查看日志：" & vbCrLf & logPath, _
           vbCritical, "视频收件箱启动失败"
    WScript.Quit 2
End If

shell.Run url, 1, False

Function FindService()
    Dim port, candidate, http
    FindService = ""
    For port = 7860 To 7879
        candidate = "http://127.0.0.1:" & port
        On Error Resume Next
        Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
        http.setProxy 2, "", ""
        http.setTimeouts 250, 250, 350, 600
        http.Open "GET", candidate & "/api/health", False
        http.Send
        If Err.Number = 0 And http.Status = 200 Then
            If InStr(1, http.responseText, """service"":""video-inbox""", vbTextCompare) > 0 Then
                FindService = candidate & "/"
                On Error GoTo 0
                Exit Function
            End If
        End If
        Err.Clear
        On Error GoTo 0
    Next
End Function

Function RuntimeLogPath()
    Dim localData
    localData = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
    RuntimeLogPath = fso.BuildPath(localData, "VideoInbox\logs\launcher.log")
    If fso.FileExists(fso.BuildPath(root, ".data\library.sqlite3")) Then
        RuntimeLogPath = fso.BuildPath(root, ".data\logs\launcher.log")
    End If
End Function
