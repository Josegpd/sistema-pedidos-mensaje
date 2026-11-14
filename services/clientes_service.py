from models.cliente import Cliente

class ClientesService:
    def __init__(self, clientes_dict: dict[str, Cliente] = None):
        # Clave: cédula normalizada (ej: 'V-12345678')
        self.clientes = clientes_dict if clientes_dict is not None else {}

    def buscar_por_cedula(self, cedula: str) -> Cliente | None:
        return self.clientes.get(cedula)

    def registrar_o_actualizar(self, cedula: str, nombres: str, apellidos: str, direccion: str) -> Cliente:
        if cedula in self.clientes:
            cliente = self.clientes[cedula]

            # Si no tenía dirección y ahora sí, se actualiza
            return cliente
        nuevo_cliente = Cliente(id=cedula, nombres=nombres, apellidos=apellidos, direccion=direccion)
        self.clientes[cedula] = nuevo_cliente
        return nuevo_cliente

    def resolver_lo_de_siempre(self, cliente: Cliente) -> list | None:

        # Obtiene los platos del pedido más frecuente o del último pedido del cliente.
        historial = cliente.get_order_history()
        if not historial:
            return None

        # Tomar los platos del último pedido como 'lo de siempre'
        ultimo_pedido = historial[-1]
        return ultimo_pedido.get_detalles()

    def obtener_promocion(self, cliente: Cliente) -> str:
        # clasifica y devuelve la sugerencia de promoción para el operador.
        historial = cliente.get_order_history()
        total_pedidos = len(historial)

        if total_pedidos == 0:
            return "Cliente NUEVO -> Sugerir: '10% de descuento en su primer pedido'."
        elif total_pedidos > 10:
            return "Cliente VIP / FRECUENTE -> Sugerir: 'Bebida gratis por fidelidad'."
        elif total_pedidos >= 3:
            return "Cliente RECURRENTE -> Sugerir: '5% de descuento en el pedido'."
        else:
            return "Cliente OCASIONAL -> Sugerir: 'Envío gratis en su próximo pedido'."