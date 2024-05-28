@echo on

REM tomado de https://stackoverflow.com/questions/5898763/how-do-i-get-the-ip-address-into-a-batch-file-variable
for /f "delims=[] tokens=2" %%a in ('ping -4 -n 1 %ComputerName% ^| findstr [') do set NetworkIP=%%a

REM tomado de https://stackoverflow.com/questions/17063947/get-current-batchfile-directory
cd /d %~dp0

REM tomado de https://stackoverflow.com/questions/206114/batch-files-how-to-read-a-file
FOR /F %%i IN (DefaultNodeIP.txt) DO set NodeIP=%%i

cd C:\Users\usuario\Documents\GitHub\ServidorDeArchivos\Client
python client.py %NodeIP% download xd.torrent
cmd /k