FROM python:3.12.11-slim

WORKDIR /app
COPY requirements.lock pyproject.toml README.md LICENSE ./
RUN python -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.lock
COPY src ./src
RUN python -m pip install --no-cache-dir --no-build-isolation --no-deps -e .

RUN useradd --create-home --uid 10001 aeris
USER aeris

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/api/v1/health', timeout=4).status == 200 else 1)"

CMD ["python", "-m", "uvicorn", "aeris.app.api:app", "--host", "0.0.0.0", "--port", "8501"]
