# Windows: установка Node.js и npm (для сайта case-3)

Без Node **нет** `npm`, без `npm` не работает `scripts\web.cmd` (React UI на http://127.0.0.1:5173).

`npm` ставится **вместе** с Node — отдельно искать npm не нужно.

---

## 1. Проверка: уже стоит или нет

Открой **новый** PowerShell и выполни:

```powershell
Test-Path "C:\Program Files\nodejs\node.exe"
node -v
npm -v
```

| Результат | Что значит |
|-----------|------------|
| `node` / `npm` показывают версии (`v22…`, `10…`) | Всё ок → раздел 5 |
| `False` и «не распознано» | Node **не установлен** → раздел 2 |
| `True`, но «не распознано» | Стоит, но нет в PATH → раздел 4 |

В PowerShell команда `where` часто молчит. Используй:

```powershell
where.exe node
Get-Command node -ErrorAction SilentlyContinue
```

---

## 2. Установка Node.js (рекомендуется .msi, не winget)

Winget у многих падает с «ошибка во время выполнения». Надёжнее установщик с сайта.

1. Открой в браузере: **https://nodejs.org/**
2. Нажми зелёную кнопку **LTS** (Long Term Support).
3. Скачается файл вида `node-vXX.X.X-x64.msi`.
4. Запусти `.msi`.
5. Next → согласись с лицензией.
6. Путь оставь по умолчанию: `C:\Program Files\nodejs\`.
7. На экране инструментов можно снять галку «Automatically install…» (Chocolatey) — **не обязательно**.
8. Убедись, что Node добавляется в PATH (в современных установщиках это по умолчанию).
9. Install → Finish.

Прямая ссылка на актуальный LTS (если главная неудобна):  
https://nodejs.org/en/download — вкладка **Windows Installer (.msi)**, архитектура **x64**.

---

## 3. Обязательно: новые окна терминала

После установки:

1. Закрой **все** окна PowerShell / cmd / терминал Cursor.
2. Открой **новое** окно PowerShell.
3. Проверь:

```powershell
node -v
npm -v
```

Должно быть примерно:

```text
v22.20.0
10.9.2
```

(цифры могут отличаться — главное, что команды отвечают).

---

## 4. Если файл есть, а команды «не распознаны» (PATH)

```powershell
Test-Path "C:\Program Files\nodejs\node.exe"
```

Если `True`:

### 4.1. Проверка в обход PATH

```powershell
& "C:\Program Files\nodejs\node.exe" -v
& "C:\Program Files\nodejs\npm.cmd" -v
```

Если версии есть — почини PATH.

### 4.2. Добавить PATH навсегда (PowerShell)

```powershell
$node = "C:\Program Files\nodejs"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$node*") {
  [Environment]::SetEnvironmentVariable("Path", $userPath + ";" + $node, "User")
  Write-Host "PATH updated. Close this window and open a new one."
} else {
  Write-Host "PATH already contains nodejs. Open a NEW terminal."
}
```

Закрой окно → новое → снова `node -v` и `npm -v`.

### 4.3. Через интерфейс Windows

1. Пуск → набери **переменные среды** → «Изменение переменных среды текущего пользователя».
2. **Path** → Изменить → Создать.
3. Вставь: `C:\Program Files\nodejs`
4. OK везде.
5. Новые окна терминала.

---

## 5. Запуск сайта case-3

Из **корня** репозитория (не из `web\`):

```powershell
cd C:\path\to\case-3
git pull
```

Терминал 1:

```powershell
.\scripts\api.cmd
```

Терминал 2:

```powershell
.\scripts\web.cmd
```

Первый запуск `web.cmd` сам сделает `npm install` (1–3 минуты).

Сайт: **http://127.0.0.1:5173**  
API docs: http://127.0.0.1:8000/docs  

`:8000` — это API, не сайт.

---

## 6. Если winget уже пробовали и сломалось

В PowerShell **от имени администратора**:

```powershell
winget uninstall OpenJS.NodeJS.LTS --silent
winget uninstall OpenJS.NodeJS --silent
```

Потом поставь заново через **.msi** (раздел 2). Не опирайся на winget, если он уже падал.

---

## 7. Частые ошибки

| Сообщение | Причина | Что делать |
|-----------|---------|------------|
| «не распознано как имя командлета» (`node` / `npm`) | Нет Node или старый терминал без PATH | Разделы 2–4, **новое** окно |
| `npm` нет, а `node` есть | Битая установка | Переустанови .msi |
| `web.cmd` / «npm не является…» | То же | Сначала `node -v` / `npm -v` |
| Winget: «ошибка во время выполнения» | Сбой winget | Только .msi с nodejs.org |
| Порт занят / UI не открывается | Старый процесс | Закрой старые `api.cmd` / `web.cmd` |

---

## 8. Минимальный чеклист перед демо

- [ ] `node -v` работает в **новом** PowerShell  
- [ ] `npm -v` работает  
- [ ] Docker Desktop запущен (для PDF)  
- [ ] `.\scripts\setup.cmd` уже делали хотя бы раз  
- [ ] В `.env` есть `VISION_API_BASE_URL` (или в UI включён Dry-run)  
- [ ] `.\scripts\api.cmd` + `.\scripts\web.cmd`  
- [ ] Браузер: http://127.0.0.1:5173  

---

См. также краткий запуск в корневом [README.md](../README.md).
