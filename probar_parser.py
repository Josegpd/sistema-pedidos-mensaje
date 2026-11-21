"""Prueba del parser por terminal.

    python probar_parser.py            -> menú interactivo
    python probar_parser.py --lote     -> analiza todo pruebas/mensajes_prueba.txt
"""

import json
import sys
from pathlib import Path

from parser_mensajes import (
    Catalogo, analizar_mensaje, confirmar_pedido, leer_lote, leer_mensaje_pegado,
    resumen_para_operador,
)
from utils import estilo as e

RAIZ = Path(__file__).parent
RUTA_MENU = RAIZ / "datos" / "menu.json"
RUTA_LOTE = RAIZ / "pruebas" / "mensajes_prueba.txt"


def mostrar(pedido, como_json=False):
    print()
    print(json.dumps(pedido, ensure_ascii=False, indent=2) if como_json else resumen_para_operador(pedido))


def correr_lote(catalogo):
    for titulo, mensaje in leer_lote(RUTA_LOTE):
        print("\n" + e.magenta(f"■ {titulo}"))
        mostrar(analizar_mensaje(mensaje, catalogo))


def procesar_mensaje(catalogo, como_json):
    print()
    texto = leer_mensaje_pegado()
    if not texto:
        print("  " + e.aviso("No se pegó ningún mensaje."))
        return
    pedido = analizar_mensaje(texto, catalogo)
    # confirmar_pedido muestra lo que se entendió, pregunta lo que falta y deja corregir
    if confirmar_pedido(pedido, catalogo) and como_json:
        mostrar(pedido, como_json=True)     # lo que recibiría el resto del programa


def main():
    try:
        catalogo = Catalogo.desde_archivo(RUTA_MENU)
    except (OSError, json.JSONDecodeError) as error:
        print(e.error(f"No se pudo cargar el menú ({RUTA_MENU}): {error}"))
        return
    if "--lote" in sys.argv:
        correr_lote(catalogo)
        return
    e.limpiar_pantalla()
    while True:
        print()
        print(e.titulo("Prueba del parser de mensajes"))
        print(e.opcion(1, "Pegar un mensaje"))
        print(e.opcion(2, "Pegar un mensaje y ver el JSON"))
        print(e.opcion(3, "Correr el lote de prueba"))
        print(e.opcion(0, "Salir"))
        print(e.cierre())
        opcion = input(e.pregunta("Opción:")).strip().lstrip("﻿")
        if opcion in ("1", "2"):
            procesar_mensaje(catalogo, como_json=opcion == "2")
        elif opcion == "3":
            correr_lote(catalogo)
        elif opcion == "0":
            print(e.tenue("Hasta luego."))
            break
        else:
            print("  " + e.error("Opción no válida: escriba 1, 2, 3 o 0."))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n" + e.tenue("Hasta luego."))
