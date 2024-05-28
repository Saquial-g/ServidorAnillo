REM tomado de https://superuser.com/questions/230233/how-to-get-lan-ip-to-a-variable-in-a-windows-batch-file
for /F "tokens=2 delims=:" %%i in ('"ipconfig | findstr IPv4"') do SET NetworkIP=%%i

REM tomado de https://stackoverflow.com/questions/17063947/get-current-batchfile-directory
cd /d %~dp0 
python node.py %~dp0Subserver1%NetworkIP%:5556 default
cmd /k