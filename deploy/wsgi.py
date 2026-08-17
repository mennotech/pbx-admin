"""WSGI/CLI entrypoint. Used by gunicorn (``wsgi:app``) and ``flask --app wsgi``."""

from pbx_admin import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
