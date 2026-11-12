"""Lectura de mensajes pegados en la terminal o guardados en archivos."""

MARCA_FIN = "FIN"


def leer_mensaje_pegado(leer=input, mostrar=print):
    """Lee un mensaje de varias líneas pegado en la terminal.

    Termina cuando el usuario escribe FIN en una línea sola, o con Ctrl+Z y
    Enter (Windows) / Ctrl+D (Linux y Mac). Las líneas en blanco dentro del
    mensaje se conservan. Devuelve el texto sin espacios sobrantes al inicio y final.
    """
    mostrar(f"Pega el mensaje y escribe {MARCA_FIN} en una línea sola para terminar:")
    lineas = []
    while True:
        try:
            linea = leer()
        except EOFError:
            break
        if linea.strip().upper() == MARCA_FIN:
            break
        lineas.append(linea.rstrip())
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
