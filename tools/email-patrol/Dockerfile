FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
COPY email_patrol/ email_patrol/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "-m", "email_patrol.server", "--streamable"]
