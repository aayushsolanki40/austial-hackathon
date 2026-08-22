# Minimal image to boot the current Austial health-check scaffold.
#
# Note: backend/pyproject.toml declares `austial` via an editable local path
# dependency (`../../austial-py/packages/...`) for development, and that
# local checkout is currently AHEAD of the last PyPI release (0.1.5) --
# src/main.py imports `austial.orm.DataSource`, which only exists in the
# unreleased ORM rewrite on the local austial-py HEAD, not in the published
# wheel. Installing plain `austial` from PyPI therefore fails at import time.
#
# Workaround: the 8 austial-py wheels were built locally from the current
# austial-py checkout (`uv build --package <pkg> --wheel`) and vendored into
# ./vendor/ for this image to install from directly, instead of reaching out
# to austial-py's source tree (outside this build context) or to PyPI. If
# austial-py cuts a new release with these changes, switch back to
# `pip install austial>=<new-version>` and delete vendor/.
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# System packages for opencv-python and pytesseract (Phase 9 ML dependencies).
# opencv-python needs libGL and other imaging libs; pytesseract needs tesseract-ocr binary.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgl1 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY vendor ./vendor

# Install the vendored austial-py wheels (order doesn't matter, pip resolves
# from the local dir), plus every other runtime dependency `pyproject.toml`
# declares under `[project.dependencies]` (kept in sync with that list by
# hand -- this image doesn't run `uv sync` itself, see the note above on why).
RUN pip install --no-cache-dir ./vendor/*.whl \
    "asyncpg>=0.29.0" \
    "passlib[bcrypt]>=1.7.4" \
    "bcrypt<4.1" \
    "python-jose[cryptography]>=3.3.0" \
    "pydantic[email]>=2.0.0" \
    "alembic>=1.13.0" \
    "celery[redis]>=5.4.0" \
    "redis>=5.0.0" \
    "boto3>=1.34.0" \
    "reportlab>=4.2.0" \
    "scikit-learn>=1.5" \
    "xgboost>=2.1" \
    "joblib>=1.4" \
    "pytesseract>=0.3.13" \
    "opencv-python>=4.10" \
    && rm -rf ./vendor

COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY src ./src

EXPOSE 8000

CMD ["python", "src/main.py"]
