"""Panel /admin para publicar desde el navegador (tambien desde el celular).

Se activa solo si existe la variable de entorno BLOG_CLAVE.
Usuario: BLOG_USUARIO (por defecto "bastian").
"""
import hashlib
import hmac
import os
import secrets
import shutil
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from PIL import Image, ImageOps, UnidentifiedImageError

import contenido as ct

USUARIO = os.environ.get('BLOG_USUARIO', 'bastian')
CLAVE = os.environ.get('BLOG_CLAVE', '')

MAX_FOTO_BYTES = 25 * 1024 * 1024
LADO_MAXIMO = 1600
LADO_MINIATURA = 480
Image.MAX_IMAGE_PIXELS = 80_000_000

_basic = HTTPBasic(realm='Kernel de Bastian', auto_error=False)


def autenticar(cred: HTTPBasicCredentials | None = Depends(_basic)) -> str:
    if not CLAVE:
        raise HTTPException(status_code=404)  # sin clave configurada, el panel no existe
    if cred is None:
        raise HTTPException(status_code=401, headers={'WWW-Authenticate': 'Basic realm="Kernel de Bastian"'})
    usuario_ok = secrets.compare_digest(cred.username.encode(), USUARIO.encode())
    clave_ok = secrets.compare_digest(cred.password.encode(), CLAVE.encode())
    if not (usuario_ok and clave_ok):
        raise HTTPException(status_code=401, headers={'WWW-Authenticate': 'Basic realm="Kernel de Bastian"'})
    return cred.username


def token_csrf() -> str:
    # El navegador reenvia la clave Basic a cualquier sitio que haga POST aqui;
    # este token (que otro sitio no puede leer) evita que publiquen o borren en tu nombre.
    return hmac.new(CLAVE.encode(), b'csrf-kernel', hashlib.sha256).hexdigest()


def revisar_token(token: str):
    if not hmac.compare_digest(token, token_csrf()):
        raise HTTPException(status_code=403, detail='Token del formulario inválido. Recarga la página.')


def procesar_foto(subida: UploadFile, base: str) -> str | None:
    """Guarda la foto achicada a 1600 px, sin metadatos (GPS incluido), y una miniatura."""
    datos = subida.file.read(MAX_FOTO_BYTES + 1)
    if not datos or len(datos) > MAX_FOTO_BYTES:
        return None
    ruta_tmp = ct.FOTOS / f'.subida-{secrets.token_hex(6)}'
    ruta_tmp.write_bytes(datos)
    try:
        with Image.open(ruta_tmp) as img:
            img = ImageOps.exif_transpose(img)  # respeta la rotacion del celular
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            nombre = base
            n = 1
            while (ct.FOTOS / f'{nombre}.jpg').exists():
                n += 1
                nombre = f'{base}-{n}'
            grande = img.copy()
            grande.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
            grande.save(ct.FOTOS / f'{nombre}.jpg', 'JPEG', quality=84, optimize=True, progressive=True)
            mini = img.copy()
            mini.thumbnail((LADO_MINIATURA, LADO_MINIATURA))
            mini.save(ct.FOTOS / f'{nombre}_min.jpg', 'JPEG', quality=80, optimize=True)
        return f'{nombre}.jpg'
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return None
    finally:
        ruta_tmp.unlink(missing_ok=True)


def escribir(ruta: Path, texto: str):
    tmp = ruta.with_suffix('.tmp')
    tmp.write_text(texto, encoding='utf-8')
    tmp.replace(ruta)


def crear_router(templates, contexto) -> APIRouter:
    router = APIRouter(prefix='/admin', dependencies=[Depends(autenticar)])

    def pagina(request: Request, nombre: str, **extra):
        return templates.TemplateResponse(
            request, nombre, contexto(request) | {'token': token_csrf(), 'categorias': ct.CATEGORIAS, 'noindex': True} | extra,
            headers={'Cache-Control': 'no-store'},
        )

    @router.get('')
    def panel(request: Request, ok: str = ''):
        return pagina(request, 'admin/panel.html', entradas=ct.todas(incluir_borradores=True), ok=ok)

    @router.get('/nueva')
    def nueva(request: Request):
        return pagina(request, 'admin/editor.html', entrada=None, hoy=date.today())

    @router.get('/editar/{slug}')
    def editar(request: Request, slug: str):
        entrada = ct.buscar(slug, incluir_borradores=True)
        if not entrada:
            raise HTTPException(status_code=404)
        return pagina(request, 'admin/editor.html', entrada=entrada, hoy=entrada.fecha)

    @router.get('/vista/{slug}')
    def vista_previa(request: Request, slug: str):
        entrada = ct.buscar(slug, incluir_borradores=True)
        if not entrada:
            raise HTTPException(status_code=404)
        return pagina(request, 'entrada.html', entrada=entrada, anterior=None, siguiente=None, previa=True)

    @router.post('/guardar')
    def guardar(
        token: str = Form(...),
        slug_original: str = Form(''),
        titulo: str = Form(...),
        fecha: str = Form(''),
        categoria: str = Form('fragmentos'),
        categoria_nueva: str = Form(''),
        texto: str = Form(''),
        borrador: bool = Form(False),
        fotos: list[UploadFile] = File(default=[]),
    ):
        revisar_token(token)
        titulo = titulo.strip()
        if not titulo:
            raise HTTPException(status_code=400, detail='La entrada necesita un título.')
        try:
            dia = date.fromisoformat(fecha)
        except ValueError:
            dia = date.today()
        # Una categoria nueva escrita a mano gana sobre la elegida en la lista
        cat = ct.slug_de(categoria_nueva.strip() or categoria).replace('-', '_')

        ct.ENTRADAS.mkdir(parents=True, exist_ok=True)
        ct.FOTOS.mkdir(parents=True, exist_ok=True)
        existente = ct.buscar(slug_original, incluir_borradores=True) if slug_original else None
        if existente:
            slug = existente.slug
        else:
            base = ct.slug_de(titulo)
            slug, n = base, 1
            while (ct.ENTRADAS / f'{slug}.txt').exists():
                n += 1
                slug = f'{base}-{n}'

        # Las fotos nuevas se agregan al final del texto; luego se pueden mover a mano
        lineas_fotos = []
        for subida in (f for f in fotos if f.filename):
            nombre = procesar_foto(subida, f'{dia.isoformat()}-{slug}'[:70])
            if nombre:
                lineas_fotos.append(f'[foto: {nombre} | ]')
        cuerpo = texto.strip()
        if lineas_fotos:
            cuerpo = (cuerpo + '\n\n' if cuerpo else '') + '\n\n'.join(lineas_fotos)

        escribir(ct.ENTRADAS / f'{slug}.txt', ct.serializar(titulo, dia, cat, borrador, cuerpo))
        return RedirectResponse(f'/admin/editar/{slug}?guardado=1', status_code=303)

    @router.post('/borrar/{slug}')
    def borrar(slug: str, token: str = Form(...), confirmar: bool = Form(False)):
        revisar_token(token)
        entrada = ct.buscar(slug, incluir_borradores=True)
        if not entrada or not confirmar:
            return RedirectResponse(f'/admin/editar/{slug}', status_code=303)
        # No se borra de verdad: va a la papelera por si fue un error
        ct.PAPELERA.mkdir(parents=True, exist_ok=True)
        marca = datetime.now().strftime('%Y%m%d-%H%M%S')
        shutil.move(ct.ENTRADAS / f'{slug}.txt', ct.PAPELERA / f'{slug}.{marca}.txt')
        return RedirectResponse('/admin?ok=borrada', status_code=303)

    return router
