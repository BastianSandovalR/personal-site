import json
import random
from collections import Counter
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

import admin
import contenido as ct

# Rutas absolutas: funciona igual si se lanza desde src/, desde la raiz o dentro de un contenedor
BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / 'static'

app = FastAPI(title='Kernel de Bastian', docs_url=None, redoc_url=None, openapi_url=None)
templates = Jinja2Templates(directory=BASE / 'templates')
app.mount('/static', StaticFiles(directory=STATIC), name='static')
ct.FOTOS.mkdir(parents=True, exist_ok=True)
app.mount('/fotos', StaticFiles(directory=ct.FOTOS), name='fotos')

# Se lee una sola vez al arrancar, no en cada visita
CITAS = json.loads((BASE / 'src' / 'data' / 'citas.json').read_text(encoding='utf-8'))

ULTIMA_ACTUALIZACION = '30 de septiembre de 2026'
POR_PAGINA = 12

# Colores del sitio. Sin CSS, se aplican con atributos HTML (bgcolor, text, link...)
TEMAS = {
    'dia': {
        'fondo': '#FFFFFF', 'texto': '#000000', 'tenue': '#555555',
        'panel': '#C0C0C0', 'hundido': '#FFFFFF', 'borde': '#808080',
        'barra': '#1F4D2B', 'barra_texto': '#FFFFFF', 'titulo': '#1F4D2B',
        'enlace': '#0000CC', 'visitado': '#551A8B', 'activo': '#CC0000',
        'rio': '#0077FF', 'rio_texto': '#FFFFFF', 'codigo': '#EFEFEF',
    },
    # Guardia nocturna: como una torre de vigilancia de incendios a las 3 AM
    'noche': {
        'fondo': '#000000', 'texto': '#E6DCC6', 'tenue': '#9A917F',
        'panel': '#1C1C1C', 'hundido': '#0A0A0A', 'borde': '#4A4A4A',
        'barra': '#3A1D00', 'barra_texto': '#FFB000', 'titulo': '#FFB000',
        'enlace': '#8CC4FF', 'visitado': '#C9A0FF', 'activo': '#FF6A3D',
        'rio': '#003B80', 'rio_texto': '#8CC4FF', 'codigo': '#1C1C1C',
    },
}

PALABRAS_MOVIL = ('mobile', 'android', 'iphone', 'ipad', 'ipod')


def es_movil(request: Request) -> bool:
    forzada = request.cookies.get('vista')
    if forzada in ('pc', 'movil'):
        return forzada == 'movil'
    # Chrome/Edge/Opera mandan este header; Firefox y Safari no, ahi se mira el user-agent
    hint = request.headers.get('sec-ch-ua-mobile')
    if hint is not None:
        return hint == '?1'
    user_agent = request.headers.get('user-agent', '').lower()
    return any(palabra in user_agent for palabra in PALABRAS_MOVIL)


def categorias_publicas() -> list[tuple[str, str, int]]:
    conteo = Counter(e.categoria for e in ct.todas())
    orden = list(ct.CATEGORIAS) + sorted(c for c in conteo if c not in ct.CATEGORIAS)
    return [(c, ct.CATEGORIAS.get(c, c.replace('_', ' ').capitalize()), conteo[c]) for c in orden if conteo[c]]


def contexto(request: Request) -> dict:
    tema = request.cookies.get('tema', 'dia')
    movil = es_movil(request)
    return {
        'movil': movil,
        'tema': tema if tema in TEMAS else 'dia',
        'c': TEMAS.get(tema, TEMAS['dia']),
        'ancho': '100%' if movil else '820',
        'ruta': request.url.path,
        'ultima_actualizacion': ULTIMA_ACTUALIZACION,
        'cv_pdf': (STATIC / 'cv.pdf').is_file(),
        'vista_forzada': request.cookies.get('vista') in ('pc', 'movil'),
    }


def render(request: Request, nombre: str, status_code: int = 200, **extra):
    return templates.TemplateResponse(request, nombre, contexto(request) | extra, status_code=status_code)


@app.middleware('http')
async def cabeceras(request: Request, call_next):
    respuesta = await call_next(request)
    # La misma URL cambia segun el dispositivo y las preferencias: los caches deben saberlo
    respuesta.headers['Vary'] = 'User-Agent, Sec-CH-UA-Mobile, Cookie'
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    respuesta.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return respuesta


