"""Corregir y completar un pedido que el parser dejó incompleto.

Hay funciones sueltas (para usarlas desde cualquier menú) y un flujo
interactivo, completar_pedido(), que pregunta al operador solo lo que falta
y no acepta datos mal escritos.
"""

from datetime import date

from utils import estilo as e

from .campos import EJEMPLOS, validar_campo
from .parser import (
    CAMPOS_CLIENTE, NOMBRES_CAMPOS, _guardar_validado, agregar_item, calcular_faltantes,
    mensajes_para_cliente, resumen_para_operador,
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
    # Los avisos sobre cómo se dedujo ese dato ya no aplican.
    if campo in ("fecha", "hora"):
        pedido["advertencias"] = [
            a for a in pedido["advertencias"]
            if not a.startswith(f"Sin {campo}") and not (campo == "hora" and "am/pm" in a)
        ]
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
        mostrar("")
        mostrar(e.titulo("Completar pedido"))
        mostrar(e.tenue(f"  Escriba '{PALABRA_CANCELAR}' en cualquier momento para dejarlo pendiente."))
        # 1. Platos.
        while "platos" in pedido["faltantes"]:
            extras_antes = len(pedido["extras"])
            agregar_platos(pedido, preguntar(e.pregunta("Platos") + e.tenue("(ej: 2 hamburguesas, 1 refresco) ")), catalogo)
            for item in pedido["extras"][extras_antes:]:
                mostrar("  " + e.aviso(f"'{item['texto']}' no está en el menú: se anotó como extra."))

        # 2. Platos ambiguos.
        while pedido["ambiguos"]:
            item = pedido["ambiguos"][0]
            mostrar("")
            mostrar(e.negrita(f"  ¿Cuál '{item['texto']}' pidió el cliente?"))
            for numero, opcion in enumerate(item["opciones"], 1):
                mostrar(e.opcion(numero, f"{opcion['nombre']}  {e.tenue(format(opcion.get('precio', 0), '.2f'))}"))
            mostrar(e.opcion(0, e.tenue("Ninguno (anotar como extra)")))
            eleccion = preguntar(e.pregunta("Opción:"))
            if eleccion.isdigit() and int(eleccion) <= len(item["opciones"]):
                numero = int(eleccion)
                resolver_ambiguo(pedido, 0, item["opciones"][numero - 1]["id"] if numero else None)
                mostrar("  " + e.ok(item["opciones"][numero - 1]["nombre"] if numero else "Anotado como extra"))
            else:
                mostrar("  " + e.error(f"Opción no válida: escriba un número del 0 al {len(item['opciones'])}."))

        # 3. Datos del cliente, fecha y hora.
        campos = [c for c in (*CAMPOS_CLIENTE, "fecha", "hora") if c in pedido["faltantes"]]
        if campos:
            mostrar("")
        for campo in campos:
            if campo in pedido["invalidos"]:
                mostrar("  " + e.aviso(pedido["invalidos"][campo]))
            while True:
                texto = e.pregunta(NOMBRES_CAMPOS[campo].capitalize()) + e.tenue(f"(ej: {EJEMPLOS[campo]}) ")
                error = completar_campo(pedido, campo, preguntar(texto), hoy)
                if not error:
                    break
                mostrar("  " + e.error(error))
    except _Cancelado:
        mostrar("  " + e.aviso("Pedido dejado como pendiente."))
        mostrar(e.cierre())
        return False
    mostrar(e.cierre())
    return pedido["completo"]


def quitar_plato(pedido, indice):
    """Quita el plato número `indice` (desde 0) de la lista de platos."""
    pedido["platos"].pop(indice)
    calcular_faltantes(pedido)


# Opciones del menú de corrección: (tecla, texto, campo o acción).
OPCIONES_CORREGIR = [
    ("1", "Cédula", "cedula"),
    ("2", "Nombre", "nombres"),
    ("3", "Apellido", "apellidos"),
    ("4", "Dirección", "direccion"),
    ("5", "Fecha", "fecha"),
    ("6", "Hora", "hora"),
    ("7", "Agregar platos", "agregar"),
    ("8", "Quitar un plato", "quitar"),
]


def confirmar_pedido(pedido, catalogo, leer=input, mostrar=print, hoy=None):
    """Muestra el resumen final y deja corregir cualquier dato antes de aceptarlo.

    Primero completa lo que falte (completar_pedido). Luego repite:
    resumen -> [1] Confirmar  [2] Corregir un dato  [0] Cancelar.
    Devuelve True si el operador confirma el pedido (completo y revisado),
    False si lo cancela o lo deja pendiente.
    """
    hoy = hoy or date.today()

    def preguntar(texto):
        return leer(texto).strip().lstrip("﻿")

    aviso = None
    while True:
        # Pantalla limpia en cada vuelta: solo el pedido como está ahora (en la terminal real)
        if mostrar is print:
            e.limpiar_pantalla()
        mostrar("")
        mostrar(resumen_para_operador(pedido))
        if aviso:
            mostrar("  " + aviso)
            aviso = None
        if not pedido["completo"]:
            if not completar_pedido(pedido, catalogo, leer, mostrar, hoy):
                return False
            continue  # se vuelve a mostrar el resumen, ya completo
        mostrar(e.opcion(1, e.verde("Confirmar pedido")))
        mostrar(e.opcion(2, "Corregir un dato"))
        mostrar(e.opcion(0, e.rojo("Cancelar pedido")))
        eleccion = preguntar(e.pregunta("¿Está todo correcto?"))
        if eleccion == "1":
            mostrar("  " + e.ok("Pedido confirmado."))
            return True
        if eleccion == "0":
            mostrar("  " + e.aviso("Pedido cancelado."))
            return False
        if eleccion == "2":
            _corregir(pedido, catalogo, preguntar, mostrar, hoy)
        else:
            aviso = e.error("Opción no válida: escriba 1, 2 o 0.")


def _corregir(pedido, catalogo, preguntar, mostrar, hoy):
    """Menú para cambiar un dato del pedido. Cualquier tecla inválida vuelve atrás."""
    mostrar("")
    mostrar(e.titulo("Corregir"))
    for tecla, texto, _ in OPCIONES_CORREGIR:
        mostrar(e.opcion(tecla, texto))
    mostrar(e.opcion(0, e.tenue("Volver")))
    mostrar(e.cierre())
    eleccion = preguntar(e.pregunta("¿Qué desea corregir?"))
    accion = next((a for tecla, _, a in OPCIONES_CORREGIR if tecla == eleccion), None)

    if accion is None:
        return
    if accion == "agregar":
        antes = len(pedido["extras"])
        agregar_platos(pedido, preguntar(e.pregunta("Platos") + e.tenue("(ej: 1 refresco) ")), catalogo)
        for item in pedido["extras"][antes:]:
            mostrar("  " + e.aviso(f"'{item['texto']}' no está en el menú: se anotó como extra."))
        return
    if accion == "quitar":
        if not pedido["platos"]:
            mostrar("  " + e.aviso("No hay platos para quitar."))
            return
        for numero, plato in enumerate(pedido["platos"], 1):
            mostrar(e.opcion(numero, f"{plato['cantidad']} × {plato['nombre']}"))
        numero = preguntar(e.pregunta("¿Cuál quitar?") + e.tenue("(0 = ninguno) "))
        if numero.isdigit() and 1 <= int(numero) <= len(pedido["platos"]):
            quitado = pedido["platos"][int(numero) - 1]["nombre"]
            quitar_plato(pedido, int(numero) - 1)
            mostrar("  " + e.ok(f"Se quitó {quitado}."))
        return

    # Un dato del cliente, la fecha o la hora: se repite hasta que sea válido.
    while True:
        texto = e.pregunta(NOMBRES_CAMPOS[accion].capitalize()) + e.tenue(f"(ej: {EJEMPLOS[accion]}) ")
        valor = preguntar(texto)
        if accion == "apellidos" and not valor:          # el apellido es opcional
            pedido["cliente"]["apellidos"] = None
            break
        error = completar_campo(pedido, accion, valor, hoy)
        if not error:
            break
        mostrar("  " + e.error(error))
    mostrar("  " + e.ok("Dato actualizado."))


class _Cancelado(Exception):
    pass


__all__ = ["agregar_platos", "completar_campo", "completar_pedido", "confirmar_pedido",
           "mensajes_para_cliente", "quitar_plato", "resolver_ambiguo"]
