"""Entradas del blog guardadas como archivos .txt en contenido/entradas/.

Formato de un archivo (ver contenido/COMO_PUBLICAR.md):

    titulo: Rutina de boxeo
    fecha: 2026-09-08
    categoria: bitacoras
    estado: publicado          (o "borrador")
    ---
    Texto con **negrita**, *cursiva*, `codigo` y [links](https://...).

    ## Subtitulo
    > una cita
    - un item de lista
    [foto: archivo.jpg | pie de foto]
"""
import html
import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from markupsafe import Markup
from PIL import Image

BASE = Path(__file__).resolve().parent.parent
CONTENIDO = Path(os.environ.get('CONTENIDO_DIR', BASE / 'contenido'))
ENTRADAS = CONTENIDO / 'entradas'
FOTOS = CONTENIDO / 'fotos'
PAPELERA = CONTENIDO / 'papelera'

CATEGORIAS = {
    'ingenieria': 'Ingeniería y sistemas',
    'bitacoras': 'Bitácoras de vida',
    'reflexiones': 'Reflexiones y cartas',
    'fragmentos': 'Fragmentos sueltos',
    'fotos': 'Archivo fotográfico',
}

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


@dataclass
class Foto:
    archivo: str
    pie: str

    @property
    def url(self) -> str:
        return f'/fotos/{self.archivo}'

    @property
    def url_miniatura(self) -> str:
        mini = Path(self.archivo).stem + '_min.jpg'
        return f'/fotos/{mini}' if (FOTOS / mini).is_file() else self.url

    @property
    def ancho(self) -> int:
        return medidas(self.archivo)[0]


@dataclass
class Entrada:
    slug: str
    titulo: str
    fecha: date
    categoria: str
    borrador: bool
    texto: str
    bloques: list = field(default_factory=list)

    @property
    def nombre_categoria(self) -> str:
        return CATEGORIAS.get(self.categoria, self.categoria.replace('_', ' ').capitalize())

    @property
    def fecha_larga(self) -> str:
        return f'{self.fecha.day} de {MESES[self.fecha.month - 1]} de {self.fecha.year}'

    @property
    def archivo(self) -> str:
        return self.slug.replace('-', '_') + '.txt'

    @property
    def fotos(self) -> list[Foto]:
        return [b[1] for b in self.bloques if b[0] == 'foto' and (FOTOS / b[1].archivo).is_file()]

    @property
    def resumen(self) -> str:
        for bloque in self.bloques:
            if bloque[0] == 'p':
                plano = re.sub(r'<[^>]+>', '', str(bloque[1]))
                plano = html.unescape(plano)
                return plano if len(plano) <= 220 else plano[:217].rsplit(' ', 1)[0] + '…'
        return ''


# ---------- Formato de texto -> bloques ----------

_LINK = re.compile(r'\[([^\]]+)\]\(((?:https?://|mailto:|/)[^\s)]+)\)')
_NEGRITA = re.compile(r'\*\*(.+?)\*\*')
_CURSIVA = re.compile(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])')
_FOTO = re.compile(r'^\[foto:\s*([^|\]]+?)\s*(?:\|\s*(.*?))?\s*\]$')


def en_linea(texto: str) -> Markup:
    """Escapa el HTML y aplica **negrita**, *cursiva*, `codigo` y [links](url)."""
    partes = texto.split('`')
    salida = []
    for i, parte in enumerate(partes):
        parte = html.escape(parte, quote=False)
        if i % 2 == 1 and i < len(partes) - 1:
            salida.append(f'<code>{parte}</code>')
            continue
        if i % 2 == 1:  # backtick sin cerrar
            parte = '`' + parte
        parte = _LINK.sub(lambda m: f'<a href="{html.escape(m[2])}">{m[1]}</a>', parte)
        parte = _NEGRITA.sub(r'<b>\1</b>', parte)
        parte = _CURSIVA.sub(r'<i>\1</i>', parte)
        salida.append(parte)
    return Markup(''.join(salida))


