"""Extracción de cédula, nombre, fecha y hora a partir de texto."""

import re
from datetime import date, timedelta

from .normalizar import capitalizar_nombre, limpiar, quitar_acentos

# Etiqueta escrita por el cliente (ya limpia) -> campo interno.
ETIQUETAS = {
    "cedula": "cedula", "ci": "cedula", "c i": "cedula", "cedula de identidad": "cedula",
    "documento": "cedula", "nro de cedula": "cedula", "numero de cedula": "cedula",
    "nombre": "nombre", "nombres": "nombres",
    "nombre completo": "nombre_completo", "cliente": "nombre_completo",
    "nombre y apellido": "nombre_completo", "nombres y apellidos": "nombre_completo",
    "apellido": "apellidos", "apellidos": "apellidos",
    "direccion": "direccion", "dir": "direccion", "direccion de entrega": "direccion",
    "entregar en": "direccion", "ubicacion": "direccion", "delivery": "direccion",
    "fecha": "fecha", "dia": "fecha", "fecha de entrega": "fecha",
    "hora": "hora", "hora de entrega": "hora",
    "fecha y hora": "fecha_hora", "fecha hora": "fecha_hora", "para": "fecha_hora",
    "entrega": "fecha_hora",
    "pedido": "pedido", "platos": "pedido", "orden": "pedido", "comida": "pedido",
    "productos": "pedido", "quiero": "pedido",
    "telefono": "otro", "tlf": "otro", "celular": "otro", "nota": "otro", "notas": "otro",
    "observacion": "otro", "observaciones": "otro",
}

LINEA_ETIQUETA = re.compile(r"^\s*[-*•·]?\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ.\s/]{1,30}?)\s*[:=]\s*(.*)$")

# Encabezado de un chat exportado/copiado de WhatsApp:
#   "[11/11/26, 12:30:05] Maria: texto"   o   "11/11/2026, 12:30 p. m. - Maria: texto"
ENCABEZADO_CHAT = re.compile(
    r"^\[?(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2})(?::\d{2})?\s*([ap]\.?\s?m\.?)?\]?\s*-?\s*[^:]{1,40}:\s?",
    re.IGNORECASE,
)

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

FECHA_NUMERICA = re.compile(r"\b(\d{1,2})\s*[/-]\s*(\d{1,2})(?:\s*[/-]\s*(\d{2,4}))?\b")
FECHA_TEXTO = re.compile(r"\b(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")(?:\s+(?:de\s+|del\s+)?(\d{4}))?\b")

HORA = re.compile(
    r"(?P<pre>\ba\s+las?\s+)?\b(?P<h>\d{1,2})(?:\s*[:h]\s*(?P<m>\d{2})\b)?\s*"
    r"(?P<suf>a\.?\s?m\b\.?|p\.?\s?m\b\.?|hrs?\b|horas\b|h\b|de\s+la\s+(?:manana|tarde|noche)|del\s+mediodia)?"
)

CEDULA = re.compile(
    r"(?:(?<![A-Za-z])([VvEe])\s*[-.]?\s*)?(?<![\d.])(\d{1,3}(?:\.\d{3}){1,2}|\d{6,9})(?![\d.]*\d)"
)
CEDULA_EN_TEXTO = re.compile(
    r"(?:\bc\.?\s?i\b\.?|\bc[eé]dula\b)\s*(?:n[°ºo.]\s*)?[:#]?\s*(.{0,20})"
    r"|\b([VvEe]\s?[-.]\s?\d{1,2}\.?\d{3}\.?\d{3})\b",
    re.IGNORECASE,
)

NOMBRE_EN_TEXTO = re.compile(
    r"\b(?:soy|me llamo|mi nombre es|a nombre de)\s+((?:[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+\s*){1,5})",
    re.IGNORECASE,
)
CORTE_NOMBRE = {"y", "quiero", "quisiera", "mi", "con", "para", "ci", "cedula", "cédula",
                "les", "te", "le", "por", "del", "de", "el", "la", "desde", "en", "a"}


def etiqueta_de(linea):
    """Si la línea es 'Etiqueta: valor' con una etiqueta conocida devuelve (campo, valor)."""
    encontrado = LINEA_ETIQUETA.match(linea)
    if not encontrado:
        return None
    campo = ETIQUETAS.get(limpiar(encontrado.group(1)))
    if campo is None:
        return None
    return campo, encontrado.group(2).strip()


