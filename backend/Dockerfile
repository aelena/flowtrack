FROM python:3.12-slim

WORKDIR /app

# Local development (docker compose) sets this to "true" so the test suite and
# linters are available inside the container. Production builds leave it false
# and get runtime dependencies only.
ARG INSTALL_DEV=false

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$INSTALL_DEV" = "true" ]; then \
      pip install --no-cache-dir -r requirements-dev.txt; \
    fi

COPY . .

RUN mkdir -p /app/storage

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
