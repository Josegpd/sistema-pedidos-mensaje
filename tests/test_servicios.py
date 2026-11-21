"""Pruebas de los servicios (clientes, pedidos, cola, reporte y persistencia).

    python -m unittest discover tests
"""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta

from models import Cliente, Mensaje, Pedido, Plato
from services import persistencia
from services.clientes_service import ClientesService
from services.cola_pedidos import ColaPedidos
from services.gestor_pedidos import GestorPedidos
from services.reporte import generar_reporte_del_dia

HOY = date.today()
HAMBURGUESA = Plato("P001", "Hamburguesa clasica", 5.0)
REFRESCO = Plato("P009", "Refresco", 1.5)


def nuevo_pedido(cliente, fecha=HOY, hora="13:00", platos=((HAMBURGUESA, 2),), texto="hola"):
    pedido = Pedido(hora, fecha.isoformat(), 0, cliente, Mensaje("1", texto, ""))
    for plato, cantidad in platos:
        pedido.agregar_detalle(plato, cantidad)
    pedido._Pedido__total = pedido.calcular_monto_total()
    return pedido


def datos_parser(cedula="V-12345678", fecha=HOY, hora="13:00", texto="otro texto"):
    return {"cliente": {"cedula": cedula}, "fecha": fecha.isoformat(), "hora": hora, "texto_original": texto}


class TestClientes(unittest.TestCase):
    def setUp(self):
        self.srv = ClientesService()
        self.ana = self.srv.registrar_o_actualizar("V-12345678", "Ana", "Pérez", "Calle 3")

    def test_buscar_cedula_en_cualquier_formato(self):
        for escrita in ("12345678", "V-12.345.678", "v12345678", "V-12345678"):
            self.assertIs(self.srv.buscar_por_cedula(escrita), self.ana, escrita)

    def test_direccion_nueva_se_actualiza_y_pedidos_viejos_no_cambian(self):
        viejo = nuevo_pedido(self.ana)
        self.srv.registrar_o_actualizar("V-12345678", "Ana", "", "Av. Nueva 99")
        self.assertEqual(self.ana.get_address(), "Av. Nueva 99")
        self.assertEqual(self.ana.get_last_names(), "Pérez")        # vacío no borra
        self.assertEqual(viejo.get_direccion(), "Calle 3")

    def test_lo_de_siempre_ignora_cancelados(self):
        nuevo_pedido(self.ana, fecha=HOY - timedelta(days=2), platos=((HAMBURGUESA, 1),))
        nuevo_pedido(self.ana, fecha=HOY, platos=((REFRESCO, 3),)).set_estado("Cancelado: prueba")
        detalles = self.srv.resolver_lo_de_siempre(self.ana)
        self.assertEqual([d.get_plato().get_id() for d in detalles], ["P001"])

    def test_clasificacion(self):
        self.assertEqual(self.srv.clasificar(self.ana), "nuevo")
        nuevo_pedido(self.ana).set_estado("Cancelado: x")
        self.assertEqual(self.srv.clasificar(self.ana), "nuevo")      # cancelados no cuentan
        nuevo_pedido(self.ana, fecha=HOY - timedelta(days=45))
        self.assertEqual(self.srv.clasificar(self.ana), "inactivo")
        nuevo_pedido(self.ana)
        self.assertEqual(self.srv.clasificar(self.ana), "ocasional")
        nuevo_pedido(self.ana)
        self.assertEqual(self.srv.clasificar(self.ana), "recurrente")
        self.assertIn("RECURRENTE", self.srv.obtener_promocion(self.ana))


class TestGestorYCola(unittest.TestCase):
    def setUp(self):
        self.cola = ColaPedidos()
        self.gestor = GestorPedidos(self.cola)
        self.ana = Cliente("V-12345678", "Ana", "Pérez", "Calle 3")

    def test_cola_ordena_por_fecha_y_hora(self):
        manana = nuevo_pedido(self.ana, fecha=HOY + timedelta(days=1), hora="09:00")
        hoy_tarde = nuevo_pedido(self.ana, fecha=HOY, hora="20:00")
        hoy_temprano = nuevo_pedido(self.ana, fecha=HOY, hora="12:00")
        for p in (manana, hoy_tarde, hoy_temprano):
            self.gestor.registrar_pedido_completo(p)
        self.assertEqual(self.cola.get_all(), [hoy_temprano, hoy_tarde, manana])
        self.assertEqual(len(self.cola), 3)

    def test_duplicados(self):
        pedido = nuevo_pedido(self.ana, texto="Pedido: 2 hamburguesas")
        self.gestor.registrar_pedido_completo(pedido)
        self.assertTrue(self.gestor.es_duplicado(datos_parser())[0])                       # misma fecha y hora
        self.assertTrue(self.gestor.es_duplicado(datos_parser(texto="Pedido: 2 hamburguesas", hora="18:00"))[0])
        self.assertFalse(self.gestor.es_duplicado(datos_parser(fecha=HOY + timedelta(days=1)))[0])
        self.assertFalse(self.gestor.es_duplicado(datos_parser(cedula="V-999999"))[0])
        self.gestor.marcar_como_cancelado(pedido.get_id(), "no contesta")
        self.assertFalse(self.gestor.es_duplicado(datos_parser())[0])                      # cancelado no cuenta
        self.assertEqual(pedido.get_estado(), "Cancelado: no contesta")

    def test_pagos(self):
        pedido = nuevo_pedido(self.ana)                     # total 10.00
        self.gestor.registrar_pedido_completo(pedido)
        self.assertIs(self.gestor.buscar_en_historial(pedido.get_id()), pedido)
        self.assertFalse(self.gestor.registro_de_pagos(pedido, "Efectivo", "r1", 50)[0])   # de más
        ok, saldo, _ = self.gestor.registro_de_pagos(pedido, "Efectivo", "r1", 4)
        self.assertTrue(ok)
        self.assertEqual(saldo, 6.0)
        self.gestor.marcar_como_cancelado(pedido.get_id(), "x")
        self.assertFalse(self.gestor.registro_de_pagos(pedido, "Efectivo", "r2", 1)[0])    # cancelado

    def test_ids_consecutivos(self):
        a, b = nuevo_pedido(self.ana), nuevo_pedido(self.ana)
        self.assertEqual(int(b.get_id()[1:]), int(a.get_id()[1:]) + 1)


