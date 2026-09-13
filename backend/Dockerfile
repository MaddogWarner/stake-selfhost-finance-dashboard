FROM python:3.12-slim AS runtime

WORKDIR /app

# Patch the base image. python:3.12-slim lags Debian security updates, so a
# freshly pulled base still carries fixed-in-Debian CVEs (perl-base, gzip,
# perl-Archive-Tar and friends). The publish gate blocks on fixable findings,
# so these have to be applied here rather than waived.
#
# Rebuilt without cache on every publish — see no-cache-filters in publish.yml.
# A cached layer would replay the package set from whenever it was first built
# and silently undo this.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# stake==0.13.0 is installed --no-deps to bypass its python-dotenv<0.14 pin (conflicts
# with pydantic-settings). Its actual runtime deps (aiohttp, inflection, single-version,
# pydantic, python-dotenv) are pinned in requirements.txt so `import stake` works.
# pip itself is upgraded first: the version bundled in the base image is old
# enough to carry its own advisories, and it travels in the shipped layer.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --no-deps stake==0.13.0
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN mkdir -p /data && chown appuser:appgroup /data

COPY . .

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
