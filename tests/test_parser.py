"""Pruebas del parser. Ejecutar desde la raíz del proyecto:

    python -m unittest discover tests
"""

import unittest
from datetime import date
from pathlib import Path

from parser_mensajes import Catalogo, analizar_mensaje, calcular_faltantes, leer_lote, separar_lote
from parser_mensajes.campos import normalizar_cedula, normalizar_fecha, normalizar_hora
from parser_mensajes.entrada import leer_mensaje_pegado

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = Catalogo.desde_archivo(RAIZ / "datos" / "menu.json")
LOTE = dict(leer_lote(RAIZ / "pruebas" / "mensajes_prueba.txt"))
HOY = date(2026, 11, 12)


def analizar(titulo):
    return analizar_mensaje(LOTE[titulo], CATALOGO, hoy=HOY)


def platos(pedido):
    return {p["id_plato"]: p["cantidad"] for p in pedido["platos"]}


class TestLote(unittest.TestCase):
    def test_completo_etiquetado(self):
        p = analizar("completo_etiquetado")
        self.assertTrue(p["completo"])
        self.assertEqual(p["cliente"], {"cedula": "V-12345678", "nombres": "Juan Carlos",
                                        "apellidos": "Pérez Gómez",
                                        "direccion": "Av. Bolívar, edificio Sol, piso 3"})
        self.assertEqual((p["fecha"], p["hora"]), ("2026-11-15", "13:30"))
        self.assertEqual(platos(p), {"P001": 2, "P009": 1, "P006": 3})
        self.assertEqual(p["total_estimado"], 16.0)

    def test_whatsapp_usa_fecha_de_recepcion(self):
        p = analizar_mensaje(LOTE["completo_whatsapp"], CATALOGO)
        self.assertEqual(p["fecha_recepcion"], "2026-11-12 11:05")
        self.assertEqual(p["fecha"], "2026-11-12")
        self.assertEqual(p["cliente"]["nombres"], "Maria")
        self.assertEqual(p["cliente"]["apellidos"], "Gonzalez")
        self.assertEqual(platos(p), {"P004": 1, "P008": 2, "P010": 2})
        self.assertTrue(p["completo"])

    def test_variaciones_y_formatos_de_cantidad(self):
        p = analizar("completo_una_linea_por_plato_variaciones")
        self.assertEqual(platos(p), {"P002": 1, "P008": 2, "P009": 3})
        self.assertEqual(p["platos"][0]["variacion"], "sin cebolla, sin tomate")
        self.assertEqual(p["platos"][1]["variacion"], "extra queso")
        self.assertEqual((p["fecha"], p["hora"]), ("2026-11-13", "19:00"))
        self.assertEqual(p["cliente"]["apellidos"], "Rojas Díaz")

    def test_texto_libre(self):
        p = analizar("texto_libre")
        self.assertEqual(p["cliente"]["cedula"], "V-15222333")
        self.assertEqual(p["cliente"]["nombres"], "Pedro")
        self.assertEqual(p["cliente"]["apellidos"], "Ramirez")
        self.assertEqual((p["fecha"], p["hora"]), ("2026-11-12", "13:30"))
        self.assertEqual(platos(p), {"P005": 2, "P009": 1})
        self.assertTrue(p["completo"])

    def test_faltantes(self):
        self.assertEqual(analizar("incompleto_sin_direccion_ni_hora")["faltantes"],
                         ["direccion", "fecha", "hora"])
        self.assertEqual(analizar("incompleto_sin_platos")["faltantes"], ["platos"])
        self.assertEqual(len(analizar("solo_saludo")["faltantes"]), 7)

    def test_lo_de_siempre(self):
        p = analizar("lo_de_siempre")
        self.assertTrue(p["lo_de_siempre"])
        self.assertEqual(p["cliente"]["cedula"], "V-12345678")
        self.assertNotIn("platos", p["faltantes"])
        self.assertEqual(p["hora"], "20:00")

        p = analizar("lo_de_siempre_con_extra")
        self.assertTrue(p["lo_de_siempre"])
        self.assertEqual(platos(p), {"P010": 1})
        self.assertEqual(p["no_reconocidos"], [])

    def test_ambiguos(self):
        p = analizar("ambiguo_pizza")
        self.assertFalse(p["completo"])
        self.assertEqual([[o["id"] for o in a["opciones"]] for a in p["ambiguos"]],
                         [["P003", "P004"], ["P005", "P006"]])
        self.assertEqual(p["ambiguos"][0]["cantidad"], 2)

    def test_no_reconocido(self):
        p = analizar("no_reconocido")
        self.assertEqual([i["texto"] for i in p["no_reconocidos"]], ["1 sushi"])
        self.assertFalse(p["completo"])

    def test_errores_de_tipeo(self):
        self.assertEqual(platos(analizar("errores_de_tipeo")), {"P001": 2, "P004": 1})

    def test_duplicados_dan_el_mismo_resultado(self):
        a, b = analizar("duplicado_a"), analizar("duplicado_b")
        self.assertEqual((a["cliente"], a["fecha"], a["hora"], a["platos"]),
                         (b["cliente"], b["fecha"], b["hora"], b["platos"]))

    def test_plato_repetido_se_suma(self):
        p = analizar("plato_repetido_en_el_mensaje")
        self.assertEqual(platos(p), {"P009": 3})
        self.assertTrue(p["advertencias"])

    def test_cedula_invalida(self):
        p = analizar("cedula_invalida")
        self.assertIn("cedula", p["faltantes"])
        self.assertTrue(any("no es válida" in a for a in p["advertencias"]))

    def test_completar_a_mano(self):
        p = analizar("incompleto_sin_direccion_ni_hora")
        p["cliente"]["direccion"] = "Calle 1"
        p["fecha"], p["hora"] = "2026-11-12", "12:00"
        self.assertEqual(calcular_faltantes(p), [])
        self.assertTrue(p["completo"])


