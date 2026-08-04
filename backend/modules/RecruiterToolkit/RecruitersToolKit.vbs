Set WshShell = CreateObject("WScript.Shell")

strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

WshShell.Run Chr(34) & strPath & "\run_tool.bat" & Chr(34), 0

Set WshShell = Nothing