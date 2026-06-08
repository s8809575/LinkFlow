@echo off
echo Starting LinkFlow...
cd /d "C:\Users\scl\Desktop\LinkFlow\src\python\dist"
LinkFlow.exe > "..\output.log" 2>&1
echo Exit code: %errorlevel%
echo Press any key to exit...
pause