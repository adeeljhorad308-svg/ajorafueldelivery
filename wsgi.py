"""WSGI entry point: `flask --app wsgi run` / gunicorn wsgi:app."""

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402 (must load .env first)

app = create_app()
