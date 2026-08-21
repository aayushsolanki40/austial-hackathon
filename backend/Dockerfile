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

COPY vendor ./vendor

# Install the vendored austial-py wheels (order doesn't matter, pip resolves
# from the local dir), plus the app's other runtime dependency.
RUN pip install --no-cache-dir ./vendor/*.whl "asyncpg>=0.29.0" \
    && rm -rf ./vendor

COPY src ./src

EXPOSE 8000

CMD ["python", "src/main.py"]
