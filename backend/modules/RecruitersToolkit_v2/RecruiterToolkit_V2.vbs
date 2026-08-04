Set WshShell = CreateObject("WScript.Shell")

folder = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

WshShell.CurrentDirectory = folder

WshShell.Run "py src\ui.py", 0, False