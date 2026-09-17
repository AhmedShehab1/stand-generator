FROM python:3.12-slim

# Install system dependencies required by WeasyPrint and Pango
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    fontconfig \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code (including fonts/, templates/, engine/, static/)
COPY . .

# Expose default application port
EXPOSE 10000

# Run with tuned Gunicorn settings for 512MB RAM environments
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --workers 2 --timeout 60 --max-requests 500 --max-requests-jitter 50"]
