"""Reconocimiento de platos y cantidades contra el catálogo (menú)."""

import difflib
import json
import re

from .normalizar import NUMEROS_EN_LETRAS, limpiar, normalizar

# Palabras de relleno que se ignoran antes de buscar el plato.
RELLENO = {
    "quiero", "quisiera", "queria", "dame", "deme", "manda", "mandame", "envia",
    "enviame", "pido", "pedir", "por", "favor", "porfa", "porfavor", "pf",
    "plis", "please", "tambien", "ademas", "y", "mas", "me", "nos", "de", "del",
    "orden", "ordenes", "unas", "unos", "el", "la", "los", "las",
}

PALABRAS_VARIACION = r"(?:sin|extra|bien|poco|poca|aparte|doble\s+queso|con\s+extra)"


class Catalogo:
    """Índice de platos por nombre y alias normalizados.

    Recibe la lista de diccionarios del menú:
        {"id": "P001", "nombre": "...", "precio": 5.0, "alias": ["...", ...]}
    """

    def __init__(self, platos):
        self.platos = {p["id"]: p for p in platos}
        self.claves = {}  # texto normalizado -> lista de ids
        for plato in platos:
            for texto in [plato["nombre"], *plato.get("alias", [])]:
                ids = self.claves.setdefault(normalizar(texto), [])
                if plato["id"] not in ids:
                    ids.append(plato["id"])

    @classmethod
    def desde_archivo(cls, ruta):
        with open(ruta, encoding="utf-8") as archivo:
            return cls(json.load(archivo))

    def buscar(self, texto):
        """Devuelve la lista de ids que coinciden.

        0 ids -> no reconocido, 1 id -> reconocido, varios -> ambiguo.
        """
        norm = normalizar(texto)
        if not norm:
            return []
        # 1. Coincidencia exacta con nombre o alias.
        if norm in self.claves:
            return list(self.claves[norm])
        # 2. Algún nombre/alias aparece completo dentro del texto: gana el más largo.
        contenidas = [c for c in self.claves if f" {c} " in f" {norm} "]
        if contenidas:
            largo = max(len(c) for c in contenidas)
            return _unir(self.claves[c] for c in contenidas if len(c) == largo)
        # 3. Todas las palabras del texto aparecen en algún nombre ("empanada").
        palabras = set(norm.split())
        parciales = [c for c in self.claves if palabras <= set(c.split())]
        if parciales:
            return _unir(self.claves[c] for c in parciales)
        # 4. Errores de tipeo ("hamburgesa", "piza peperoni").
        parecidas = difflib.get_close_matches(norm, self.claves, n=1, cutoff=0.8)
        if parecidas:
            return list(self.claves[parecidas[0]])
        return []

    def resumen(self, id_plato):
        plato = self.platos[id_plato]
        return {"id": plato["id"], "nombre": plato["nombre"]}


def _unir(listas):
    resultado = []
    for ids in listas:
        for id_plato in ids:
            if id_plato not in resultado:
                resultado.append(id_plato)
    return resultado


def separar_items(linea):
    """'2 hamburguesas, 1 refresco y una pizza' -> ['2 hamburguesas', '1 refresco', 'una pizza']."""
    # Las comas dentro de paréntesis son parte de la variación, no separan platos.
    linea = re.sub(r"\([^)]*\)", lambda m: m.group().replace(",", " /"), linea)
    numeros = "|".join(sorted(NUMEROS_EN_LETRAS, key=len, reverse=True))
    patron = rf"\s*(?:[,;+]|\s(?:y|e|mas|más)\s(?=(?:\d|{numeros})\b))\s*"
    return [parte.strip() for parte in re.split(patron, linea, flags=re.IGNORECASE) if parte.strip()]


def separar_variacion(texto):
    """'hamburguesa (sin cebolla)' -> ('hamburguesa', 'sin cebolla')."""
    variaciones = []
    for contenido in re.findall(r"\(([^)]*)\)", texto):
        variaciones.append(" ".join(contenido.replace(" /", ",").replace("/", ",").split()))
    texto = re.sub(r"\([^)]*\)", " ", texto)
    encontrado = re.search(rf"(?:\s+-\s*|\s+con\s+|\s+)?\b{PALABRAS_VARIACION}\b.*$", texto, re.IGNORECASE)
    if encontrado:
        variaciones.append(encontrado.group().strip(" -").strip())
        texto = texto[: encontrado.start()]
    return texto.strip(" -"), ", ".join(v for v in variaciones if v)


def separar_cantidad(texto):
    """'2x hamburguesas' / 'hamburguesas x2' / 'dos hamburguesas' -> (2, 'hamburguesas').

    Si no hay cantidad explícita, devuelve 1. `texto` debe venir ya limpio.
    """
    palabras = [p for p in texto.split() if p not in RELLENO]
    texto = " ".join(palabras)

    encontrado = re.match(r"^(\d+)\s*(?:x\b)?\s*(.*)$", texto)
    if encontrado:
        return int(encontrado.group(1)), encontrado.group(2)
    encontrado = re.match(r"^(.*?)\s*(?:x\s*)?(\d+)$", texto)
    if encontrado:
        return int(encontrado.group(2)), encontrado.group(1)
    for palabra in sorted(NUMEROS_EN_LETRAS, key=len, reverse=True):
        if texto == palabra or texto.startswith(palabra + " "):
            resto = texto[len(palabra):].split()
            return NUMEROS_EN_LETRAS[palabra], " ".join(p for p in resto if p not in RELLENO)
    return 1, texto


def analizar_item(texto, catalogo):
    """Analiza un solo ítem ('2 pizzas pepperoni sin aceitunas').

    Devuelve un dict con 'estado' = 'ok' | 'ambiguo' | 'no_reconocido'.
    """
    original = texto.strip(" -*•·\t")
    sin_variacion, variacion = separar_variacion(original)
    cantidad, nombre = separar_cantidad(limpiar(sin_variacion))
    ids = catalogo.buscar(nombre) if nombre else []

    item = {"texto": original, "cantidad": cantidad, "variacion": variacion}
    if len(ids) == 1:
        plato = catalogo.platos[ids[0]]
        item.update(estado="ok", id_plato=plato["id"], nombre=plato["nombre"],
                    precio=plato.get("precio", 0))
    elif ids:
        item.update(estado="ambiguo", opciones=[catalogo.resumen(i) for i in ids])
    else:
        item.update(estado="no_reconocido")
    return item
