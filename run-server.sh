#!/usr/bin/env bash
set -euo pipefail
CS_API_KEY=${CS_API_KEY:-cs-secret}
CS_ALLOW_UNSECURED_ADMIN=${CS_ALLOW_UNSECURED_ADMIN:-1}
export CS_API_KEY
export CS_ALLOW_UNSECURED_ADMIN
uvicorn cs_web.main:app --reload
