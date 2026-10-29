import os
from flask import Blueprint, Response, send_from_directory

docs_bp = Blueprint("docs", __name__)

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWAGGER_UI = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14"

DOCS_PAGE = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>URL Shortener API</title>
  <link rel="stylesheet" href="{SWAGGER_UI}/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="{SWAGGER_UI}/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({{ url: "/openapi.json", dom_id: "#swagger-ui", tryItOutEnabled: true }});
  </script>
</body>
</html>
"""


@docs_bp.route("/docs")
def docs():
    return Response(DOCS_PAGE, mimetype="text/html")


@docs_bp.route("/openapi.json")
def openapi_spec():
    return send_from_directory(APP_DIR, "openapi.json", mimetype="application/json")
