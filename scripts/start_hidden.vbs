Option Explicit
' Start Video Inbox without a console window. Double-click to open the app:
' if the service is already running, the page is opened instead of a second copy.
Dim shell, fso, here, root, pythonw, launcher, command

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

here = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(here)
pythonw = fso.BuildPath(root, ".venv\Scripts\pythonw.exe")
launcher = fso.BuildPath(root, "launcher.py")

If Not fso.FileExists(pythonw) Then
    MsgBox "Python environment not found." & vbCrLf & vbCrLf & _
           "Run run_web.bat once to prepare .venv, then try again.", _
           vbCritical, "Video Inbox"
    WScript.Quit 1
End If

shell.CurrentDirectory = root
command = """" & pythonw & """ """ & launcher & """ --no-browser"
shell.Run command, 0, False
