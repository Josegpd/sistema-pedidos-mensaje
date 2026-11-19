"""Corregir y completar un pedido que el parser dejó incompleto.

Hay funciones sueltas (para usarlas desde cualquier menú) y un flujo
interactivo, completar_pedido(), que pregunta al operador solo lo que falta
y no acepta datos mal escritos.
"""

from datetime import date

from .campos import EJEMPLOS, validar_campo
from .parser import (
    CAMPOS_CLIENTE, NOMBRES_CAMPOS, _guardar_validado, agregar_item, calcular_faltantes,
    mensajes_para_cliente,
)
from .platos import analizar_item, separar_items

PALABRA_CANCELAR = "cancelar"


def completar_campo(pedido, campo, valor, hoy=None):
    """Valida y guarda un dato (cédula, nombres, apellidos, dirección, fecha u hora).

    Devuelve None si quedó guardado, o el mensaje de error si el dato no es válido
    (en ese caso el pedido no cambia ese campo).
    """
    _, error = validar_campo(campo, valor, hoy or date.today())
    if error:
        return error
    _guardar_validado(pedido, campo, valor, hoy or date.today())
    calcular_faltantes(pedido)
    return None


def agregar_platos(pedido, texto, catalogo):
    """Agrega platos escritos por el operador ('2 hamburguesas, 1 refresco').

    Lo que no está en el menú queda en extras y lo dudoso en ambiguos.
    """
    for parte in separar_items(texto):
        agregar_item(pedido, analizar_item(parte, catalogo))
    calcular_faltantes(pedido)


def resolver_ambiguo(pedido, indice, id_plato=None):
    """Resuelve el ambiguo número `indice` (desde 0) eligiendo `id_plato`.

    Si id_plato es None, el ítem pasa a extras. Devuelve False si el id no
    es una de las opciones.
    """
    item = pedido["ambiguos"][indice]
    if id_plato is None:
        pedido["ambiguos"].pop(indice)
        pedido["extras"].append({k: item[k] for k in ("texto", "cantidad", "variacion")})
        calcular_faltantes(pedido)
        return True
    for opcion in item["opciones"]:
        if opcion["id"] == id_plato:
            pedido["ambiguos"].pop(indice)
            agregar_item(pedido, {
                "estado": "ok", "texto": item["texto"], "cantidad": item["cantidad"],
                "variacion": item["variacion"], "id_plato": opcion["id"],
                "nombre": opcion["nombre"], "precio": opcion.get("precio", 0),
            })
            calcular_faltantes(pedido)
            return True
    return False


def completar_pedido(pedido, catalogo, leer=input, mostrar=print, hoy=None):
    """Pregunta al operador, uno por uno, los datos que faltan o están mal.

    Repite cada pregunta hasta que la respuesta sea válida. El operador puede
    escribir 'cancelar' para dejar el pedido como está (devuelve False).
    Devuelve True cuando el pedido queda completo.
    """
    hoy = hoy or date.today()

    def preguntar(texto):
        respuesta = leer(texto).strip().lstrip("﻿")
        if respuesta.lower() == PALABRA_CANCELAR:
            raise _Cancelado
        return respuesta

    try:
        mostrar(f"(Escriba '{PALABRA_CANCELAR}' en cualquier momento para dejarlo pendiente)")
        # 1. Platos.
        while "platos" in pedido["faltantes"]:
            agregar_platos(pedido, preguntar("Platos (ej: 2 hamburguesas, 1 refresco): "), catalogo)
            for item in pedido["extras"]:
                mostrar(f"  '{item['texto']}' no está en el menú: se anotó como extra.")

        # 2. Platos ambiguos.
        while pedido["ambiguos"]:
            item = pedido["ambiguos"][0]
            mostrar(f"¿Cuál '{item['texto']}' pidió el cliente?")
            for numero, opcion in enumerate(item["opciones"], 1):
                mostrar(f"  {numero}) {opcion['nombre']} - {opcion.get('precio', 0):.2f}")
            mostrar("  0) Ninguno (anotar como extra)")
            eleccion = preguntar("Opción: ")
            if eleccion.isdigit() and int(eleccion) <= len(item["opciones"]):
                numero = int(eleccion)
                resolver_ambiguo(pedido, 0, item["opciones"][numero - 1]["id"] if numero else None)
            else:
                mostrar(f"  Opción no válida: escriba un número del 0 al {len(item['opciones'])}.")

        # 3. Datos del cliente, fecha y hora.
        for campo in [c for c in (*CAMPOS_CLIENTE, "fecha", "hora") if c in pedido["faltantes"]]:
            if campo in pedido["invalidos"]:
                mostrar(f"  {pedido['invalidos'][campo]}")
            while True:
                valor = preguntar(f"{NOMBRES_CAMPOS[campo].capitalize()} (ej: {EJEMPLOS[campo]}): ")
                error = completar_campo(pedido, campo, valor, hoy)
                if not error:
                    break
                mostrar(f"  {error}")
    except _Cancelado:
        mostrar("Pedido dejado como pendiente.")
        return False
    return pedido["completo"]


class _Cancelado(Exception):
    pass


__all__ = ["agregar_platos", "completar_campo", "completar_pedido", "mensajes_para_cliente",
           "resolver_ambiguo"]
