Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

folder = FSO.GetParentFolderName(WScript.ScriptFullName)

pythonw = "C:\Users\Avinash B\AppData\Local\Programs\Python\Python313\pythonw.exe"

WshShell.CurrentDirectory = folder

WshShell.Run """" & pythonw & """ """ & folder & "\app.py""", 0, False