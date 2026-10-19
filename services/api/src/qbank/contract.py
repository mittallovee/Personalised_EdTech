"""The API contract: the OpenAPI document generated from the code (API style guide §1).

It is committed at ``api/openapi.json`` so every API change is visible in review, and clients
(the web app's generated client now, mobile apps and partners later) are built from it.
"""

import json

from qbank.core.config import SERVICE_ROOT, AppEnv, Settings
from qbank.main import create_app

OPENAPI_FILE = SERVICE_ROOT.parents[1] / "api" / "openapi.json"

# Building the app needs a database URL, but generating the document never connects.
_NO_DATABASE = "postgresql+psycopg://openapi:unused@127.0.0.1:1/none"


def render_openapi() -> str:
    app = create_app(Settings(app_env=AppEnv.TEST, database_url=_NO_DATABASE))
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"