@app.exception_handler(StarletteHTTPException)
async def error_http(request: Request, exc: StarletteHTTPException):
    # 401 necesita su cabecera para que el navegador pida la clave; archivos faltantes no necesitan pagina
    if exc.status_code == 401 or request.url.path.startswith(('/static', '/fotos')):
        return await http_exception_handler(request, exc)
    detalle = exc.detail if exc.status_code in (400, 403) else None
    return render(request, 'error.html', exc.status_code, codigo=exc.status_code, detalle=detalle)


@app.get('/', response_class=HTMLResponse)
def inicio(request: Request):
    entradas = ct.todas()
    return render(
        request, 'inicio.html',
        recientes=entradas[:6],
        cita=random.choice(CITAS),
        categorias=categorias_publicas(),
        total=len(entradas),
    )


@app.get('/bitacora', response_class=HTMLResponse)
def bitacora(request: Request, cat: str = '', pagina: int = 1):
    entradas = ct.todas()
    if cat:
        entradas = [e for e in entradas if e.categoria == cat]
        if not entradas:
            raise HTTPException(status_code=404)
    paginas = max(1, -(-len(entradas) // POR_PAGINA))
    pagina = min(max(1, pagina), paginas)
    return render(
        request, 'bitacora.html',
        entradas=entradas[(pagina - 1) * POR_PAGINA: pagina * POR_PAGINA],
        cat=cat,
        nombre_cat=ct.CATEGORIAS.get(cat, cat.replace('_', ' ').capitalize()) if cat else '',
        categorias=categorias_publicas(),
        pagina=pagina,
        paginas=paginas,
    )


@app.get('/entrada/{slug}', response_class=HTMLResponse)
def entrada(request: Request, slug: str):
    entradas = ct.todas()
    actual = next((i for i, e in enumerate(entradas) if e.slug == slug), None)
    if actual is None:
        raise HTTPException(status_code=404)
    return render(
        request, 'entrada.html',
        entrada=entradas[actual],
        # la lista va de mas nueva a mas antigua
        siguiente=entradas[actual - 1] if actual > 0 else None,
        anterior=entradas[actual + 1] if actual + 1 < len(entradas) else None,
    )


@app.get('/galeria', response_class=HTMLResponse)
def galeria(request: Request):
    fotos = [(foto, e) for e in ct.todas() for foto in e.fotos]
    return render(request, 'galeria.html', fotos=fotos, columnas=2 if es_movil(request) else 4)


@app.get('/profesional', response_class=HTMLResponse)
def profesional(request: Request):
    return render(request, 'profesional.html')


@app.get('/contact')
def contacto_antiguo():
    return RedirectResponse('/profesional#contacto', status_code=301)


@app.get('/preferencias')
def preferencias(request: Request, tema: str = '', vista: str = '', volver: str = '/'):
    # Solo se vuelve a rutas de este mismo sitio
    if not volver.startswith('/') or volver.startswith('//') or '\\' in volver:
        volver = '/'
    respuesta = RedirectResponse(volver, status_code=303)
    un_anio = 60 * 60 * 24 * 365
    if tema in TEMAS:
        respuesta.set_cookie('tema', tema, max_age=un_anio, samesite='lax', httponly=True)
    if vista in ('pc', 'movil'):
        respuesta.set_cookie('vista', vista, max_age=un_anio, samesite='lax', httponly=True)
    elif vista == 'auto':
        respuesta.delete_cookie('vista')
    return respuesta


@app.get('/feed.xml')
def feed(request: Request):
    entradas = ct.todas()[:20]
    base = str(request.base_url).rstrip('/')
    ahora = format_datetime(datetime.now(timezone.utc))
    return templates.TemplateResponse(
        request, 'feed.xml',
        {'entradas': entradas, 'base': base, 'ahora': ahora, 'rfc822': lambda d: format_datetime(
            datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc))},
        media_type='application/rss+xml; charset=utf-8',
    )


@app.get('/robots.txt', response_class=HTMLResponse)
def robots():
    return HTMLResponse('User-agent: *\nDisallow: /admin\n', media_type='text/plain')


app.include_router(admin.crear_router(templates, lambda r: contexto(r) | {'categorias_usadas': categorias_publicas()}))
