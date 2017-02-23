FROM python:alpine

RUN apk --quiet update && \
    apk --quiet add \
        --no-cache \
        gcc \
        git \
        libpq \
        postgresql-dev \
        musl-dev && \
    python3.6 -m venv /venv && \
    mkdir -p /big_repos


ARG PYTHON_COMMONS_HOST
ARG PYTHON_COMMONS_SCHEME
ARG PYTHON_COMMONS_PORT

COPY requirements.txt /

RUN source /venv/bin/activate && \
    pip install --upgrade pip && \
    pip install \
        --quiet \
        --no-cache-dir \
        --trusted-host ${PYTHON_COMMONS_HOST} \
        --extra-index-url ${PYTHON_COMMONS_SCHEME}${PYTHON_COMMONS_HOST}:${PYTHON_COMMONS_PORT} \
        --requirement /requirements.txt

ENV PYTHONPATH /usr/app/src
COPY run.py /
COPY scanner /usr/app/src/scanner

CMD ["/venv/bin/python", "-m", "run"]
