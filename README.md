# WeatherDress — сборка EXE

Инструкция по упаковке виджета в standalone `.exe` с помощью PyInstaller.

---

## Требования

| Что | Версия |
|-----|--------|
| Python | 3.8 и выше |
| pip | любая актуальная |
| PyInstaller | 5.x / 6.x |

Убедись, что Python установлен и доступен в терминале:

```powershell
python --version
```

---

## Структура папки перед сборкой

```
📁 папка проекта/
├── weather_widget.py   ← основной скрипт
├── WeatherDress.ico    ← иконка (опционально)
├── launch_widget.bat   ← запуск через Python (альтернатива EXE)
└── README_BUILD.md     ← этот файл
```

---

## Шаг 1 — Установка PyInstaller

Открой PowerShell в папке с проектом и выполни:

```powershell
python -m pip install pyinstaller
```

Проверь установку:

```powershell
python -m PyInstaller --version
```

---

## Шаг 2 — Сборка EXE

### Без иконки

```powershell
python -m PyInstaller --onefile --windowed --name WeatherDress weather_widget.py
```

### С иконкой (рекомендуется)

```powershell
python -m PyInstaller --onefile --windowed --name WeatherDress --icon=WeatherDress.ico weather_widget.py
```

| Флаг | Что делает |
|------|------------|
| `--onefile` | упаковывает всё в один `.exe` файл |
| `--windowed` | скрывает консольное окно при запуске |
| `--name WeatherDress` | имя итогового файла |
| `--icon=WeatherDress.ico` | иконка приложения |

Сборка занимает **2–5 минут**. По окончании увидишь:

```
INFO: Building EXE ... completed successfully.
```

---

## Шаг 3 — Готовый файл

После сборки появятся папки `build/` и `dist/`. Нужный файл находится здесь:

```
dist\WeatherDress.exe
```

Папки `build/` и `__pycache__/` можно удалить — они нужны только в процессе сборки.

---

## Предупреждения при сборке (не критично)

PyInstaller может выводить предупреждения вида:

```
WARNING: Library not found: could not resolve 'sycl6.dll'
WARNING: Library not found: could not resolve 'msmpi.dll'
```

Это **нормально** — это лишние библиотеки Anaconda/MKL, которые виджету не нужны. На работу `.exe` не влияют.

---

## Повторная сборка

Если ты изменил `weather_widget.py` и хочешь пересобрать, сначала удали старые файлы:

```powershell
Remove-Item -Recurse -Force build, dist, WeatherDress.spec
```

Затем снова запусти команду из Шага 2.

---

## Зависимости виджета

Виджет использует только стандартные библиотеки Python и `requests`. PyInstaller включает их автоматически. Дополнительно устанавливать ничего не нужно.

Если при запуске `.exe` появляется ошибка про `pystray` или `Pillow`:

```powershell
python -m pip install pystray Pillow requests
```

После этого пересобери EXE.

---

## Итог

```
weather_widget.py  →  [PyInstaller]  →  dist\WeatherDress.exe
```

Готовый `.exe` работает на любом Windows 10/11 без установки Python.
