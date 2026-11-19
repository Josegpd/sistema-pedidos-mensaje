"""Función principal: convierte el texto de un mensaje de chat en un pedido (dict)."""

import re
from datetime import date, datetime

from .campos import (
    NOMBRES_LARGOS, buscar_cedula, buscar_nombre, dividir_nombre_completo, etiqueta_de,
    normalizar_fecha, normalizar_hora, quitar_encabezado_chat, validar_campo,
)
from utils import estilo as e

from .normalizar import capitalizar_nombre, quitar_acentos
from .platos import analizar_item, separar_items

LO_DE_SIEMPRE = re.compile(
    r"\blo\s+(?:de\s+siempre|mismo|usual|de\s+costumbre|de\s+la\s+(?:otra|ultima)\s+vez)\b"
)
LINEA_CON_VINETA = re.compile(r"^\s*[-*•·]")
LINEA_CON_CANTIDAD = re.compile(r"^\s*\d+\s*x?\s+[a-záéíóúñ]{3,}", re.IGNORECASE)
# Palabras con las que el cliente introduce un plato: "quiero 2 pizzas", "y una soda".
INTRODUCCION = re.compile(
    r"^(?:(?:hola|buenas|quiero|quisiera|queria|quería|dame|deme|me\s+das|me\s+da|"
    r"me\s+env[ií]as|m[aá]ndame|pido|ademas|además|tambien|también|y|e)\b[\s,!.]*)+",
    re.IGNORECASE,
)

CAMPOS_CLIENTE = ("cedula", "nombres", "apellidos", "direccion")
# Lo indispensable para registrar un pedido. La cédula identifica al cliente en
# el resto del sistema. El apellido es opcional; si falta la fecha o la hora se
# asume el momento actual.
CAMPOS_OBLIGATORIOS = ("cedula", "nombres", "direccion")
NOMBRES_CAMPOS = {
    "cedula": "cédula", "nombres": "nombres", "apellidos": "apellidos",
    "direccion": "dirección", "fecha": "fecha", "hora": "hora", "platos": "platos",
}


