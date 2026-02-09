# Build Stage 1: Frontend
FROM node:20-slim AS build-frontend
WORKDIR /app/gui-web
COPY gui-web/package*.json ./
RUN npm install
COPY gui-web/ ./
RUN npm run build

# Build Stage 2: Backend & Runner
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files
COPY backend/ ./backend/
COPY uese/ ./uese/
COPY profiles/ ./profiles/

# Copy built frontend from Stage 1
COPY --from=build-frontend /app/gui-web/dist ./gui-web/dist

# Expose port (Cloud Run uses PORT env var)
ENV PORT 8080
EXPOSE 8080

# Command to run the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
