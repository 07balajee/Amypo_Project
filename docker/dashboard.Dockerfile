FROM python:3.11-slim
WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir ".[dashboard]"

COPY config.yaml ./

EXPOSE 8501
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD python -c "import httpx,sys; sys.exit(0 if httpx.get('http://localhost:8501/_stcore/health').status_code==200 else 1)"

CMD ["streamlit", "run", "app/dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