def parsear_cuerpo(texto: str) -> list:
    bloques = []
    lineas = texto.replace('\r\n', '\n').split('\n')
    i = 0
    parrafo: list[str] = []

    def cerrar_parrafo():
        if parrafo:
            bloques.append(('p', en_linea(' '.join(parrafo))))
            parrafo.clear()

    while i < len(lineas):
        linea = lineas[i].rstrip()
        limpia = linea.strip()
        if limpia.startswith('```'):
            cerrar_parrafo()
            codigo = []
            i += 1
            while i < len(lineas) and not lineas[i].strip().startswith('```'):
                codigo.append(lineas[i])
                i += 1
            bloques.append(('codigo', '\n'.join(codigo)))
        elif not limpia:
            cerrar_parrafo()
        elif limpia.startswith('## '):
            cerrar_parrafo()
            bloques.append(('h', en_linea(limpia[3:])))
        elif limpia == '---':
            cerrar_parrafo()
            bloques.append(('hr',))
        elif (m := _FOTO.match(limpia)):
            cerrar_parrafo()
            bloques.append(('foto', Foto(Path(m[1]).name, m[2] or '')))
        elif limpia.startswith('>'):
            cerrar_parrafo()
            if bloques and bloques[-1][0] == 'cita':
                bloques[-1] = ('cita', Markup(f'{bloques[-1][1]}<br>{en_linea(limpia[1:].strip())}'))
            else:
                bloques.append(('cita', en_linea(limpia[1:].strip())))
        elif limpia.startswith('- '):
            cerrar_parrafo()
            if bloques and bloques[-1][0] == 'lista':
                bloques[-1][1].append(en_linea(limpia[2:]))
            else:
                bloques.append(('lista', [en_linea(limpia[2:])]))
        else:
            parrafo.append(limpia)
        i += 1
    cerrar_parrafo()
    return bloques


def leer_entrada(ruta: Path) -> Entrada | None:
    try:
        cabecera, _, cuerpo = ruta.read_text(encoding='utf-8').partition('\n---\n')
    except (OSError, UnicodeDecodeError):
        return None
    datos = {}
    for linea in cabecera.splitlines():
        clave, sep, valor = linea.partition(':')
        if sep:
            datos[clave.strip().lower()] = valor.strip()
    try:
        fecha = date.fromisoformat(datos.get('fecha', ''))
    except ValueError:
        fecha = date.fromtimestamp(ruta.stat().st_mtime)
    return Entrada(
        slug=ruta.stem,
        titulo=datos.get('titulo') or ruta.stem.replace('-', ' ').capitalize(),
        fecha=fecha,
        categoria=datos.get('categoria', 'fragmentos').lower(),
        borrador=datos.get('estado', '').lower() == 'borrador',
        texto=cuerpo.strip(),
        bloques=parsear_cuerpo(cuerpo),
    )


def serializar(titulo: str, fecha: date, categoria: str, borrador: bool, texto: str) -> str:
    titulo = ' '.join(titulo.split())
    estado = 'borrador' if borrador else 'publicado'
    return (f'titulo: {titulo}\nfecha: {fecha.isoformat()}\ncategoria: {categoria}\n'
            f'estado: {estado}\n---\n{texto.strip()}\n')


# ---------- Cache: se relee solo cuando cambia algun archivo ----------

_cache: dict = {'firma': None, 'entradas': []}
_medidas: dict[str, tuple[float, tuple[int, int]]] = {}


def todas(incluir_borradores: bool = False) -> list[Entrada]:
    ENTRADAS.mkdir(parents=True, exist_ok=True)
    archivos = sorted(ENTRADAS.glob('*.txt'))
    firma = tuple((a.name, a.stat().st_mtime_ns) for a in archivos)
    if firma != _cache['firma']:
        entradas = [e for a in archivos if (e := leer_entrada(a))]
        entradas.sort(key=lambda e: (e.fecha, e.slug), reverse=True)
        _cache.update(firma=firma, entradas=entradas)
    if incluir_borradores:
        return list(_cache['entradas'])
    return [e for e in _cache['entradas'] if not e.borrador]


def buscar(slug: str, incluir_borradores: bool = False) -> Entrada | None:
    return next((e for e in todas(incluir_borradores) if e.slug == slug), None)


def medidas(archivo: str) -> tuple[int, int]:
    ruta = FOTOS / archivo
    try:
        mtime = ruta.stat().st_mtime
    except OSError:
        return (0, 0)
    guardado = _medidas.get(archivo)
    if guardado and guardado[0] == mtime:
        return guardado[1]
    try:
        with Image.open(ruta) as img:
            tam = img.size
    except OSError:
        tam = (0, 0)
    _medidas[archivo] = (mtime, tam)
    return tam


def slug_de(titulo: str) -> str:
    reemplazos = str.maketrans('áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN')
    base = re.sub(r'[^a-z0-9]+', '-', titulo.translate(reemplazos).lower()).strip('-')
    return base[:60].strip('-') or 'entrada'
