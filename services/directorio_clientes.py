"""
Directorio de clientes e historial de compras.

Funcionalidades para el operador:
1. Listar los clientes registrados en el sistema (nombres, apellidos, cédula y dirección).
2. Consultar el historial de compras de un cliente buscándolo por cédula o por nombre.

Trabaja sobre los objetos en memoria (ClientesService / Cliente / Pedido), así
que siempre muestra lo mismo que el resto del sistema.
"""

import re

from models.cliente import Cliente
from parser_mensajes.normalizar import limpiar
from services.clientes_service import ClientesService
from utils.validaciones import leer_entero, leer_texto_no_vacio


def _solo_alfanumerico(texto: str) -> str:
    """'V-12.345.678' -> 'v12345678' (para comparar cédulas sin importar el formato)."""
    return re.sub(r"[^a-z0-9]", "", str(texto).lower())


def _solo_digitos(texto: str) -> str:
    return re.sub(r"\D", "", str(texto))


class GestorClientes:
    """Consulta el directorio de clientes y el historial de pedidos de cada uno."""

    def __init__(self, clientes_srv: ClientesService):
        self.clientes_srv = clientes_srv

    # Función 1: listado de clientes
    def listar_clientes(self) -> list[Cliente]:
        """Retorna los clientes registrados, ordenados por apellidos y nombres."""
        return sorted(
            self.clientes_srv.clientes.values(),
            key=lambda c: limpiar(f"{c.get_last_names() or ''} {c.get_names() or ''}"),
        )

    # Búsqueda por cédula o nombre
    def buscar_clientes(self, criterio: str) -> list[Cliente]:
        """
        Busca clientes por cédula o por nombre.
        - Si el criterio tiene dígitos se busca por cédula (acepta 'V-12.345.678' o '12345678').
        - Si no, se busca por nombre/apellido (sin importar mayúsculas ni acentos);
          todas las palabras escritas deben aparecer en el nombre completo.
        Una cédula escrita completa devuelve únicamente a ese cliente.
        """
        criterio = criterio.strip()
        if not criterio:
            return []

        clientes = list(self.clientes_srv.clientes.values())

        if any(ch.isdigit() for ch in criterio):
            buscado = _solo_alfanumerico(criterio)
            digitos = _solo_digitos(criterio)

            # Coincidencia exacta (con o sin la letra V/E)
            exactos = [
                c for c in clientes
                if buscado == _solo_alfanumerico(c.get_id())
                or (buscado == digitos and digitos == _solo_digitos(c.get_id()))
            ]
            if exactos:
                return exactos

            # Coincidencia parcial
            return [c for c in clientes if buscado in _solo_alfanumerico(c.get_id())]

        palabras = limpiar(criterio).split()
        if not palabras:
            return []
        encontrados = []
        for c in clientes:
            nombre_completo = limpiar(f"{c.get_names() or ''} {c.get_last_names() or ''}")
            if all(p in nombre_completo for p in palabras):
                encontrados.append(c)
        return encontrados

    # Función 2: historial de compras
    def obtener_historial(self, cliente: Cliente) -> list[dict]:
        """Detalle de cada pedido del cliente (el más reciente primero)."""
        historial = []
        for pedido in cliente.get_order_history():
            pagos = [
                {
                    "referencia": pago.get_id(),
                    "fecha": pago.get_date(),
                    "metodo": pago.get_pay_method(),
                    "monto": pago.get_monto(),
                }
                for pago in pedido.get_datos_pago()
            ]
            historial.append({
                "id_pedido": pedido.get_id(),
                "fecha": pedido.get_fecha() or "Fecha no registrada",
                "hora": pedido.get_hora() or "",
                "estado": pedido.get_estado(),
                "platos": [
                    {
                        "cantidad": d.get_cantidad(),
                        "nombre": d.get_plato().get_name(),
                        "precio": d.get_precio_unitario(),
                    }
                    for d in pedido.get_detalles()
                ],
                "pagos": pagos,
                "total": pedido.calcular_monto_total(),
                "saldo": max(0.0, pedido.calcular_saldo_restante()),
            })

        historial.sort(key=lambda p: (str(p["fecha"]), str(p["hora"])), reverse=True)
        return historial


