FROM python:3.14-slim-bookworm@sha256:416f0db2a2b561945630cef9877a7ea0581b27449eb9fd9df42f03e1b74b5b63 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /build

COPY pyproject.toml ./
COPY requirements.lock ./
COPY apps/__init__.py ./apps/__init__.py
COPY apps/api ./apps/api
COPY packages/__init__.py ./packages/__init__.py
COPY packages/python ./packages/python
COPY services ./services
RUN python -m venv /opt/portfolio-venv \
    && /opt/portfolio-venv/bin/pip install --upgrade pip==26.2.1 \
    && /opt/portfolio-venv/bin/pip install --no-deps -r requirements.lock \
    && /opt/portfolio-venv/bin/pip install --no-deps .

FROM python:3.14-slim-bookworm@sha256:416f0db2a2b561945630cef9877a7ea0581b27449eb9fd9df42f03e1b74b5b63 AS runtime

ENV PATH="/opt/portfolio-venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORTFOLIO_STORAGE_ROOT=/app/var/media

RUN groupadd --system --gid 10001 portfolio \
    && useradd --system --uid 10001 --gid portfolio --home-dir /app --shell /usr/sbin/nologin portfolio \
    && mkdir -p /app/var/media \
    && chown -R portfolio:portfolio /app

COPY --from=builder /opt/portfolio-venv /opt/portfolio-venv
RUN /opt/portfolio-venv/bin/python -m pip uninstall --yes pip \
    && /usr/local/bin/python -m pip uninstall --yes pip
WORKDIR /app
COPY --chown=portfolio:portfolio apps/__init__.py ./apps/__init__.py
COPY --chown=portfolio:portfolio apps/api ./apps/api
COPY --chown=portfolio:portfolio packages/__init__.py ./packages/__init__.py
COPY --chown=portfolio:portfolio packages/python ./packages/python
COPY --chown=portfolio:portfolio services ./services
COPY --chown=portfolio:portfolio db ./db
COPY --chown=portfolio:portfolio alembic.ini pyproject.toml requirements.lock ./

USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGTERM
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--timeout-graceful-shutdown", "30", "--proxy-headers"]
