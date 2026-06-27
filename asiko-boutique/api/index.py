"""
Vercel Serverless Entry Point for ASIKO Boutique.
Imports the Starlette app from app.main — Vercel wraps it as an ASGI function.
"""
from app.main import app
