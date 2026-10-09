# WF-008. See 02-architecture.md section 11. Build from the repo root:
#   docker build -f infra/docker/Dockerfile -t hermi .
# shortcut: base images are pinned by tag, not digest. Pin both python:3.13-slim stages by digest
# when the first release is cut (Dependabot's docker ecosystem keeps the digest fresh).

ARG BASE_REGISTRY=docker.io/library
FROM ${BASE_REGISTRY}/node:22-slim AS web
WORKDIR /src
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/
COPY packages packages
COPY locales locales
COPY app-buildout/brand app-buildout/brand
RUN npm ci
COPY apps/web apps/web
RUN npm run build --workspace apps/web

FROM ${BASE_REGISTRY}/python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=0 UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY apps/api apps/api
COPY apps/worker apps/worker
# Wheels only: the slim image has no compiler, so a source-only dependency fails the build.
RUN uv sync --frozen --no-dev --all-packages --no-cache

FROM ${BASE_REGISTRY}/python:3.13-slim
ARG RELEASE_SHA=dev
ENV RELEASE_SHA=${RELEASE_SHA} \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp \
    TMPDIR=/tmp
# Pick up Debian security fixes newer than the base image (libpcre2 CVE-2026-103111). Drop pip and
# the packaging tools the runtime never uses: their vendored msgpack, urllib3 and setuptools copies
# carry HIGH advisories that Trivy reports against the image.
RUN apt-get update \
    && apt-get -y --no-install-recommends upgrade \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/local/lib/python3.13/site-packages/pip* /usr/local/lib/python3.13/site-packages/setuptools* \
        /usr/local/lib/python3.13/site-packages/pkg_resources /usr/local/lib/python3.13/site-packages/wheel* \
        /usr/local/lib/python3.13/ensurepip/_bundled /usr/local/bin/pip /usr/local/bin/pip3* \
    && useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin hermi
WORKDIR /app
COPY --from=builder /app /app
COPY --from=web /src/apps/web/dist /app/apps/web/dist
USER 10001
EXPOSE 8100
# The slim image has no curl; the standard library is enough.
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request as u; u.urlopen('http://127.0.0.1:%s/health/live' % os.environ.get('PORT','8100'), timeout=2)"]
ENTRYPOINT ["hermi"]
# Bind all interfaces inside the container; the platform overrides the command for other roles.
CMD ["api", "--host", "0.0.0.0"]
