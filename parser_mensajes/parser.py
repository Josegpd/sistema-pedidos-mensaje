"""Función principal: convierte el texto de un mensaje de chat en un pedido (dict)."""

import re
from datetime import date

from .campos import (
    buscar_cedula, buscar_nombre, dividir_nombre_completo, etiqueta_de,
    normalizar_cedula, normalizar_fecha, normalizar_hora, quitar_encabezado_chat,
)
from .normalizar import capitalizar_nombre, quitar_acentos
from .platos import analizar_item, separar_items

LO_DE_SIEMPRE = re.compile(
    r"\blo\s+(?:de\s+siempre|mismo|usual|de\s+costumbre|de\s+la\s+(?:otra|ultima)\s+vez)\b"
)
LINEA_CON_VINETA = re.compile(r"^\s*[-*•·]")
LINEA_CON_CANTIDAD = re.compile(r"^\s*\d+\s*x?\s+[a-záéíóúñ]{3,}", re.IGNORECASE)

NOMBRES_CAMPOS = {
    "cedula": "cédula", "nombres": "nombres", "apellidos": "apellidos",
    "direccion": "dirección", "fecha": "fecha", "hora": "hora", "platos": "platos",
}


def analizar_mensaje(texto, catalogo, hoy=None):
    """Analiza un mensaje de chat y devuelve un diccionario con el pedido.

    - texto: el mensaje tal cual (puede tener varias líneas).
    - catalogo: un objeto Catalogo (ver platos.py).
    - hoy: fecha de referencia para 'hoy'/'mañana' (por defecto la fecha actual).

    Claves del resultado:
        cliente        {"cedula", "nombres", "apellidos", "direccion"}
        fecha, hora    "YYYY-MM-DD", "HH:MM" (o None)
        platos         [{"id_plato", "nombre", "cantidad", "precio", "variacion", "texto"}]
        total_estimado suma de precio * cantidad de los platos reconocidos
        lo_de_siempre  True si el cliente pidió "lo de siempre"
        ambiguos       [{"texto", "cantidad", "variacion", "opciones": [{"id", "nombre"}]}]
        no_reconocidos [{"texto", "cantidad", "variacion"}]
        faltantes      lista de campos que faltan (ver calcular_faltantes)
        advertencias   lista de textos para que el operador revise
        completo       True si no falta nada y no hay ambigüedades
        fecha_recepcion "YYYY-MM-DD HH:MM" si el texto traía el encabezado del chat
        texto_original el mensaje recibido
    """
    resultado = {
        "cliente": {"cedula": None, "nombres": None, "apellidos": None, "direccion": None},
        "fecha": None,
        "hora": None,
        "platos": [],
        "total_estimado": 0.0,
        "lo_de_siempre": False,
        "ambiguos": [],
        "no_reconocidos": [],
        "faltantes": [],
        "advertencias": [],
        "completo": False,
        "fecha_recepcion": None,
        "texto_original": texto,
    }
    avisos = resultado["advertencias"]

    # 1. Separar líneas y quitar encabezados de WhatsApp ("[11/11/26, 12:30] Maria: ...").
    lineas = []
    for linea in (texto or "").replace("\r", "").split("\n"):
        linea, recepcion = quitar_encabezado_chat(linea)
        if recepcion and not resultado["fecha_recepcion"]:
            resultado["fecha_recepcion"] = recepcion
        if linea.strip():
            lineas.append(linea.strip())
    if hoy is None:
        recepcion = resultado["fecha_recepcion"]
        hoy = date.fromisoformat(recepcion[:10]) if recepcion else date.today()

    # 2. Clasificar líneas: "Etiqueta: valor", líneas de pedido y texto libre.
    valores, lineas_pedido, libres = {}, [], []
    en_pedido = False
    for linea in lineas:
        etiqueta = etiqueta_de(linea)
        if etiqueta:
            campo, valor = etiqueta
            en_pedido = campo == "pedido"
            if en_pedido:
                if valor:
                    lineas_pedido.append(valor)
            elif campo != "otro" and valor:
                if campo in valores and valores[campo] != valor:
                    avisos.append(f"El campo '{campo}' aparece dos veces; se usó '{valores[campo]}'.")
                valores.setdefault(campo, valor)
        elif en_pedido:
            lineas_pedido.append(linea)
        else:
            libres.append(linea)
    texto_libre = "\n".join(libres)

    # 3. "Lo de siempre".
    resultado["lo_de_siempre"] = bool(LO_DE_SIEMPRE.search(quitar_acentos(texto.lower())))

    # 4. Datos del cliente, fecha y hora.
    _extraer_cliente(resultado, valores, texto_libre)
    _extraer_fecha_hora(resultado, valores, texto_libre, hoy)

    # 5. Platos: todas las líneas de la sección "Pedido:" y, fuera de ella,
    #    las líneas libres que mencionen algo del menú.
    items = []
    for linea in lineas_pedido:
        items += [(item, True) for item in separar_items(linea)]
    for linea in libres:
        parece_plato = bool(LINEA_CON_VINETA.match(linea) or LINEA_CON_CANTIDAD.match(linea))
        items += [(item, parece_plato) for item in separar_items(linea)]
    for texto_item, reportar_si_falla in items:
        if LO_DE_SIEMPRE.search(quitar_acentos(texto_item.lower())):
            continue
        item = analizar_item(texto_item, catalogo)
        if item["estado"] == "ok":
            _agregar_plato(resultado, item)
        elif item["estado"] == "ambiguo":
            resultado["ambiguos"].append(_sin_estado(item))
        elif reportar_si_falla:
            resultado["no_reconocidos"].append(_sin_estado(item))

    for plato in resultado["platos"]:
        if not 1 <= plato["cantidad"] <= 50:
            avisos.append(f"Cantidad inusual para {plato['nombre']}: {plato['cantidad']}.")
    resultado["total_estimado"] = round(
        sum(p["cantidad"] * p["precio"] for p in resultado["platos"]), 2
    )
    calcular_faltantes(resultado)
    return resultado


