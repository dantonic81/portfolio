# Build Stage
FROM python:3.12-slim AS build

# Set the working directory in the container
WORKDIR /app

# Copy all needed files, everything else gets blocked in .dockerignore
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Runtime Stage
FROM python:3.12-slim AS runtime

# Set the working directory in the container
WORKDIR /app

# Copy installed dependencies from the build stage
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /app/ ./

# Run the application
CMD [ "python", "etl.py" ]