def quitar_encabezado_chat(linea):
    """Devuelve (linea_sin_encabezado, 'YYYY-MM-DD HH:MM' o None)."""
    encontrado = ENCABEZADO_CHAT.match(linea)
    if not encontrado:
        return linea, None
    fecha = normalizar_fecha(encontrado.group(1), date.today())
    hora = normalizar_hora(encontrado.group(2) + " " + (encontrado.group(3) or ""))[0]
    if not fecha or not hora:
        return linea, None
    return linea[encontrado.end():], f"{fecha} {hora}"


def normalizar_cedula(texto):
    """'V-12.345.678', 'v12345678', '12345678' -> 'V-12345678'. Devuelve None si no es válida."""
    encontrado = CEDULA.search(texto or "")
    if not encontrado:
        return None
    numero = encontrado.group(2).replace(".", "")
    if not 6 <= len(numero) <= 9:
        return None
    return f"{(encontrado.group(1) or 'V').upper()}-{int(numero)}"


def buscar_cedula(texto):
    """Busca una cédula en texto libre ('mi CI es 12345678', 'V-12345678')."""
    for encontrado in CEDULA_EN_TEXTO.finditer(texto):
        cedula = normalizar_cedula(encontrado.group(1) or encontrado.group(2))
        if cedula:
            return cedula
    return None


def buscar_nombre(texto):
    """'Hola, soy maria gonzalez y quiero...' -> 'Maria Gonzalez'."""
    encontrado = NOMBRE_EN_TEXTO.search(texto)
    if not encontrado:
        return None
    palabras = []
    for palabra in encontrado.group(1).split():
        if palabra.lower() in CORTE_NOMBRE:
            break
        palabras.append(palabra)
    return capitalizar_nombre(" ".join(palabras)) or None


def dividir_nombre_completo(nombre):
    """'Juan Carlos Perez Gomez' -> ('Juan Carlos', 'Perez Gomez').

    Con 3 palabras asume 1 nombre y 2 apellidos (no siempre es cierto, por eso
    quien llama agrega una advertencia).
    """
    palabras = nombre.split()
    if len(palabras) < 2:
        return capitalizar_nombre(nombre), ""
    corte = 2 if len(palabras) >= 4 else 1
    return capitalizar_nombre(" ".join(palabras[:corte])), capitalizar_nombre(" ".join(palabras[corte:]))


def _texto_fecha(texto):
    return quitar_acentos(texto.lower())


def normalizar_fecha(texto, hoy):
    """'11/11/2026', '11-11', '11 de noviembre', 'hoy', 'mañana' -> 'YYYY-MM-DD' o None."""
    texto = _texto_fecha(texto)
    if re.search(r"\bpasado\s+manana\b", texto):
        return (hoy + timedelta(days=2)).isoformat()
    if re.search(r"(?<!la )\bmanana\b", texto):
        return (hoy + timedelta(days=1)).isoformat()
    if re.search(r"\bhoy\b", texto):
        return hoy.isoformat()
    for patron in (FECHA_NUMERICA, FECHA_TEXTO):
        for encontrado in patron.finditer(texto):
            dia, mes, anio = encontrado.groups()
            mes = MESES.get(mes) or int(mes)
            anio = int(anio) if anio else hoy.year
            if anio < 100:
                anio += 2000
            try:
                return date(anio, mes, int(dia)).isoformat()
            except ValueError:
                continue
    return None


def normalizar_hora(texto, solo_numero=False):
    """'1:30 pm', '13:30', '7pm', 'a las 8', '1:30 de la tarde' -> ('HH:MM', dudosa).

    `dudosa` es True si la hora no indica am/pm y podría ser de mañana o tarde.
    Con `solo_numero=True` también acepta un número suelto ('Hora: 8').
    Devuelve (None, False) si no encuentra ninguna hora.
    """
    texto = _texto_fecha(texto)
    for encontrado in HORA.finditer(texto):
        pre, h, m, suf = encontrado.group("pre", "h", "m", "suf")
        numero_suelto = solo_numero and texto.strip() == h
        if not (pre or m or suf or numero_suelto):
            continue
        hora, minutos = int(h), int(m or 0)
        suf = (suf or "").replace(".", "").replace(" ", "")
        tarde = suf in ("pm", "delatarde", "delanoche") or (suf == "delmediodia" and hora < 12)
        if tarde and hora < 12:
            hora += 12
        if suf == "am" and hora == 12:
            hora = 0
        if hora > 23 or minutos > 59:
            continue
        dudosa = not suf and 1 <= hora <= 11
        return f"{hora:02d}:{minutos:02d}", dudosa
    return None, False
