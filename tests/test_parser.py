"""Pruebas del parser. Ejecutar desde la raíz del proyecto:

    python -m unittest discover tests
"""

import unittest
from datetime import date, datetime
from pathlib import Path

from parser_mensajes import (
    Catalogo, agregar_platos, analizar_mensaje, calcular_faltantes, completar_campo,
    completar_pedido, confirmar_pedido, leer_lote, mensajes_para_cliente, resolver_ambiguo,
    separar_lote,
)


def responder(*respuestas):
    """Simula lo que escribe el operador, en orden."""
    it = iter(respuestas)
    return lambda _: next(it)
from parser_mensajes.campos import normalizar_cedula, normalizar_fecha, normalizar_hora
from parser_mensajes.entrada import leer_mensaje_pegado

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = Catalogo.desde_archivo(RAIZ / "datos" / "menu.json")
LOTE = dict(leer_lote(RAIZ / "pruebas" / "mensajes_prueba.txt"))
HOY = date(2026, 11, 12)
AHORA = datetime(2026, 11, 12, 16, 0)


def analizar(titulo):
    return analizar_mensaje(LOTE[titulo], CATALOGO, hoy=HOY, ahora=AHORA)


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
        p = analizar("incompleto_sin_direccion_ni_hora")
        self.assertEqual(p["faltantes"], ["direccion"])
        self.assertEqual((p["fecha"], p["hora"]), ("2026-11-12", "16:00"))   # se asume ahora
        self.assertEqual(analizar("incompleto_sin_platos")["faltantes"], ["platos"])
        self.assertEqual(analizar("solo_saludo")["faltantes"],
                         ["cedula", "nombres", "direccion", "platos"])

    def test_cedula_obligatoria_y_apellido_opcional(self):
        texto = "Nombre: Luis\nDirección: Calle Real 10\nPedido: 1 jugo"
        p = analizar_mensaje(texto, CATALOGO, hoy=HOY, ahora=AHORA)
        self.assertEqual(p["faltantes"], ["cedula"])
        self.assertFalse(p["completo"])
        self.assertIsNone(completar_campo(p, "cedula", "20111222", HOY))
        self.assertIsNone(p["cliente"]["apellidos"])
        self.assertTrue(p["completo"])

    def test_lo_de_siempre(self):
        p = analizar("lo_de_siempre")
        self.assertTrue(p["lo_de_siempre"])
        self.assertEqual(p["cliente"]["cedula"], "V-12345678")
        self.assertNotIn("platos", p["faltantes"])
        self.assertEqual(p["hora"], "20:00")

        p = analizar("lo_de_siempre_con_extra")
        self.assertTrue(p["lo_de_siempre"])
        self.assertEqual(platos(p), {"P010": 1})
        self.assertEqual(p["extras"], [])

    def test_ambiguos(self):
        p = analizar("ambiguo_pizza")
        self.assertFalse(p["completo"])
        self.assertEqual([[o["id"] for o in a["opciones"]] for a in p["ambiguos"]],
                         [["P003", "P004"], ["P005", "P006"]])
        self.assertEqual(p["ambiguos"][0]["cantidad"], 2)

    def test_plato_fuera_del_menu_va_a_extras(self):
        p = analizar("plato_fuera_del_menu")
        self.assertEqual([i["texto"] for i in p["extras"]], ["1 sushi"])
        self.assertEqual(platos(p), {"P009": 1})
        self.assertEqual(p["total_estimado"], 1.5)
        self.assertTrue(p["completo"])
        self.assertIn("no es parte de nuestro menú", mensajes_para_cliente(p)[0])

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
        self.assertIsNone(p["cliente"]["cedula"])
        self.assertEqual(p["faltantes"], ["cedula"])
        self.assertFalse(p["completo"])
        self.assertIn("no es válida", p["invalidos"]["cedula"])
        self.assertIn("no es válida", mensajes_para_cliente(p)[0])

    def test_completar_a_mano(self):
        p = analizar("incompleto_sin_direccion_ni_hora")
        p["cliente"]["direccion"] = "Calle 1"
        p["fecha"], p["hora"] = "2026-11-12", "12:00"
        self.assertEqual(calcular_faltantes(p), [])
        self.assertTrue(p["completo"])


    def test_datos_mal_escritos(self):
        p = analizar("datos_mal_escritos")
        self.assertEqual(set(p["invalidos"]), {"cedula", "nombres", "direccion", "fecha", "hora"})
        self.assertEqual(p["faltantes"], ["cedula", "nombres", "direccion", "fecha", "hora"])
        self.assertIsNone(p["cliente"]["nombres"])
        self.assertFalse(p["completo"])
        mensajes = mensajes_para_cliente(p)
        self.assertEqual(len(mensajes), 5)
        self.assertTrue(any("No entendimos la hora 'cuando puedan'" in m for m in mensajes))

    def test_texto_libre_con_plato_fuera_del_menu(self):
        p = analizar_mensaje("Hola, quiero 2 pizzas y 1 sushi", CATALOGO, hoy=HOY, ahora=AHORA)
        self.assertEqual([a["texto"] for a in p["ambiguos"]], ["2 pizzas"])
        self.assertEqual([e["texto"] for e in p["extras"]], ["1 sushi"])
        p = analizar_mensaje("Hola buenas, ¿están abiertos?", CATALOGO, hoy=HOY, ahora=AHORA)
        self.assertEqual(p["extras"], [])

    def test_fecha_pasada_no_se_acepta(self):
        p = analizar("fecha_pasada")
        self.assertIsNone(p["fecha"])
        self.assertIn("ya pasó", p["invalidos"]["fecha"])

    def test_mensajes_para_cliente(self):
        p = analizar("ambiguo_pizza")
        self.assertEqual(mensajes_para_cliente(p), [
            "¿Cuál '2 pizzas' desea? Tenemos: Pizza margarita o Pizza pepperoni.",
            "¿Cuál '1 empanada' desea? Tenemos: Empanada de carne o Empanada de queso.",
        ])
        p = analizar("incompleto_sin_direccion_ni_hora")
        self.assertEqual(mensajes_para_cliente(p), [
            "Faltó en su pedido: la dirección de entrega."])


