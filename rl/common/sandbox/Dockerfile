ARG PIXCELL_SANDBOX_SPEC_SHA256
FROM python@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONNOUSERSITE=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        build-essential \
        cmake \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /opt/pixcell-sandbox/requirements.txt
RUN python -m pip wheel \
    --wheel-dir /opt/pixcell-sandbox/wheels \
    --requirement /opt/pixcell-sandbox/requirements.txt

FROM python@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64
ARG PIXCELL_SANDBOX_SPEC_SHA256

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONNOUSERSITE=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/pixcell-sandbox/wheels /opt/pixcell-sandbox/wheels
RUN python -m pip install \
    --no-index \
    --find-links /opt/pixcell-sandbox/wheels \
    gdsfactory==9.20.7 \
    gdstk==0.9.0 \
    kfactory==2.0.1 \
    klayout==0.30.6 \
    numpy==2.4.6 \
    scipy==1.18.0 \
    scikit-image==0.26.0 \
    shapely==2.1.2 \
    && rm -rf /opt/pixcell-sandbox/wheels \
    && python - <<'PY'
from importlib.metadata import version

import gdsfactory
import gdstk
import kfactory

assert version("gdsfactory") == "9.20.7"
assert version("gdstk") == "0.9.0"
assert version("kfactory") == "2.0.1"
PY

COPY supervise.py /usr/local/lib/pixcell/supervise.py

LABEL org.qpg-mit.pixcell.role="model-program-evaluator" \
    org.qpg-mit.pixcell.sandbox-spec-sha256="${PIXCELL_SANDBOX_SPEC_SHA256}"
