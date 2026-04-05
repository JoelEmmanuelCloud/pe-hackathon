FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files first for layer caching
COPY pyproject.toml .
COPY .python-version .

# Install dependencies
RUN uv sync --no-dev

# Copy app source
COPY . .

EXPOSE 5000

CMD ["uv", "run", "run.py"]
