"""Parser de mensajes de chat para pedidos del restaurante.

Uso típico desde otro módulo:

    from parser_mensajes import Catalogo, analizar_mensaje, leer_mensaje_pegado

    catalogo = Catalogo.desde_archivo("datos/menu.json")
    pedido = analizar_mensaje(leer_mensaje_pegado(), catalogo)
    if not pedido["completo"]:
        print(pedido["faltantes"])
"""

from .entrada import leer_lote, leer_mensaje_pegado, separar_lote
from .parser import analizar_mensaje, calcular_faltantes, resumen_para_operador
from .platos import Catalogo

__all__ = [
    "Catalogo",
    "analizar_mensaje",
    "calcular_faltantes",
    "leer_lote",
    "leer_mensaje_pegado",
    "resumen_para_operador",
    "separar_lote",
]
