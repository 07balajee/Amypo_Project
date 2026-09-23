FROM python:3.11-slim
WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir ".[qa]"

COPY config.yaml ./

EXPOSE 8001
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD python -c "import httpx,sys; sys.exit(0 if httpx.get('http://localhost:8001/api/v1/health').status_code==200 else 1)"

CMD ["uvicorn", "app.qa.api:app", "--host", "0.0.0.0", "--port", "8001"]
