# Web stack image: FastAPI server + the static single-page UI.
# archlinux base per project convention; llama-cpp serves the local
# HY-MT1.5 fallback engine (README LOCAL MODEL FALLBACK).
FROM archlinux:latest

RUN pacman -Syu --noconfirm python llama-cpp \
    && pacman -Scc --noconfirm

# arch marks system python as externally managed (PEP 668): poetry runs from
# a scratch venv and gets its own in-project virtualenv (/app/.venv) instead
# of touching the pacman-owned system tree
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir poetry \
    && POETRY_VIRTUALENVS_IN_PROJECT=true /opt/venv/bin/poetry install --only main,web

COPY core/ core/
COPY locales/ locales/
COPY web/ web/
COPY ui/__init__.py ui/i18n.py ui/

EXPOSE 8000
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
