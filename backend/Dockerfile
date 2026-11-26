# case-3 backend — FastAPI + Playwright Chromium + XeLaTeX + Pandoc + LibreOffice
# Chromium 159 (Playwright 1.65.2) лежит в vendor/playwright.
# Образ linux/amd64: так его запускает Docker на Windows.
# Сборка не ходит на cdn.playwright.dev.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CASE3_ROOT=/app \
    CASE3_TEX_LOCAL=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    CASE3_PORT=8000

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
      ca-certificates \
      curl \
      libatomic1 \
      latexmk \
      lmodern \
      texlive-xetex \
      texlive-lang-cyrillic \
      texlive-latex-recommended \
      texlive-latex-extra \
      texlive-fonts-recommended \
      fonts-dejavu \
      fonts-liberation \
      pandoc \
      libreoffice-impress \
      libreoffice-writer \
    && apt-get --purge remove -y '.*-doc$' \
    && apt-get clean -y

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY prompt ./prompt
COPY assets ./assets

# Zip из репозитория. Каталоги — те, что ждёт Playwright 1.65.2.
COPY vendor/playwright/chrome-linux64.zip \
     vendor/playwright/chrome-headless-shell-linux64.zip \
     vendor/playwright/unpack.py \
     /tmp/pw/
RUN python /tmp/pw/unpack.py && rm -rf /tmp/pw

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . "playwright==1.65.2" && \
    python -m playwright install-deps chromium && \
    test -x /ms-playwright/chromium-1255/chrome-linux64/chrome && \
    test -x /ms-playwright/chromium_headless_shell-1255/chrome-headless-shell-linux64/chrome-headless-shell && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/runs/out /app/runs/work /app/runs/uploads /app/runs/logs /app/local

EXPOSE 8000

# Порт берётся из CASE3_PORT (compose или backend/.env). 8000 — только внутри сети Docker.
CMD ["sh", "-c", "exec uvicorn case3.api:app --host 0.0.0.0 --port ${CASE3_PORT:-8000} --workers 1"]
