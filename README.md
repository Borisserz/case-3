# case-3

Текст → **Qwen (text-to-text)** → LaTeX → **PDF/DOCX** (Docker).

Модель пишет только `.tex`. Картинки не генерирует.

## Каждый день

1. Положи `notes.txt` в корень проекта.
2. Запусти:

```cmd
scripts\run.cmd notes.txt
```

Только PDF / только Word:

```cmd
scripts\run.cmd notes.txt pdf
scripts\run.cmd notes.txt docx
```

Без API (проверка TeX):

```cmd
scripts\run.cmd notes.txt both --dry-run
```

Результат: `out\<имя>_<время>\` (`.tex`, `.pdf`, `.docx`).  
Логи: `logs\...`

Залить tex+логи на GitHub для дебага:

```cmd
scripts\push-debug.cmd
```

## Скрипты

| Скрипт | Когда |
|--------|--------|
| `scripts\setup.cmd` | один раз (pip + docker image) |
| `scripts\run.cmd` | каждый прогон |
| `scripts\push-debug.cmd` | отправить логи нам |

## Первый запуск (Windows)

```cmd
git clone https://github.com/Borisserz/case-3.git
cd case-3
git pull
scripts\setup.cmd
```

В `.env` укажи хост Qwen:

```env
VISION_API_BASE_URL=http://192.168.x.x:8080
```

## macOS

```bash
cp .env.example .env
pip install -e .
docker compose build
./scripts/run.sh notes.txt
```

## Docker / виртуализация

Если Engine stopped / «Virtualization support not detected»:

1. PowerShell админ: `systeminfo | findstr /i Hyper-V` — нужно **Virtualization Enabled In Firmware: Yes**
2. `optionalfeatures`: Virtual Machine Platform + WSL → reboot → `wsl --install`
3. BIOS: Intel VT-x / AMD SVM
4. Потом: `docker version` и `scripts\setup.cmd`
