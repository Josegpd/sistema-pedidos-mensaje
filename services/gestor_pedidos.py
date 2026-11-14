from datetime import datetime
from models.pedido import Pedido
from models.cliente import Cliente
from models.pago import Pago
from cola_pedidos import ColaPedidos
from parser_mensajes import calcular_faltantes


class GestorPedidos:
    def __init__(self, cola:ColaPedidos):
        self.cola = cola
        self.historial:list[Pedido] = []
        self.pedidos_incompletos:list[dict] = []

        