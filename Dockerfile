# Multi-stage build for College Housing Platform
# Stage 1: Base image with common dependencies
FROM python:3.9-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    unzip \
    gnupg \
    ca-certificates \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Web application
FROM base AS web

# Copy application code
COPY . /app/

# Set user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Default command
CMD ["python", "app.py"]

# Stage 3: Scraper with Chrome
FROM base AS scraper

# Install Chrome dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation \
    libappindicator1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm-dev \
    libgtk-3-0 \
    libxshmfence-dev \
    xdg-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome version
ENV CHROME_VERSION=114.0.5735.90

# Install Chrome and ChromeDriver
RUN wget https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip && \
    wget https://chromedriver.storage.googleapis.com/${CHROME_VERSION}/chromedriver_linux64.zip && \
    unzip chrome-linux64.zip && \
    unzip chromedriver_linux64.zip && \
    mv chrome-linux64 /opt/chrome && \
    mv chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    ln -s /opt/chrome/chrome /usr/bin/google-chrome && \
    chmod +x /opt/chrome/chrome && \
    rm -rf *.zip

# Verify installation
RUN google-chrome --version && chromedriver --version

# Copy application code
COPY . /app/

# Set user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Default command for scraper
CMD ["python", "src/scraper.py"]
