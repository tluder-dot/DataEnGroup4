# The dbt runner, with our transform/ project copied in: the image alone
# rebuilds silver and gold. Build from the repo root, so .dockerignore applies:
#     docker build -f transform/Dockerfile -t <name>:<tag> .
# Run:
#     docker run ... <image> build

# Pinned at both ends, like the ingestion image.
FROM python:3.12.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DBT_PROFILES_DIR=/usr/app

# Every package pinned, dbt-core included: pinning only the adapter let pip
# pick dbt-core 1.13.0-rc1, a release candidate, on 6 November.
COPY transform/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && useradd --create-home --uid 10001 dbt

WORKDIR /usr/app
COPY transform/ ./

# Packages are fetched at build time, so a run needs no network but
# BigQuery's. dbt writes target/ and logs/ here at run time, so the user owns it.
RUN dbt deps && chown -R dbt /usr/app

USER dbt

# The entrypoint is dbt, so "build", "test" or "debug" is all a run passes.
ENTRYPOINT ["dbt"]
CMD ["--version"]
