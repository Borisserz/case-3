import { useEffect, useRef, useState } from "react";
import { MsgMarkdown } from "./lightMd";
import { useFocusTrap } from "./useFocusTrap";

export type LayoutOption = {
  id: string;
  name: string;
  desc: string;
  md: string;
};

export const LAYOUT_OPTIONS: LayoutOption[] = [
  {
    id: "bullets",
    name: "Тезисы (список)",
    desc: "Заголовок и список ключевых тезисов",
    md: "# Заголовок слайда\n\n- первый тезис\n- второй тезис\n- третий тезис",
  },
  {
    id: "section",
    name: "Раздел (глава)",
    desc: "Титул главы с крупным номером и описанием",
    md: "## 02\n\n# Название главы\n\nКороткое описание, зачем этот раздел на слайде.",
  },
  {
    id: "callout",
    name: "Ключевой тезис",
    desc: "Акцентная карточка с термином и определением",
    md: "# Термин\n\n**Определение** в две строки: что имеется в виду и зачем это на слайде.",
  },
  {
    id: "quote",
    name: "Цитата / позиция",
    desc: "Фокусная мысль спикера или эксперта",
    md: "# Позиция\n\n_Формулировка, которую слайд держит в центре кадра._\n\nисточник или роль",
  },
  {
    id: "scorecard",
    name: "Сводка показателей",
    desc: "Сетка ключевых KPI с дельтами и статусами",
    md: "# Сводка\n\n| Показатель | Статус |\n| --- | --- |\n| Объём | в плане |\n| Темп | держать |\n| Разрыв | пауза |",
  },
  {
    id: "stat_hero",
    name: "Главная цифра",
    desc: "Крупная якорная метрика и выводы",
    md: "# Главная цифра\n\nподпись метрики\n\n- что это значит\n- что делать дальше",
  },
  {
    id: "compare",
    name: "Сравнение 2 сторон",
    desc: "Две контрастные карточки (За vs Против / Модели)",
    md: "# Сравнение\n\n### За\nаргумент в одну строку\n\n### Против\nаргумент в одну строку",
  },
  {
    id: "card_row",
    name: "3 направления",
    desc: "Три параллельных трека с описанием",
    md: "# Три направления\n\n### Первое\nкороткая подпись\n\n### Второе\nкороткая подпись\n\n### Третье\nкороткая подпись",
  },
  {
    id: "table_hero",
    name: "Таблица",
    desc: "Сводная таблица параметров и статусов",
    md: "# Параметры\n\n| Параметр | Статус |\n| --- | --- |\n| Срок | в плане |\n| Объём | держать |\n| Риск | пауза |",
  },
  {
    id: "timeline",
    name: "Таймлайн (этапы)",
    desc: "Дорожная карта реализации по шагам",
    md: "# Этапы\n\n- **Старт** — подготовка\n- **Сбор** — данные\n- **Сверка** — план\n- **Итог** — решение",
  },
  {
    id: "closing",
    name: "Финальный слайд",
    desc: "Главный вердикт и следующие шаги",
    md: "# Вердикт\n\n- первый следующий шаг\n- второй следующий шаг\n- третий следующий шаг",
  },
];

type Props = {
  open: boolean;
  onClose: () => void;
  onPick: (layout: string) => void;
  afterSlideNum?: number;
};

export function LayoutPickerModal({
  open,
  onClose,
  onPick,
  afterSlideNum,
}: Props) {
  const modalRef = useRef<HTMLDivElement>(null);
  const [activeId, setActiveId] = useState(LAYOUT_OPTIONS[0].id);
  useFocusTrap(modalRef, { active: open });

  useEffect(() => {
    if (!open) return;
    setActiveId(LAYOUT_OPTIONS[0].id);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const active =
    LAYOUT_OPTIONS.find((opt) => opt.id === activeId) ?? LAYOUT_OPTIONS[0];

  return (
    <div
      className="presentation-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="layout-picker-title"
      onClick={onClose}
    >
      <div
        ref={modalRef}
        className="presentation-layout-picker"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="presentation-layout-picker-head">
          <div>
            <h3 id="layout-picker-title" className="presentation-layout-picker-title">
              Добавить слайд
            </h3>
            <p className="presentation-layout-picker-sub">
              {afterSlideNum != null
                ? `Выберите макет для вставки после слайда ${afterSlideNum}`
                : "Выберите макет нового слайда"}
            </p>
          </div>
          <button
            type="button"
            className="presentation-layout-picker-close"
            onClick={onClose}
            aria-label="Закрыть"
            title="Закрыть (Esc)"
          >
            ×
          </button>
        </header>

        <div className="presentation-layout-picker-body">
          <div className="presentation-layout-picker-list" role="listbox" aria-label="Макеты">
            {LAYOUT_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                role="option"
                aria-selected={opt.id === active.id}
                className={`presentation-layout-opt${opt.id === active.id ? " is-active" : ""}`}
                onMouseEnter={() => setActiveId(opt.id)}
                onFocus={() => setActiveId(opt.id)}
                onClick={() => {
                  onPick(opt.id);
                  onClose();
                }}
              >
                <span className="presentation-layout-opt-name">{opt.name}</span>
                <span className="presentation-layout-opt-desc">{opt.desc}</span>
              </button>
            ))}
          </div>

          <aside className="presentation-layout-preview" aria-label="Предпросмотр макета">
            <p className="presentation-layout-preview-kicker">Предпросмотр</p>
            <div className="presentation-layout-slide-frame">
              <MsgMarkdown text={active.md} className="presentation-layout-slide" />
            </div>
            <p className="presentation-layout-preview-note">{active.desc}</p>
          </aside>
        </div>
      </div>
    </div>
  );
}