class TestCompletar(unittest.TestCase):
    def test_completar_campo_valida_y_normaliza(self):
        p = analizar("datos_mal_escritos")
        p["cliente"]["nombres"] = "Mario"
        self.assertIsNone(completar_campo(p, "cedula", "V-20.111.222", HOY))
        self.assertIn("No entendimos la hora", completar_campo(p, "hora", "a la hora de siempre", HOY))
        self.assertIsNone(p["hora"])
        self.assertIsNone(completar_campo(p, "hora", "1:30 pm", HOY))
        self.assertEqual(p["hora"], "13:30")
        self.assertIn("ya pasó", completar_campo(p, "fecha", "01/11/2026", HOY))
        self.assertIsNone(completar_campo(p, "fecha", "mañana", HOY))
        self.assertEqual(p["fecha"], "2026-11-13")
        self.assertIsNotNone(completar_campo(p, "direccion", "x", HOY))
        self.assertIsNone(completar_campo(p, "direccion", "Calle 9, casa 2", HOY))
        self.assertTrue(p["completo"])

    def test_resolver_ambiguo(self):
        p = analizar("ambiguo_pizza")
        self.assertFalse(resolver_ambiguo(p, 0, "P009"))          # no es una opción
        self.assertTrue(resolver_ambiguo(p, 0, "P004"))
        self.assertTrue(resolver_ambiguo(p, 0, None))             # la empanada pasa a extras
        self.assertEqual(platos(p), {"P004": 2})
        self.assertEqual(p["extras"][0]["texto"], "1 empanada")
        self.assertEqual(p["total_estimado"], 18.0)
        self.assertTrue(p["completo"])

    def test_agregar_platos(self):
        p = analizar("incompleto_sin_platos")
        agregar_platos(p, "2 hamburguesas, 1 sushi", CATALOGO)
        self.assertEqual(platos(p), {"P001": 2})
        self.assertEqual(len(p["extras"]), 1)
        self.assertTrue(p["completo"])

    def test_completar_pedido_interactivo(self):
        p = analizar("datos_mal_escritos")
        p["ambiguos"] = analizar("ambiguo_pizza")["ambiguos"][:1]
        respuestas = iter([
            "9",                       # opción inválida
            "2",                       # Pizza pepperoni
            "12", "V-12.345.678",      # cédula inválida y luego válida
            "Mario123", "Mario",       # nombre inválido y luego válido
            "Av. Lara, casa 5",        # dirección
            "el finde", "15/11/2026",  # fecha
            "a las 8 pm",              # hora
        ])
        salida = []
        listo = completar_pedido(p, CATALOGO, leer=lambda _: next(respuestas),
                                 mostrar=salida.append, hoy=HOY)
        self.assertTrue(listo)
        self.assertEqual(p["cliente"]["cedula"], "V-12345678")
        self.assertEqual((p["fecha"], p["hora"]), ("2026-11-15", "20:00"))
        self.assertEqual(platos(p), {"P009": 1, "P004": 2})
        self.assertEqual(p["invalidos"], {})
        self.assertTrue(any("Opción no válida" in s for s in salida))

    def test_confirmar_directo(self):
        p = analizar("completo_etiquetado")
        self.assertTrue(confirmar_pedido(p, CATALOGO, leer=responder("1"),
                                         mostrar=lambda *_: None, hoy=HOY))

    def test_confirmar_con_correcciones(self):
        p = analizar("completo_etiquetado")
        listo = confirmar_pedido(p, CATALOGO, mostrar=lambda *_: None, hoy=HOY, leer=responder(
            "2", "4", "Av. Lara, casa 5",          # corregir dirección
            "2", "6", "lueguito", "8pm",            # hora inválida y luego válida
            "2", "3", "",                            # borrar apellido (opcional)
            "2", "8", "2",                           # quitar el refresco
            "2", "7", "1 jugo",                      # agregar un jugo
            "1",                                     # confirmar
        ))
        self.assertTrue(listo)
        self.assertEqual(p["cliente"]["direccion"], "Av. Lara, casa 5")
        self.assertEqual(p["hora"], "20:00")
        self.assertFalse(any("hora" in a for a in p["advertencias"]))
        self.assertIsNone(p["cliente"]["apellidos"])
        self.assertEqual(platos(p), {"P001": 2, "P006": 3, "P010": 1})

    def test_quitar_todos_los_platos_vuelve_a_preguntar(self):
        p = analizar("plato_repetido_en_el_mensaje")      # solo tiene refrescos
        listo = confirmar_pedido(p, CATALOGO, mostrar=lambda *_: None, hoy=HOY, leer=responder(
            "2", "8", "1",           # quitar el único plato -> queda incompleto
            "2 empanadas de carne",  # completar_pedido pide platos otra vez
            "1",
        ))
        self.assertTrue(listo)
        self.assertEqual(platos(p), {"P005": 2})

    def test_confirmar_cancelar(self):
        p = analizar("completo_etiquetado")
        self.assertFalse(confirmar_pedido(p, CATALOGO, leer=responder("0"),
                                          mostrar=lambda *_: None, hoy=HOY))

    def test_completar_pedido_cancelar(self):
        p = analizar("solo_saludo")
        listo = completar_pedido(p, CATALOGO, leer=lambda _: "cancelar", mostrar=lambda *_: None)
        self.assertFalse(listo)


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

    def test_fin_al_final_de_la_linea(self):
        lineas = iter(["Cédula: 123", "Quiero 2 pizzas FIN", "no se lee"])
        texto = leer_mensaje_pegado(leer=lambda: next(lineas), mostrar=lambda *_: None)
        self.assertEqual(texto, "Cédula: 123\nQuiero 2 pizzas")

    def test_fin_en_minusculas_dentro_de_texto_no_corta(self):
        lineas = iter(["Dirección: Calle El Fin", "fin"])
        texto = leer_mensaje_pegado(leer=lambda: next(lineas), mostrar=lambda *_: None)
        self.assertEqual(texto, "Dirección: Calle El Fin")

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
