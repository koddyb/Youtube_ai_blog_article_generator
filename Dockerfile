# Multi-stage Dockerfile pour Django AI Blog App
# Stage 1: Builder
FROM python:3.14-slim as builder

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements et installer dépendances Python
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.14-slim

WORKDIR /app

# Installer uniquement les runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Créer utilisateur non-root pour sécurité
RUN useradd -m -u 1000 appuser

# Copier les packages Python depuis le builder
COPY --from=builder /root/.local /home/appuser/.local

# Copier le code de l'application
COPY . .

# Changer propriété des fichiers
RUN chown -R appuser:appuser /app

# Passer à l'utilisateur non-root
USER appuser

# Ajouter le dossier local au PATH
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Port sur lequel Gunicorn écoute (Traefik fera le reverse proxy)
EXPOSE 8000

# Commande de démarrage
CMD ["gunicorn", "ai_blog_app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