class TestReporte(unittest.TestCase):
    def test_reporte_cuenta_entregados_de_hoy_con_cobrado_y_por_cobrar(self):
        ana = Cliente("V-1", "Ana", "", "Calle 3")
        pagado = nuevo_pedido(ana, platos=((HAMBURGUESA, 2),))                  # 10.00
        pagado.push_pago(type("P", (), {"get_monto": lambda self: 10.0})())
        sin_pagar = nuevo_pedido(ana, platos=((REFRESCO, 2),))                  # 3.00
        ayer = nuevo_pedido(ana, fecha=HOY - timedelta(days=1))
        pendiente = nuevo_pedido(ana)
        cancelado = nuevo_pedido(ana)
        for p in (pagado, sin_pagar, ayer):
            p.set_estado("Entregado")
        cancelado.set_estado("Cancelado: x")
        with tempfile.TemporaryDirectory() as carpeta, redirect_stdout(io.StringIO()):
            antes = os.getcwd()
            os.chdir(carpeta)
            try:
                texto = generar_reporte_del_dia({"pedidos": [pagado, sin_pagar, ayer, pendiente, cancelado]})
            finally:
                os.chdir(antes)
        self.assertIn("Pedidos entregados: 2    Cancelados: 1", texto)
        lineas = {l.split("|")[0].strip(): l.split("|")[-1].strip() for l in texto.splitlines() if "|" in l}
        self.assertEqual(lineas["TOTAL"], "13.00")
        self.assertEqual(lineas["Cobrado"], "10.00")
        self.assertEqual(lineas["Por cobrar"], "3.00")


class TestPersistencia(unittest.TestCase):
    def test_guardar_y_cargar(self):
        with tempfile.TemporaryDirectory() as carpeta:
            rutas_originales = dict(persistencia.RUTAS)
            for clave in persistencia.RUTAS:
                persistencia.RUTAS[clave] = os.path.join(carpeta, f"{clave}.json")
            persistencia.guardar_json(persistencia.RUTAS["menu"], [HAMBURGUESA.a_dict()])
            try:
                ana = Cliente("V-12345678", "Ana", "Pérez", "Calle 3")
                pedido = nuevo_pedido(ana, platos=())
                pedido.agregar_detalle(HAMBURGUESA, 1, "sin cebolla")
                pedido.agregar_extra("1 sushi")
                incompleto = {"cliente": {"cedula": None}, "faltantes": ["direccion"], "texto_original": "hola"}
                persistencia.guardar_todo({"clientes": {ana.get_id(): ana}, "pedidos": [pedido],
                                           "incompletos": [incompleto]})
                ana.actualizar_datos(direccion="Av. Nueva 99")

                d = persistencia.cargar_todo()
                ana2 = d["clientes"]["V-12345678"]
                pedido2 = d["pedidos"][0]
                self.assertEqual(pedido2.get_id(), pedido.get_id())
                self.assertEqual(pedido2.get_direccion(), "Calle 3")
                self.assertEqual(pedido2.get_detalles()[0].get_variacion(), "sin cebolla")
                self.assertEqual(pedido2.get_extras(), ["1 sushi"])
                self.assertEqual(len(ana2.get_order_history()), 1)          # historial reconstruido
                self.assertEqual(d["incompletos"], [incompleto])
                siguiente = nuevo_pedido(ana2)
                self.assertGreater(int(siguiente.get_id()[1:]), int(pedido.get_id()[1:]))
            finally:
                persistencia.RUTAS.clear()
                persistencia.RUTAS.update(rutas_originales)


if __name__ == "__main__":
    unittest.main()
