FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# Pin uv so rebuilding the Codespace does not silently change the package manager.
COPY --from=ghcr.io/astral-sh/uv:0.11.33 /uv /uvx /bin/
