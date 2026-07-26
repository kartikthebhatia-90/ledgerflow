from __future__ import annotations

import os

from cachelib.redis import RedisCache

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
GUEST_TOKEN_JWT_SECRET = os.environ["GUEST_TOKEN_JWT_SECRET"]
GUEST_TOKEN_JWT_AUDIENCE = "superset"
GUEST_TOKEN_JWT_EXP_SECONDS = 300

FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "DISABLE_EMBEDDED_SUPERSET_LOGOUT": True,
}

ENABLE_CORS = True
CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": ["*"],
    "origins": [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
}

TALISMAN_ENABLED = True
TALISMAN_CONFIG = {
    "content_security_policy": {
        "default-src": ["'self'"],
        "img-src": ["'self'", "data:", "blob:"],
        "worker-src": ["'self'", "blob:"],
        "connect-src": ["'self'", "http://127.0.0.1:8000", "http://localhost:8000"],
        "frame-ancestors": ["http://127.0.0.1:8000", "http://localhost:8000"],
    },
}

SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = False  # Local-only HTTP development. Use True behind HTTPS.

SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SUPERSET_METADATA_DATABASE_URI",
    "postgresql+psycopg2://superset:superset@superset-db:5432/superset",
)

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "ledgerflow_superset_",
    "CACHE_REDIS_HOST": "superset-cache",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_REDIS_DB": 1,
}
DATA_CACHE_CONFIG = CACHE_CONFIG
FILTER_STATE_CACHE_CONFIG = CACHE_CONFIG
EXPLORE_FORM_DATA_CACHE_CONFIG = CACHE_CONFIG

WTF_CSRF_ENABLED = True
PUBLIC_ROLE_LIKE = "Gamma"
ROW_LIMIT = 50000
