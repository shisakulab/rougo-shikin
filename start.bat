@echo off
chcp 65001 > nul
cd /d "%~dp0"
where python > nul 2>&1 && goto run_python
where py > nul 2>&1 && goto run_py
echo Python が見つかりません。README.md の「必要なもの」を確認してください。
pause
exit /b 1

:run_python
python server.py --local
goto end

:run_py
py -3 server.py --local

:end
pause
