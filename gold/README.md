# Gold eval — эталоны LaTeX для модели

Вырезки в стиле реальных отчётов (Prototip / CSIS / STP-паттерны), упрощённые под образ `case-3:tex` (article + DejaVu, без полного СТП).

| Файл | Чему учит |
|------|-----------|
| `01_figure.tex` | figure + includegraphics + caption/label |
| `02_table.tex` | booktabs tabular |
| `03_lists_sections.tex` | section / itemize / enumerate |
| `04_mixed_mini.tex` | текст + таблица + место под картинку |

При генерации эти файлы (укороченно) дописываются в system prompt.

Для прогона eval: положи вход в `gold/evals/<name>/content.txt` (+ images) и сравни выход с ожидаемым `.tex` вручную / diff.
