Шаг 1 — установи PyInstaller:
powershellpip install pyinstaller
Шаг 2 — если pip тоже не найден, значит Python не добавлен в PATH. Попробуй так:
powershellpython -m pip install pyinstaller
Шаг 3 — после установки собери .exe:
powershellpython -m PyInstaller --onefile --windowed --name WeatherDress weather_widget.py

Используй python -m PyInstaller вместо просто pyinstaller — это работает даже когда PATH не настроен.