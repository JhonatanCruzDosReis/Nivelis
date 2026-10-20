@echo off
powershell.exe -ExecutionPolicy Bypass -NoExit -Command "Set-Location '%~dp0'; & '%~dp0build-apk.ps1'"
