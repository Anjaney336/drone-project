FROM python:3.12.11-slim

WORKDIR /app
COPY requirements.lock pyproject.toml README.md LICENSE ./
# requirements.lock carries its own --extra-index-url for the CPU-only torch wheels.
# opencv-python-headless is used rather than opencv-python precisely so this slim image
# does not need libGL and the rest of the GUI stack.
RUN python -m pip install --no-cache-dir -r requirements.lock
COPY src ./src
RUN python -m pip install --no-build-isolation --no-deps -e .

# Runtime data the service actually serves. Without models/ every model reports
# NOT_TRAINED; without data/demo the seeded dataset export has nothing to read.
COPY configs ./configs
COPY data/demo ./data/demo
COPY data/manifests ./data/manifests
COPY models ./models

# data/uploads is written at runtime, so it must exist and be owned by the app user.
RUN useradd --create-home --uid 10001 aeris \
    && mkdir -p /app/data/uploads /app/artifacts \
    && chown -R aeris:aeris /app/data /app/artifacts
USER aeris

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/api/v1/health', timeout=4).status == 200 else 1)"

CMD ["python", "-m", "uvicorn", "aeris.app.api:app", "--host", "0.0.0.0", "--port", "8501"]
