FROM alpine

ARG PYPI_SERVER_HOST
ARG PYPI_SERVER_SCHEME
ARG PYPI_SERVER_PORT

RUN apk update && \
    apk add \
        --no-cache \
        gcc \
        git \
        libpq \
        libmagic \
        musl-dev \
        postgresql-dev \
        py-virtualenv \
        python3-dev \
        python3 && \
    pyvenv /venv && \
    mkdir -p /big_repos

COPY ./requirements.txt /
COPY ./run.py /

RUN source /venv/bin/activate && \
    pip install \
        --no-cache-dir \
        --trusted-host ${PYPI_SERVER_HOST} \
        --extra-index-url ${PYPI_SERVER_SCHEME}${PYPI_SERVER_HOST}:${PYPI_SERVER_PORT} \
        --requirement /requirements.txt

ENV PYTHONPATH /pylibs
CMD ["/venv/bin/python", "-m", "run"]
