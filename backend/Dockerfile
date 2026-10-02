FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN python -m venv /opt/venv
# stake==0.13.0 is installed --no-deps to bypass its python-dotenv<0.14 pin (conflicts
# with pydantic-settings). Its actual runtime deps (aiohttp, inflection, single-version,
# pydantic, python-dotenv) are pinned in requirements.txt so `import stake` works.
# Upgrade build tooling before installing dependencies. Only the final venv
# crosses into runtime, so superseded dependency layers are not shipped.
RUN /opt/venv/bin/python -m pip install --no-cache-dir --upgrade pip setuptools \
    && /opt/venv/bin/python -m pip install --no-cache-dir -r requirements.txt \
    && /opt/venv/bin/python -m pip install --no-cache-dir --no-deps stake==0.13.0
RUN /opt/venv/bin/python -m pip uninstall -y pip

FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH"

# Patch the base image. python:3.12-slim lags Debian security updates, so a
# freshly pulled base still carries fixed-in-Debian CVEs (perl-base, gzip,
# perl-Archive-Tar and friends). The publish gate blocks on fixable findings,
# so these have to be applied here rather than waived.
#
# Rebuilt without cache on every publish — see no-cache-filters in publish.yml.
# A cached layer would replay the package set from whenever it was first built
# and silently undo this.
RUN /usr/local/bin/python -m pip uninstall -y pip setuptools \
    && apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN mkdir -p /data && chown appuser:appgroup /data

COPY . .

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
