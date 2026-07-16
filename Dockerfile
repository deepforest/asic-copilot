# ==========================================
# Stage 1: Build the React static frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend

# Copy dependencies list and install
COPY frontend/package.json ./
RUN npm install

# Copy source files and compile React into static dist folder
COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Build the FastAPI python backend
# ==========================================
FROM python:3.11-slim
WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy backend dependency descriptors and install them
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy backend source code files
COPY main.py ./
COPY backend/ ./backend/

# Copy compiled React frontend assets from Stage 1
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Expose server port
EXPOSE 8000
ENV PORT=8000

# Run uvicorn web server using uv environment
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
