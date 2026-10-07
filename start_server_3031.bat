@echo off
chcp 65001 > nul
echo ========================================================
echo   Запуск локального веб-сервера для трекера откликов
echo   Порт: 3031
echo ========================================================
echo.
start http://localhost:3031/tracker.html
python -m http.server 3031
pause
