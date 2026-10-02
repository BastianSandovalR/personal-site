# Cómo publicar en el Kernel de Bastian

Hay dos formas. Las dos terminan en lo mismo: un archivo `.txt` en `contenido/entradas/`.

## 1. Desde el navegador o el celular (lo normal)

1. Entra a `/admin` (usuario `bastian` y la clave definida en `BLOG_CLAVE`).
2. Presiona **Escribir entrada nueva**, escribe, adjunta fotos y guarda.
3. Si marcas "borrador", solo tú la ves (desde la vista previa del panel).

Las fotos se achican a 1600 px, se genera una miniatura y se les **borra el GPS**
y los demás metadatos antes de publicarlas.

## 2. A mano (con un editor de texto)

Crea `contenido/entradas/mi-entrada.txt` (el nombre del archivo es la URL: `/entrada/mi-entrada`):

```
titulo: Mi entrada
fecha: 2026-10-01
categoria: bitacoras
estado: publicado
---
Primer párrafo. Una línea en blanco separa párrafos.

## Un subtítulo

Texto con **negrita**, *cursiva*, `código` y [un enlace](https://github.com/BastianSandovalR).

> Una cita

- Una lista
- de cosas

[foto: nombre-de-la-foto.jpg | El pie de la foto]
```

Para poesía, cada verso empieza con `| ` y una línea en blanco separa las estrofas:

```
| Primer verso
| segundo verso

| Otra estrofa
```

Las fotos van en `contenido/fotos/`. Categorías con nombre bonito: `ingenieria`, `bitacoras`,
`reflexiones`, `fragmentos`, `poemas`, `fotos`. Cualquier otra también funciona (ej: `recetas`).

## Papelera

Borrar desde el panel no elimina: mueve el archivo a `contenido/papelera/`. Para recuperar
una entrada, devuélvela a `contenido/entradas/` (sin la marca de fecha del nombre).
