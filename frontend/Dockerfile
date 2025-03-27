FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY frontend.requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r frontend.requirements.txt
RUN pip install --upgrade streamlit

# Copy the entire repository to ensure proper module imports
COPY . /app/

# Make the healthcheck script executable
RUN chmod +x /app/frontend/healthcheck.py

# Expose port for Streamlit
EXPOSE 8501

# Set environment variables
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_STATIC_SERVING=true
ENV ENABLE_MOCK_FALLBACKS=true
ENV SHOW_API_ERRORS=true

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "/app/frontend/healthcheck.py"]

# Run the application directly with streamlit
CMD ["streamlit", "run", "--server.enableCORS=false", "--server.enableXsrfProtection=false", "/app/frontend/app.py"]