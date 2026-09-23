# M0/M1 placeholder for the llama.cpp server containers. Replaced in M2 by
# ghcr.io/ggml-org/llama.cpp:server with baked GGUF weights (see CLAUDE.md §3, §14 M2).
FROM python:3.11-slim
WORKDIR /srv

RUN pip install --no-cache-dir "fastapi>=0.115" "uvicorn[standard]>=0.30"
COPY scripts/inference_stub_server.py ./inference_stub_server.py

ENV PORT=8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/health').status==200 else 1)"

CMD ["sh", "-c", "uvicorn inference_stub_server:app --host 0.0.0.0 --port ${PORT}"]
