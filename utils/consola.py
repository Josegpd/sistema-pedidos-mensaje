"""Utilidades de consola: limpieza de pantalla y pausa.

Si la salida no es una terminal (por ejemplo, al redirigir a un archivo) no se
borra nada, así el texto sale limpio.
"""

import os
import sys

_ES_TERMINAL = sys.stdout.isatty()

if _ES_TERMINAL and os.name == "nt":
    os.system("")  # activa las secuencias ANSI en cmd / PowerShell de Windows


def limpiar_pantalla() -> None:
    """Borra la terminal (incluido el historial de desplazamiento)."""
    if _ES_TERMINAL:
        print("\033[H\033[2J\033[3J", end="", flush=True)


def pausar(mensaje: str = "Presione Enter para volver al menú...") -> None:
    """Deja el resultado en pantalla hasta que el operador lo termine de leer."""
    input(f"\n{mensaje}")
