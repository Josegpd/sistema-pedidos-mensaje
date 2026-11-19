"""Colores y formato para la terminal, sin librerías externas.

Usa códigos ANSI, que funcionan en Windows 10/11 (PowerShell, cmd, VS Code),
Linux y Mac. Los colores se apagan solos si la salida no es una terminal
(por ejemplo, en las pruebas o al redirigir a un archivo) o si existe la
variable de entorno NO_COLOR.

Uso:
    from utils import estilo as e

    print(e.titulo("Nuevo pedido"))
    print(e.ok("Pedido registrado"))
    print(e.error("La cédula no es válida"))
    print(e.verde("texto en verde"), e.negrita("texto en negrita"))
"""

import os
import sys

ANCHO = 58


def _activar():
    """Prepara la consola: UTF-8 para los símbolos y ANSI en Windows."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        os.system("")  # activa el modo ANSI de la consola de Windows
    return True


COLORES = _activar()


def _ansi(codigo):
    return lambda texto: f"\033[{codigo}m{texto}\033[0m" if COLORES else str(texto)


negrita = _ansi("1")
tenue = _ansi("2")
rojo = _ansi("31")
verde = _ansi("32")
amarillo = _ansi("33")
azul = _ansi("34")
magenta = _ansi("35")
cian = _ansi("36")


def titulo(texto):
    """╭─ Texto ────────────╮"""
    relleno = max(ANCHO - len(texto) - 5, 0)
    return cian("╭─ ") + negrita(texto) + cian(" " + "─" * relleno + "╮")


def cierre():
    return cian("╰" + "─" * (ANCHO - 2) + "╯")


def separador():
    return tenue("─" * ANCHO)


def ok(texto):
    return verde(f"✔ {texto}")


def error(texto):
    return rojo(f"✖ {texto}")


def aviso(texto):
    return amarillo(f"⚠ {texto}")


def info(texto):
    return cian(f"› {texto}")


def campo(etiqueta, valor, ancho=11):
    """'  Cédula     V-12345678' (o 'falta' en rojo si no hay valor)."""
    return f"  {tenue(etiqueta.ljust(ancho))}{valor if valor else rojo('falta')}"


def opcion(tecla, texto):
    """'  [1] Pegar un mensaje'"""
    return f"  {cian('[' + str(tecla) + ']')} {texto}"


def pregunta(texto):
    """Texto para input(): '› Cédula: ' con la flecha resaltada."""
    return f"{cian('›')} {negrita(texto)} "


def limpiar_pantalla():
    if COLORES:
        print("\033[2J\033[H", end="")
