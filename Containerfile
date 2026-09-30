# Mismo esquema que craic (Podman rootless). Escucha en 8001 para no chocar con craic (8000):
#   podman build -t webpersonal .
#   podman run -d --name webpersonal -p 127.0.0.1:8001:8001 \
#       -v webpersonal-contenido:/app/contenido -e BLOG_CLAVE=una-clave-larga webpersonal
# El volumen guarda las entradas y fotos que subas desde /admin (sobreviven a reconstruir la imagen).
FROM docker.io/library/python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY templates ./templates
COPY static ./static
COPY contenido ./contenido

VOLUME ["/app/contenido"]

EXPOSE 8001
CMD ["uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers", "--forwarded-allow-ips", "*"]