def calcular_faltantes(pedido):
    """Recalcula 'faltantes' y 'completo'.

    Úsala de nuevo después de completar datos a mano (por ejemplo, cuando el
    operador escribe la dirección o se rellenan los datos del cliente registrado).
    """
    cliente = pedido["cliente"]
    faltan = [c for c in ("cedula", "nombres", "apellidos", "direccion") if not cliente.get(c)]
    faltan += [c for c in ("fecha", "hora") if not pedido.get(c)]
    if not (pedido["platos"] or pedido["ambiguos"] or pedido["lo_de_siempre"]):
        faltan.append("platos")
    pedido["faltantes"] = faltan
    pedido["completo"] = not faltan and not pedido["ambiguos"] and not pedido["no_reconocidos"]
    return faltan


def resumen_para_operador(pedido):
    """Texto legible para mostrar en la terminal."""
    cliente = pedido["cliente"]
    lineas = [
        f"Cédula:    {cliente['cedula'] or '-'}",
        f"Nombres:   {cliente['nombres'] or '-'}",
        f"Apellidos: {cliente['apellidos'] or '-'}",
        f"Dirección: {cliente['direccion'] or '-'}",
        f"Fecha:     {pedido['fecha'] or '-'}    Hora: {pedido['hora'] or '-'}",
        "Platos:",
    ]
    for plato in pedido["platos"]:
        extra = f" ({plato['variacion']})" if plato["variacion"] else ""
        lineas.append(f"  {plato['cantidad']} x {plato['nombre']}{extra}  -> {plato['cantidad'] * plato['precio']:.2f}")
    if pedido["lo_de_siempre"]:
        lineas.append("  * Pidió \"lo de siempre\": buscar en su historial.")
    if not pedido["platos"] and not pedido["lo_de_siempre"]:
        lineas.append("  (ninguno)")
    lineas.append(f"Total estimado: {pedido['total_estimado']:.2f}")
    for item in pedido["ambiguos"]:
        opciones = " / ".join(o["nombre"] for o in item["opciones"])
        lineas.append(f"AMBIGUO: '{item['texto']}' puede ser: {opciones}")
    for item in pedido["no_reconocidos"]:
        lineas.append(f"NO RECONOCIDO: '{item['texto']}'")
    if pedido["faltantes"]:
        lineas.append("FALTA: " + ", ".join(NOMBRES_CAMPOS[c] for c in pedido["faltantes"]))
    for aviso in pedido["advertencias"]:
        lineas.append(f"Aviso: {aviso}")
    lineas.append("Estado: " + ("COMPLETO" if pedido["completo"] else "INCOMPLETO"))
    return "\n".join(lineas)


