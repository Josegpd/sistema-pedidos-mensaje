"""Parser de mensajes de chat para pedidos del restaurante.

Uso típico desde otro módulo:

    from parser_mensajes import Catalogo, analizar_mensaje, completar_pedido, mensajes_para_cliente

    catalogo = Catalogo.desde_archivo("datos/menu.json")
    pedido = analizar_mensaje(leer_mensaje_pegado(), catalogo)
    if not pedido["completo"]:
        for frase in mensajes_para_cliente(pedido):   # qué decirle al cliente
            print(frase)
        completar_pedido(pedido, catalogo)            # el operador completa lo que falta
"""

from .campos import validar_campo
from .completar import agregar_platos, completar_campo, completar_pedido, resolver_ambiguo
from .entrada import leer_lote, leer_mensaje_pegado, separar_lote
from .parser import analizar_mensaje, calcular_faltantes, mensajes_para_cliente, resumen_para_operador
from .platos import Catalogo

__all__ = [
    "Catalogo",
    "agregar_platos",
    "analizar_mensaje",
    "calcular_faltantes",
    "completar_campo",
    "completar_pedido",
    "leer_lote",
    "leer_mensaje_pegado",
    "mensajes_para_cliente",
    "resolver_ambiguo",
    "resumen_para_operador",
    "separar_lote",
    "validar_campo",
]
