# Build Stage
FROM python:3.12-slim AS build

# Set the working directory in the container
WORKDIR /app

# Copy all needed files, everything else gets blocked in .dockerignore
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt && rm -rf /root/.cache

# Runtime Stage
FROM python:3.12-slim AS runtime

# Set the working directory in the container
WORKDIR /app

# Copy installed dependencies from the build stage
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /app/ ./
COPY --from=build /usr/local/bin /usr/local/bin

# Expose the port for Flask
EXPOSE 8000

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "main:app"]