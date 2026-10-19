# Smoke fixtures

Готовые Source для `scripts\smoke.cmd` (Windows) или:

```bash
PYTHONPATH=src python -m case3.cli run fixtures/smoke/01_temp_shares.txt \
  -p "отчёт с графиками" --format both
```

| File | Проверка |
|------|----------|
| `01_temp_shares.txt` | line + donut / таблицы с числами |
| `02_wide_table.txt` | широкая таблица → `tabularx`, без overflow |
| `03_prose_no_numbers.txt` | без графиков (нет чисел) |
