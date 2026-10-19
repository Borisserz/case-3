/** Liber-style in-chat report: title, prose, tables, figure PNGs. */

export type PreviewBlock =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; text: string }
  | {
      type: "table";
      caption?: string;
      headers: string[];
      rows: string[][];
    }
  | {
      type: "figure";
      id: string;
      kind: string;
      caption?: string;
      url?: string;
    };

export type ReportPreview = {
  title?: string;
  blocks: PreviewBlock[];
};

type Downloads = Record<string, string>;

type Props = {
  preview: ReportPreview;
  downloads?: Downloads;
  runId?: string;
  stats?: string;
  warnings?: string[];
};

export function ReportView({
  preview,
  downloads,
  runId,
  stats,
  warnings,
}: Props) {
  const blocks = preview.blocks || [];
  let figN = 0;
  let tabN = 0;

  return (
    <article className="report">
      {(stats || (warnings && warnings.length > 0) || runId) && (
        <header className="report-meta">
          {runId && <span className="report-run">run {runId}</span>}
          {stats && <span className="report-stats">{stats}</span>}
          {warnings && warnings.length > 0 && (
            <span className="report-warns">{warnings.join(" · ")}</span>
          )}
        </header>
      )}

      {preview.title ? (
        <h1 className="report-title">{preview.title}</h1>
      ) : (
        <h1 className="report-title muted">Отчёт</h1>
      )}

      <div className="report-body">
        {blocks.map((b, i) => {
          if (b.type === "heading") {
            const Tag = b.level >= 2 ? "h3" : "h2";
            return (
              <Tag key={i} className={`report-h report-h${b.level}`}>
                {b.text}
              </Tag>
            );
          }
          if (b.type === "paragraph") {
            return (
              <p key={i} className="report-p">
                {b.text}
              </p>
            );
          }
          if (b.type === "table") {
            tabN += 1;
            const n = tabN;
            return (
              <figure key={i} className="report-table-wrap">
                {b.caption ? (
                  <figcaption className="report-caption">
                    Таблица {n}: {b.caption}
                  </figcaption>
                ) : (
                  <figcaption className="report-caption muted">
                    Таблица {n}
                  </figcaption>
                )}
                <div className="report-table-scroll">
                  <table className="report-table">
                    <thead>
                      <tr>
                        {b.headers.map((h, hi) => (
                          <th key={hi}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {b.rows.map((row, ri) => (
                        <tr key={ri}>
                          {row.map((cell, ci) => (
                            <td key={ci}>{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </figure>
            );
          }
          if (b.type === "figure") {
            figN += 1;
            const n = figN;
            const label =
              b.kind === "chart" ? "Рис." : "Илл.";
            return (
              <figure key={i} className="report-fig">
                {b.url ? (
                  <a href={b.url} target="_blank" rel="noreferrer" className="report-fig-link">
                    <img src={b.url} alt={b.caption || b.id} loading="lazy" />
                  </a>
                ) : (
                  <div className="report-fig-missing">
                    {b.id} — изображение недоступно
                  </div>
                )}
                <figcaption className="report-caption">
                  {label} {n}
                  {b.caption ? `: ${b.caption}` : ""}
                </figcaption>
              </figure>
            );
          }
          return null;
        })}
      </div>

      {downloads && (downloads.pdf || downloads.docx) && (
        <footer className="report-actions downloads">
          {downloads.pdf && (
            <a href={downloads.pdf} download>
              PDF
            </a>
          )}
          {downloads.docx && (
            <a className="secondary" href={downloads.docx} download>
              DOCX
            </a>
          )}
        </footer>
      )}
    </article>
  );
}
