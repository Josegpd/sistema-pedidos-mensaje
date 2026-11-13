"""Prueba del parser por terminal.

    python probar_parser.py            -> menú interactivo
    python probar_parser.py --lote     -> analiza todo pruebas/mensajes_prueba.txt
"""

import json
import sys
from pathlib import Path

from parser_mensajes import Catalogo, analizar_mensaje, leer_lote, leer_mensaje_pegado, resumen_para_operador

RAIZ = Path(__file__).parent
RUTA_MENU = RAIZ / "datos" / "menu.json"
RUTA_LOTE = RAIZ / "pruebas" / "mensajes_prueba.txt"


def mostrar(pedido, como_json=False):
    print("-" * 50)
    print(json.dumps(pedido, ensure_ascii=False, indent=2) if como_json else resumen_para_operador(pedido))
    print("-" * 50)


def correr_lote(catalogo):
    for titulo, mensaje in leer_lote(RUTA_LOTE):
        print(f"\n### {titulo}")
        mostrar(analizar_mensaje(mensaje, catalogo))


def main():
    try:
        catalogo = Catalogo.desde_archivo(RUTA_MENU)
    except (OSError, json.JSONDecodeError) as error:
        print(f"No se pudo cargar el menú ({RUTA_MENU}): {error}")
        return
    if "--lote" in sys.argv:
        correr_lote(catalogo)
        return
    while True:
        print("\n1) Pegar un mensaje\n2) Pegar un mensaje y ver JSON\n3) Correr lote de prueba\n0) Salir")
        opcion = input("Opción: ").strip().lstrip("﻿")
        if opcion in ("1", "2"):
            texto = leer_mensaje_pegado()
            if texto:
                mostrar(analizar_mensaje(texto, catalogo), como_json=opcion == "2")
            else:
                print("No se pegó ningún mensaje.")
        elif opcion == "3":
            correr_lote(catalogo)
        elif opcion == "0":
            break
        else:
            print("Opción no válida, escribe 1, 2, 3 o 0.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nHasta luego.")