def _extraer_cliente(resultado, valores, texto_libre):
    cliente, avisos = resultado["cliente"], resultado["advertencias"]

    if "cedula" in valores:
        cliente["cedula"] = normalizar_cedula(valores["cedula"])
        if not cliente["cedula"]:
            avisos.append(f"La cédula '{valores['cedula']}' no es válida.")
    else:
        cliente["cedula"] = buscar_cedula(texto_libre)

    nombres = valores.get("nombres") or valores.get("nombre")
    apellidos = valores.get("apellidos")
    completo = valores.get("nombre_completo")
    # "Nombre: Juan Perez" sin línea de apellido -> se trata como nombre completo.
    if not completo and not apellidos and "nombre" in valores and len(valores["nombre"].split()) >= 2:
        completo, nombres = valores["nombre"], None
    if not (completo or nombres or apellidos):
        completo = buscar_nombre(texto_libre)
    if completo and not (nombres or apellidos):
        nombres, apellidos = dividir_nombre_completo(completo)
        if len(completo.split()) not in (2, 4) and apellidos:
            avisos.append(f"Se separó '{completo}' como nombres='{nombres}' y "
                          f"apellidos='{apellidos}'; verificar con el cliente.")
    cliente["nombres"] = capitalizar_nombre(nombres) if nombres else None
    cliente["apellidos"] = capitalizar_nombre(apellidos) if apellidos else None
    cliente["direccion"] = valores.get("direccion") or None


def _extraer_fecha_hora(resultado, valores, texto_libre, hoy):
    avisos = resultado["advertencias"]
    fecha_hora = valores.get("fecha_hora", "")

    texto_fecha = valores.get("fecha") or fecha_hora
    fecha = normalizar_fecha(texto_fecha, hoy) if texto_fecha else None
    if valores.get("fecha") and not fecha:
        avisos.append(f"No se entendió la fecha '{valores['fecha']}'.")
    if not fecha and not valores.get("fecha"):
        fecha = normalizar_fecha(texto_libre, hoy)

    if valores.get("hora"):
        hora, dudosa = normalizar_hora(valores["hora"], solo_numero=True)
        if not hora:
            avisos.append(f"No se entendió la hora '{valores['hora']}'.")
    else:
        hora, dudosa = normalizar_hora(fecha_hora)
        if not hora:
            hora, dudosa = normalizar_hora(texto_libre)
    if dudosa:
        avisos.append(f"La hora {hora} no dice am/pm; se tomó en formato 24 h.")

    recepcion = resultado["fecha_recepcion"]
    if recepcion and not fecha:
        fecha = recepcion[:10]
        avisos.append("Sin fecha en el mensaje: se usó la fecha en que se recibió.")
    if recepcion and not hora:
        hora = recepcion[11:]
        avisos.append("Sin hora en el mensaje: se usó la hora en que se recibió.")
    if fecha and fecha < hoy.isoformat():
        avisos.append(f"La fecha {fecha} ya pasó.")
    resultado["fecha"], resultado["hora"] = fecha, hora


def _agregar_plato(resultado, item):
    for plato in resultado["platos"]:
        if plato["id_plato"] == item["id_plato"] and plato["variacion"] == item["variacion"]:
            plato["cantidad"] += item["cantidad"]
            resultado["advertencias"].append(
                f"'{item['nombre']}' aparece más de una vez; se sumaron las cantidades.")
            return
    resultado["platos"].append({
        "id_plato": item["id_plato"],
        "nombre": item["nombre"],
        "cantidad": item["cantidad"],
        "precio": item["precio"],
        "variacion": item["variacion"],
        "texto": item["texto"],
    })


def _sin_estado(item):
    return {k: v for k, v in item.items() if k != "estado"}
