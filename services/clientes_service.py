from datetime import date

from models.cliente import Cliente
from parser_mensajes.campos import normalizar_cedula

# Días sin pedir para considerar a un cliente inactivo
DIAS_INACTIVO = 30


def _no_cancelado(pedido) -> bool:
    return not (pedido.get_estado() or "").startswith("Cancelado")


class ClientesService:
    def __init__(self, clientes_dict: dict[str, Cliente] = None):
        # Clave: cédula normalizada (ej: 'V-12345678')
        self.clientes = clientes_dict if clientes_dict is not None else {}

    def buscar_por_cedula(self, cedula: str) -> Cliente | None:
        # Acepta '12345678', 'V-12.345.678', 'v12345678'... todas son la misma cédula
        return self.clientes.get(normalizar_cedula(cedula) or cedula)

    def registrar_o_actualizar(self, cedula: str, nombres: str, apellidos: str, direccion: str) -> Cliente:
        cliente = self.buscar_por_cedula(cedula)
        if cliente:
            # Si el cliente escribió datos nuevos (por ejemplo, otra dirección), se actualizan
            cliente.actualizar_datos(nombres=nombres, apellidos=apellidos, direccion=direccion)
            return cliente
        nuevo_cliente = Cliente(id=cedula, nombres=nombres, apellidos=apellidos, direccion=direccion)
        self.clientes[cedula] = nuevo_cliente
        return nuevo_cliente

    def resolver_lo_de_siempre(self, cliente: Cliente) -> list | None:
        # Los platos del último pedido que no fue cancelado
        validos = [p for p in cliente.get_order_history() if _no_cancelado(p)]
        if not validos:
            return None
        ultimo_pedido = max(validos, key=lambda p: (p.get_fecha() or "", p.get_hora() or ""))
        return ultimo_pedido.get_detalles()

    def clasificar(self, cliente: Cliente, hoy: date | None = None) -> str:
        """'nuevo', 'inactivo', 'vip', 'recurrente' u 'ocasional' (sin contar cancelados)."""
        validos = [p for p in cliente.get_order_history() if _no_cancelado(p)]
        if not validos:
            return "nuevo"
        ultima_fecha = max(p.get_fecha() or "" for p in validos)
        hoy = hoy or date.today()
        try:
            dias = (hoy - date.fromisoformat(ultima_fecha)).days
        except ValueError:
            dias = 0
        if dias > DIAS_INACTIVO:
            return "inactivo"
        if len(validos) > 10:
            return "vip"
        if len(validos) >= 3:
            return "recurrente"
        return "ocasional"

    def obtener_promocion(self, cliente: Cliente, hoy: date | None = None) -> str:
        # Clasifica y devuelve la sugerencia de promoción para el operador.
        return {
            "nuevo": "Cliente NUEVO -> Sugerir: '10% de descuento en su primer pedido'.",
            "inactivo": f"Cliente INACTIVO (más de {DIAS_INACTIVO} días sin pedir) -> Sugerir: '15% de descuento por volver'.",
            "vip": "Cliente VIP / FRECUENTE -> Sugerir: 'Bebida gratis por fidelidad'.",
            "recurrente": "Cliente RECURRENTE -> Sugerir: '5% de descuento en el pedido'.",
            "ocasional": "Cliente OCASIONAL -> Sugerir: 'Envío gratis en su próximo pedido'.",
        }[self.clasificar(cliente, hoy)]