def analizar_mensaje(texto, catalogo, hoy=None, ahora=None):
    """Analiza un mensaje de chat y devuelve un diccionario con el pedido.

    - texto: el mensaje tal cual (puede tener varias líneas).
    - catalogo: un objeto Catalogo (ver platos.py).
    - hoy: fecha de referencia para 'hoy'/'mañana' (por defecto la fecha actual).
    - ahora: momento que se asume si el mensaje no trae fecha u hora
      (por defecto, la hora de recepción del chat o la hora actual).

    Claves del resultado:
        cliente        {"cedula", "nombres", "apellidos", "direccion"} (None si falta o es inválido)
        fecha, hora    "YYYY-MM-DD", "HH:MM" (si no vienen, el momento actual; None si son inválidas)
        platos         [{"id_plato", "nombre", "cantidad", "precio", "variacion", "texto"}]
        extras         [{"texto", "cantidad", "variacion"}]: lo que pidió y no está en el menú
        total_estimado suma de precio * cantidad de los platos (los extras no suman)
        lo_de_siempre  True si el cliente pidió "lo de siempre"
        ambiguos       [{"texto", "cantidad", "variacion", "opciones": [{"id", "nombre", "precio"}]}]
        invalidos      {campo: mensaje}: datos que el cliente escribió pero no se entendieron
        faltantes      campos obligatorios que faltan o están mal (ver calcular_faltantes)
        advertencias   avisos internos para el operador (no impiden registrar)
        completo       True si no falta nada y no hay platos ambiguos
        fecha_recepcion "YYYY-MM-DD HH:MM" si el texto traía el encabezado del chat
        texto_original el mensaje recibido

    Para avisarle al cliente qué corregir, usa mensajes_para_cliente(pedido).
    """
    resultado = {
        "cliente": {campo: None for campo in CAMPOS_CLIENTE},
        "fecha": None,
        "hora": None,
        "platos": [],
        "extras": [],
        "total_estimado": 0.0,
        "lo_de_siempre": False,
        "ambiguos": [],
        "invalidos": {},
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
    recepcion = resultado["fecha_recepcion"]
    if ahora is None:
        ahora = datetime.fromisoformat(recepcion) if recepcion else datetime.now()
    if hoy is None:
        hoy = ahora.date()

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
    resultado["lo_de_siempre"] = bool(LO_DE_SIEMPRE.search(quitar_acentos((texto or "").lower())))

    # 4. Datos del cliente, fecha y hora.
    _extraer_cliente(resultado, valores, texto_libre, hoy)
    _extraer_fecha_hora(resultado, valores, texto_libre, hoy, ahora)

    # 5. Platos: todas las líneas de la sección "Pedido:" y, fuera de ella,
    #    las líneas libres que mencionen algo del menú.
    items = []
    for linea in lineas_pedido:
        items += [(_sin_introduccion(item), True) for item in separar_items(linea)]
    for linea in libres:
        con_vineta = bool(LINEA_CON_VINETA.match(linea))
        for item in separar_items(linea):
            item = _sin_introduccion(item)
            # En texto libre, lo que no se reconoce solo es extra si parece un plato
            # ("1 sushi"); así un saludo no termina anotado como extra.
            items.append((item, con_vineta or bool(LINEA_CON_CANTIDAD.match(item))))
    for texto_item, es_extra_si_falla in items:
        if LO_DE_SIEMPRE.search(quitar_acentos(texto_item.lower())):
            continue
        agregar_item(resultado, analizar_item(texto_item, catalogo), es_extra_si_falla)

    for plato in resultado["platos"]:
        if plato["cantidad"] > 50:
            avisos.append(f"Cantidad inusual para {plato['nombre']}: {plato['cantidad']}.")
    calcular_faltantes(resultado)
    return resultado


def agregar_item(pedido, item, es_extra_si_falla=True):
    """Coloca un ítem ya analizado (ver platos.analizar_item) en platos, ambiguos o extras."""
    if item["cantidad"] < 1:
        pedido["advertencias"].append(f"Se ignoró '{item['texto']}': la cantidad debe ser al menos 1.")
    elif item["estado"] == "ok":
        _agregar_plato(pedido, item)
    elif item["estado"] == "ambiguo":
        pedido["ambiguos"].append(_sin_estado(item))
    elif es_extra_si_falla:
        pedido["extras"].append(_sin_estado(item))


def calcular_faltantes(pedido):
    """Recalcula 'faltantes', 'total_estimado' y 'completo'.

    Úsala de nuevo después de cambiar el pedido a mano (por ejemplo, al rellenar
    los datos del cliente registrado o resolver "lo de siempre").

    Obligatorio: platos entendidos, cédula, nombre y dirección. La fecha y la
    hora solo faltan si el cliente las escribió de forma que no se entendió. El
    apellido es opcional. Los extras no impiden registrar el pedido.
    """
    cliente = pedido["cliente"]
    faltan = [c for c in CAMPOS_OBLIGATORIOS if not cliente.get(c)]
    faltan += [c for c in ("fecha", "hora") if not pedido.get(c)]
    if not (pedido["platos"] or pedido["ambiguos"] or pedido["lo_de_siempre"]):
        faltan.append("platos")
    pedido["faltantes"] = faltan
    pedido["total_estimado"] = round(sum(p["cantidad"] * p["precio"] for p in pedido["platos"]), 2)
    pedido["completo"] = not faltan and not pedido["ambiguos"]
    return faltan


def mensajes_para_cliente(pedido):
    """Lista de frases para pedirle al cliente que corrija o complete su pedido.

    Ejemplo:
        ["Faltó en su pedido: la dirección de entrega y la hora de entrega.",
         "No entendimos la fecha 'el finde'. Escríbala así: 15/11/2026, 'hoy' o 'mañana'.",
         "¿Cuál '2 pizzas' desea? Tenemos: Pizza margarita o Pizza pepperoni.",
         "'1 sushi' no es parte de nuestro menú; lo anotamos como extra (sujeto a disponibilidad)."]
    """
    mensajes = []
    invalidos = pedido.get("invalidos", {})
    faltan = [c for c in pedido["faltantes"] if c not in invalidos]
    if faltan:
        mensajes.append(f"Faltó en su pedido: {_enumerar([NOMBRES_LARGOS[c] for c in faltan])}.")
    mensajes += [invalidos[c] for c in (*CAMPOS_CLIENTE, "fecha", "hora") if c in invalidos]
    for item in pedido["ambiguos"]:
        opciones = _enumerar([o["nombre"] for o in item["opciones"]], "o")
        mensajes.append(f"¿Cuál '{item['texto']}' desea? Tenemos: {opciones}.")
    for item in pedido["extras"]:
        mensajes.append(f"'{item['texto']}' no es parte de nuestro menú; "
                        "lo anotamos como extra (sujeto a disponibilidad).")
    return mensajes


def resumen_para_operador(pedido):
    """Tarjeta del pedido para mostrar en la terminal (con colores si se puede)."""
    cliente = pedido["cliente"]
    nombre = " ".join(filter(None, (cliente["nombres"], cliente["apellidos"])))
    entrega = None
    if pedido["fecha"] and pedido["hora"]:
        entrega = f"{date.fromisoformat(pedido['fecha']).strftime('%d/%m/%Y')} · {pedido['hora']}"
    lineas = [
        e.titulo("Pedido"),
        e.campo("Cliente", nombre if cliente["nombres"] else None),
        e.campo("Cédula", cliente["cedula"]),
        e.campo("Dirección", cliente["direccion"]),
        e.campo("Entrega", entrega),
        "",
        "  " + e.negrita("Platos"),
    ]
    for plato in pedido["platos"]:
        izquierda = f"   {plato['cantidad']:>2} × {plato['nombre']}"
        importe = f"{plato['cantidad'] * plato['precio']:.2f}"
        lineas.append(izquierda.ljust(e.ANCHO - len(importe)) + importe)
        if plato["variacion"]:
            lineas.append(e.tenue(f"        {plato['variacion']}"))
    for item in pedido["ambiguos"]:
        lineas.append(e.amarillo(f"   ?  {item['texto']} (¿cuál?)"))
    for item in pedido["extras"]:
        lineas.append(e.magenta(f"   +  {item['texto']} (extra, fuera del menú)"))
    if pedido["lo_de_siempre"]:
        lineas.append(e.cian("   ↺  \"Lo de siempre\": buscar en su historial"))
    if not (pedido["platos"] or pedido["ambiguos"] or pedido["extras"] or pedido["lo_de_siempre"]):
        lineas.append("   " + e.rojo("ninguno"))
    total = f"{pedido['total_estimado']:.2f}"
    lineas += ["  " + e.tenue("─" * (e.ANCHO - 2)),
               "  " + e.negrita("Total".ljust(e.ANCHO - 2 - len(total)) + total)]

    if pedido["advertencias"]:
        lineas.append("")
        lineas += ["  " + e.aviso(a) for a in pedido["advertencias"]]
    mensajes = mensajes_para_cliente(pedido)
    if mensajes:
        lineas += ["", "  " + e.negrita("Para el cliente")]
        lineas += ["  " + e.info(m) for m in mensajes]
    lineas.append("")
    lineas.append("  " + (e.ok("COMPLETO") if pedido["completo"] else e.error("INCOMPLETO")))
    lineas.append(e.cierre())
    return "\n".join(lineas)


def _extraer_cliente(resultado, valores, texto_libre, hoy):
    cliente, avisos = resultado["cliente"], resultado["advertencias"]

    if "cedula" in valores:
        _guardar_validado(resultado, "cedula", valores["cedula"], hoy)
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
    if nombres:
        _guardar_validado(resultado, "nombres", nombres, hoy)
    if apellidos:
        _guardar_validado(resultado, "apellidos", apellidos, hoy)
    if valores.get("direccion"):
        _guardar_validado(resultado, "direccion", valores["direccion"], hoy)


def _extraer_fecha_hora(resultado, valores, texto_libre, hoy, ahora):
    avisos = resultado["advertencias"]
    fecha_hora = valores.get("fecha_hora", "")

    # Fecha: la etiqueta manda; si no hay etiqueta se busca en el texto libre.
    texto_fecha = valores.get("fecha") or fecha_hora or texto_libre
    if valores.get("fecha"):
        _guardar_validado(resultado, "fecha", valores["fecha"], hoy)
    elif normalizar_fecha(texto_fecha, hoy):
        _guardar_validado(resultado, "fecha", texto_fecha, hoy)

    # Hora: igual que la fecha.
    if valores.get("hora"):
        _guardar_validado(resultado, "hora", valores["hora"], hoy)
        _, dudosa = normalizar_hora(valores["hora"], solo_numero=True)
    else:
        hora, dudosa = normalizar_hora(fecha_hora)
        if not hora:
            hora, dudosa = normalizar_hora(texto_libre)
        resultado["hora"] = hora
    if dudosa and resultado["hora"]:
        avisos.append(f"La hora {resultado['hora']} no dice am/pm; se tomó en formato 24 h.")

    # Si no dijo fecha u hora, se asume el momento actual (o el de recepción del chat).
    if not resultado["fecha"] and "fecha" not in resultado["invalidos"]:
        resultado["fecha"] = ahora.date().isoformat()
        avisos.append("Sin fecha en el mensaje: se asumió hoy.")
    if not resultado["hora"] and "hora" not in resultado["invalidos"]:
        resultado["hora"] = ahora.strftime("%H:%M")
        avisos.append("Sin hora en el mensaje: se asumió la hora actual.")


def _guardar_validado(pedido, campo, valor, hoy):
    """Valida el dato; si es correcto lo guarda, si no lo anota en 'invalidos'."""
    normalizado, error = validar_campo(campo, valor, hoy)
    destino = pedido["cliente"] if campo in CAMPOS_CLIENTE else pedido
    destino[campo] = normalizado
    if error:
        pedido["invalidos"][campo] = error
    else:
        pedido["invalidos"].pop(campo, None)
    return error


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


def _sin_introduccion(texto):
    """'quiero 2 pizzas' -> '2 pizzas' (solo para que el texto del ítem quede limpio)."""
    return INTRODUCCION.sub("", texto.strip()).strip() or texto.strip()


def _sin_estado(item):
    return {k: v for k, v in item.items() if k != "estado"}


def _enumerar(partes, conector="y"):
    """['a', 'b', 'c'] -> 'a, b y c'."""
    if len(partes) <= 1:
        return "".join(partes)
    return ", ".join(partes[:-1]) + f" {conector} " + partes[-1]