class TestCampos(unittest.TestCase):
    def test_cedula(self):
        self.assertEqual(normalizar_cedula("V-12.345.678"), "V-12345678")
        self.assertEqual(normalizar_cedula("e 8123456"), "E-8123456")
        self.assertIsNone(normalizar_cedula("123"))

    def test_fecha(self):
        self.assertEqual(normalizar_fecha("15/11/2026", HOY), "2026-11-15")
        self.assertEqual(normalizar_fecha("15-11-26", HOY), "2026-11-15")
        self.assertEqual(normalizar_fecha("20 de diciembre", HOY), "2026-12-20")
        self.assertEqual(normalizar_fecha("pasado mañana", HOY), "2026-11-14")
        self.assertIsNone(normalizar_fecha("a las 10 de la mañana", HOY))
        self.assertIsNone(normalizar_fecha("31/02/2026", HOY))

    def test_hora(self):
        self.assertEqual(normalizar_hora("1:30 pm"), ("13:30", False))
        self.assertEqual(normalizar_hora("7 p.m."), ("19:00", False))
        self.assertEqual(normalizar_hora("12 am"), ("00:00", False))
        self.assertEqual(normalizar_hora("a las 8"), ("08:00", True))
        self.assertEqual(normalizar_hora("1:30 de la tarde"), ("13:30", False))
        self.assertEqual(normalizar_hora("8", solo_numero=True), ("08:00", True))
        self.assertEqual(normalizar_hora("quiero 2 hamburguesas"), (None, False))


class TestEntrada(unittest.TestCase):
    def test_leer_mensaje_pegado_hasta_fin(self):
        lineas = iter(["Cédula: 123", "", "Pedido:", "- 1 refresco", "fin", "no se lee"])
        texto = leer_mensaje_pegado(leer=lambda: next(lineas), mostrar=lambda *_: None)
        self.assertEqual(texto, "Cédula: 123\n\nPedido:\n- 1 refresco")

    def test_leer_mensaje_pegado_hasta_eof(self):
        lineas = iter(["hola"])

        def leer():
            try:
                return next(lineas)
            except StopIteration:
                raise EOFError

        self.assertEqual(leer_mensaje_pegado(leer=leer, mostrar=lambda *_: None), "hola")

    def test_separar_lote(self):
        self.assertEqual(separar_lote("# comentario\n=== a ===\nuno\n=== b ===\ndos\n"),
                         [("a", "uno"), ("b", "dos")])


if __name__ == "__main__":
    unittest.main()
