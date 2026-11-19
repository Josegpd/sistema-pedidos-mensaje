"""Lectura de mensajes pegados en la terminal o guardados en archivos."""

from utils import estilo as e

MARCA_FIN = "FIN"


def leer_mensaje_pegado(leer=input, mostrar=print):
    """Lee un mensaje de varias líneas pegado en la terminal.

    Termina cuando el usuario escribe FIN en una línea sola (en cualquier
    combinación de mayúsculas), cuando una línea acaba en " FIN" en mayúsculas
    ("Quiero 2 pizzas FIN"), o con Ctrl+Z y Enter (Windows) / Ctrl+D (Linux y Mac).
    Las líneas en blanco dentro del mensaje se conservan. Devuelve el texto sin
    espacios sobrantes al inicio y final.
    """
    mostrar(e.negrita("  Pegue el mensaje del cliente.")
            + e.tenue(f" Termine con {MARCA_FIN} en una línea sola (o al final de la última)."))
    lineas = []
    while True:
        try:
            linea = leer().lstrip("﻿").rstrip()
        except EOFError:
            break
        if linea.strip().upper() == MARCA_FIN:
            break
        if linea.endswith(" " + MARCA_FIN):
            lineas.append(linea[: -len(MARCA_FIN)].rstrip())
            break
        lineas.append(linea)
    return "\n".join(lineas).strip()


def separar_lote(texto):
    """Divide un archivo de lote en mensajes.

    Cada mensaje empieza con una línea '=== titulo ==='. Las líneas que empiezan
    con '#' antes del primer título son comentarios. Devuelve [(titulo, mensaje)].
    """
    mensajes, titulo, lineas = [], None, []
    for linea in texto.replace("\r", "").lstrip("﻿").split("\n"):
        if linea.startswith("===") and linea.rstrip().endswith("==="):
            if titulo is not None:
                mensajes.append((titulo, "\n".join(lineas).strip()))
            titulo, lineas = linea.strip("= \t"), []
        elif titulo is not None:
            lineas.append(linea)
    if titulo is not None:
        mensajes.append((titulo, "\n".join(lineas).strip()))
    return mensajes


def leer_lote(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return separar_lote(archivo.read())
