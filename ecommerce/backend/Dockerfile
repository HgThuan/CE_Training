FROM python:3.12-slim AS builder

ARG REQUIREMENTS_FILE=requirements/production.txt

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements ./requirements
RUN pip install --upgrade pip \
    && pip install --requirement "${REQUIREMENTS_FILE}"

FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system django \
    && useradd --system --gid django --create-home django

COPY --from=builder /opt/venv /opt/venv
COPY --chown=django:django . .

RUN mkdir -p /app/staticfiles /app/media \
    && chown -R django:django /app/staticfiles /app/media

USER django

EXPOSE 8000

CMD ["gunicorn", "config.asgi:application", "--bind=0.0.0.0:8000", "--worker-class=uvicorn_worker.UvicornWorker"]

