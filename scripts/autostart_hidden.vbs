Option Explicit
' Silent start used by the Startup shortcut: no console, no automatic browser tab.
Dim shell, fso, here, root, pythonw, launcher, command

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

here = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(here)
pythonw = fso.BuildPath(root, ".venv\Scripts\pythonw.exe")
launcher = fso.BuildPath(root, "launcher.py")

If Not fso.FileExists(pythonw) Then
    WScript.Quit 0
End If

shell.Environment("PROCESS")("VIDEO_OPEN_BROWSER") = "0"
shell.CurrentDirectory = root
command = """" & pythonw & """ """ & launcher & """ --no-browser"
shell.Run command, 0, False
