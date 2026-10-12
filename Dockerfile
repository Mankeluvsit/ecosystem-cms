 # syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CMS_HOST=0.0.0.0 \
    CMS_PORT=8765 \
    CMS_DB=/data/cms.sqlite3

WORKDIR /srv/ecosystem-cms
COPY requirements.txt ./
RUN --mount=type=secret,id=proxy_ca,target=/run/proxy-ca.pem \
    if [ -f /run/proxy-ca.pem ]; then export PIP_CERT=/run/proxy-ca.pem; fi; \
    pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY README.md DEPLOYMENT.md ./
COPY docker-entrypoint.sh ./
RUN mkdir -p /data && useradd --create-home --uid 10001 cms && chown -R cms:cms /srv/ecosystem-cms /data && chmod 755 docker-entrypoint.sh
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health',timeout=3)"
ENTRYPOINT ["/srv/ecosystem-cms/docker-entrypoint.sh"]
CMD ["python", "-m", "app.web"]
