@echo off
:: WeatherDress Widget — запуск
title WeatherDress Widget

python --version >nul 2>&1
if errorlevel 1 (
    echo Python не найден! Установите Python 3.8+ с https://python.org
    pause & exit /b 1
)

echo Проверка зависимостей...
pip install requests --quiet --disable-pip-version-check

:: pythonw — запуск без консольного окна
start "" pythonw "%~dp0weather_widget.py"
