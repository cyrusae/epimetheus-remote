FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .
COPY templates/ templates/

# Create SSH directory
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Create non-root user (optional, but good practice)
RUN useradd -m -u 1000 appuser && \
    mkdir -p /home/appuser/.ssh && \
    chown -R appuser:appuser /home/appuser/.ssh && \
    chmod 700 /home/appuser/.ssh

# Switch to non-root user for runtime (SSH key will be mounted)
USER appuser
WORKDIR /home/appuser/app

# Copy app files to user directory
COPY --chown=appuser:appuser app.py .
COPY --chown=appuser:appuser templates/ templates/

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health').read()"

# Run the application
CMD ["python", "-u", "app.py"]