"""Funciones de limpieza de texto usadas por todo el parser."""

import re
import unicodedata

NUMEROS_EN_LETRAS = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "docena": 12, "media docena": 6,
}


def quitar_acentos(texto):
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def limpiar(texto):
    """Minúsculas, sin acentos, sin signos de puntuación y sin espacios repetidos."""
    texto = quitar_acentos(texto.lower())
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return " ".join(texto.split())


def singular(palabra):
    """Singular aproximado: 'hamburguesas' -> 'hamburguesa', 'panes' -> 'pan'."""
    if len(palabra) > 4 and palabra.endswith("es") and palabra[-3] in "lnrdz":
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def normalizar(texto):
    """Forma canónica para comparar nombres de platos y alias."""
    return " ".join(singular(p) for p in limpiar(texto).split())


def capitalizar_nombre(texto):
    """'mARIA  jose' -> 'Maria Jose' (conserva los acentos que haya)."""
    return " ".join(p.capitalize() for p in texto.split())
