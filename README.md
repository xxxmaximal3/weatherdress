приложение погоды для windows
<img width="325" height="179" alt="image" src="https://github.com/user-attachments/assets/13a67998-e8f4-4a1e-a20a-36637fbc05f4" />

Шаг 1 — установи PyInstaller:
powershellpip install pyinstaller

Шаг 2 — если pip тоже не найден, значит Python не добавлен в PATH. Попробуй так:
powershellpython -m pip install pyinstaller

Шаг 3 — после установки собери .exe:
powershellpython -m PyInstaller --onefile --windowed --name WeatherDress weather_widget.py

Используй python -m PyInstaller вместо просто pyinstaller — это работает даже когда PATH не настроен.
