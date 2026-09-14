# Build stage for Next.js frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install
COPY . .
RUN pnpm build

# Final stage
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies for psycopg2 and PDF processing
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Copy built frontend to backend static files if we want to serve it together
# Or we can serve them separately. Let's assume we serve them together for simplicity on Render.
COPY --from=frontend-builder /app/.next ./.next

# Ensure static directories exist
RUN mkdir -p backend/static/uploads backend/data

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Start command
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port $PORT"]