# Presentación por consola
def mostrar_directorio_clientes(gestor: GestorClientes) -> None:
    """Imprime una tabla con todos los clientes registrados."""
    clientes = gestor.listar_clientes()

    print("\n" + "=" * 90)
    print(f"{'DIRECTORIO DE CLIENTES REGISTRADOS':^90}")
    print("=" * 90)
    if not clientes:
        print("No hay clientes registrados en el sistema.")
        print("=" * 90)
        return

    print(f"{'Nombres y apellidos':<30} | {'Cédula':<13} | {'Pedidos':>7} | {'Dirección':<28}")
    print("-" * 90)
    for c in clientes:
        nombre = f"{c.get_names()} {c.get_last_names()}".strip()
        direccion = c.get_address() or "No registrada"
        if len(nombre) > 30:
            nombre = nombre[:27] + "..."
        if len(direccion) > 28:
            direccion = direccion[:25] + "..."
        print(f"{nombre:<30} | {c.get_id():<13} | {len(c.get_order_history()):>7} | {direccion:<28}")
    print("-" * 90)
    print(f"Total de clientes: {len(clientes)}")
    print("=" * 90)


def _elegir_cliente(coincidencias: list[Cliente]) -> Cliente | None:
    """Si hay varios clientes con la búsqueda, deja que el operador escoja uno."""
    if len(coincidencias) == 1:
        return coincidencias[0]

    print(f"\nSe encontraron {len(coincidencias)} clientes:")
    for i, c in enumerate(coincidencias, 1):
        print(f"  [{i}] {c.get_names()} {c.get_last_names()} | Cédula: {c.get_id()}")
    sel = leer_entero("Seleccione el número de cliente (0 para volver): ", 0, len(coincidencias))
    if sel == 0:
        return None
    return coincidencias[sel - 1]


def consultar_historial_cliente(gestor: GestorClientes, criterio: str) -> None:
    """Busca un cliente por cédula o nombre y muestra su historial de compras."""
    coincidencias = gestor.buscar_clientes(criterio)

    print("\n" + "=" * 80)
    print(f"{'HISTORIAL DE COMPRAS':^80}")
    print("=" * 80)

    if not coincidencias:
        print(f"No se encontró ningún cliente registrado con: '{criterio}'")
        print("=" * 80)
        return

    cliente = _elegir_cliente(coincidencias)
    if cliente is None:
        return

    historial = gestor.obtener_historial(cliente)
    print(f"Cliente: {cliente.get_names()} {cliente.get_last_names()} | Cédula: {cliente.get_id()}")
    print(f"Dirección: {cliente.get_address() or 'No registrada'}")
    print(f"Total de pedidos realizados: {len(historial)}")
    print("-" * 80)

    if not historial:
        print("Este cliente aún no tiene pedidos registrados.")
        print("=" * 80)
        return

    for idx, ped in enumerate(historial, 1):
        print(f"[{idx}] Pedido {ped['id_pedido']} | Fecha: {ped['fecha']} {ped['hora']} | Estado: {ped['estado']}")
        print("    Platos:")
        for p in ped["platos"]:
            print(f"      - {p['cantidad']}x {p['nombre']} (${p['precio']:.2f} c/u)")
        print(f"    Total: ${ped['total']:.2f} | Saldo pendiente: ${ped['saldo']:.2f}")
        if ped["pagos"]:
            print("    Pagos:")
            for pg in ped["pagos"]:
                print(f"      - {pg['metodo']}: ${pg['monto']:.2f} (ref. {pg['referencia']}, {pg['fecha']})")
        else:
            print("    Pagos: sin pagos registrados")
        print("-" * 80)
    print("=" * 80)


def pedir_y_consultar_historial(gestor: GestorClientes) -> None:
    """Pide el criterio al operador y muestra el historial."""
    criterio = leer_texto_no_vacio("Ingrese la cédula o el nombre del cliente: ")
    consultar_historial_cliente(gestor, criterio)
