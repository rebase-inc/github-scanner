FROM python:alpine

RUN pip install --upgrade pip && \
    pip install rq-dashboard

STOPSIGNAL SIGKILL

ENTRYPOINT ["rq-dashboard", "-H", "redis", "-b", "0.0.0.0", "-p", "4444", "--interval", "3000"]
