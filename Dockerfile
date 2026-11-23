# Web stack image: FastAPI server + the static single-page UI.
# archlinux base per project convention.
FROM archlinux:latest

RUN pacman -Syu --noconfirm python \
    && pacman -Scc --noconfirm

# arch marks system python as externally managed (PEP 668): the sanctioned
# way to pip-install in a container is a dedicated venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements-web.txt .
RUN python -m pip install --no-cache-dir -r requirements-web.txt

COPY core/ core/
COPY locales/ locales/
COPY web/ web/
COPY ui/__init__.py ui/i18n.py ui/

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
