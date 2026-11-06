# The ingestion image: the database extractor and the clickstream consumer.
# Build from the repo root, so .dockerignore applies:
#     docker build -f ingestion/Dockerfile -t <name>:<tag> .
# Run the extractor (the default) or the consumer (command override):
#     docker run ... <image>
#     docker run ... <image> python consume_clickstream.py

# Pinned at both ends: the Python patch release and the Debian release. A
# floating tag such as python:3.12 is a different image next month.
FROM python:3.12.12-slim-bookworm

# No .pyc files in a filesystem thrown away at exit, and logs printed as they
# happen, so a crashed container's log is not empty.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies before the code, so editing a script does not reinstall them.
# Every package is pinned in requirements.txt.
COPY ingestion/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 ingest

COPY ingestion/extract_orders.py ingestion/consume_clickstream.py \
     ingestion/clickstream.schema.json ./

# Nothing is installed at run time, so nothing needs root.
USER ingest

# Credentials are never in the image. Mount the application default login
# read-only and point GOOGLE_APPLICATION_CREDENTIALS at it at run time.
# Exec form, so the process receives the stop signal directly.
CMD ["python", "extract_orders.py"]
