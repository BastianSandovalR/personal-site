# Kernel de Bastian

Blog personal y perfil profesional servidos **solo con HTML**: sin CSS y sin JavaScript.
Colores, columnas y menús salen de atributos y etiquetas HTML (`bgcolor`, tablas, `<details>`, `<marquee>`).

- **Responsivo sin CSS:** el servidor detecta si la visita viene de un celular (`Sec-CH-UA-Mobile` o user-agent) y arma la versión adecuada.
- **Modo noche sin JavaScript:** un enlace guarda la preferencia en una cookie desde el servidor.
- **Panel de publicación** (`/admin`, HTTP Basic + token CSRF) con formularios HTML: escribir, editar, borradores y subida de fotos. Las fotos se reducen a 1600 px y se les eliminan los metadatos EXIF (incluido el GPS).
- **Entradas en texto plano** (`contenido/entradas/*.txt`) con un formato mínimo propio. Ver [`contenido/COMO_PUBLICAR.md`](contenido/COMO_PUBLICAR.md).
- **RSS** en `/feed.xml`.

## Correr en local

```bash
python3 -m venv venv && venv/bin/pip install -r requirements.txt
BLOG_CLAVE=prueba-local venv/bin/python -m uvicorn main:app --app-dir src --reload --port 8001
```

Sitio en http://localhost:8001. Panel en http://localhost:8001/admin (usuario `bastian`).

## Desplegar (Podman)

```bash
podman build -t webpersonal .
podman run -d --name webpersonal -p 127.0.0.1:8001:8001 \
    -v webpersonal-contenido:/app/contenido --env-file ~/.config/webpersonal.env webpersonal
```

`~/.config/webpersonal.env` contiene `BLOG_CLAVE=...`. El volumen guarda lo publicado desde `/admin`.

Stack: Python, FastAPI, Jinja2, Pillow, Podman.
