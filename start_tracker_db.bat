@echo off
cd /d "%~dp0"
echo Starting Job Tracker Server with SQLite...
echo Open in browser: http://localhost:3031/tracker.html
echo.
start http://localhost:3031/tracker.html
python server_with_db.py
pause
