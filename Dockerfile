FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    unzip \
    gnupg \
    ca-certificates \
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
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome version
ENV CHROME_VERSION=114.0.5735.90

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
RUN ls -la /usr/local/bin/chromedriver && \
    ls -la /usr/bin/google-chrome && \
    google-chrome --version

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ .

# Disable buffering for real-time logs
ENV PYTHONUNBUFFERED=1

CMD ["python", "scraper.py"]
