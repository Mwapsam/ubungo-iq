# Use an official Python runtime based on Debian 12 "bookworm" as a parent image.
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on 

RUN apt-get update && apt-get install -y libheif-dev

RUN pip install poetry

COPY pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root 

COPY . /app/

EXPOSE 8000
