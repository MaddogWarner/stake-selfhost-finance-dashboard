FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
# stake==0.13.0 is installed --no-deps to bypass its python-dotenv<0.14 pin (conflicts
# with pydantic-settings). Its actual runtime deps (aiohttp, inflection, single-version,
# pydantic, python-dotenv) are pinned in requirements.txt so `import stake` works.
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --no-deps stake==0.13.0
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN mkdir -p /data && chown appuser:appgroup /data

COPY . .

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
