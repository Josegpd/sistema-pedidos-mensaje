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

    # Deteccion de duplicados
    def es_duplicado(self, datos_parser: dict) -> tuple[bool, str]:
        cedula_nueva = datos_parser.get("cliente", {}).get("cedula")
        hora_nueva = datos_parser.get("hora")
        texto_nuevo = datos_parser.get("texto_original", "").strip()

        for pedido in self.historial_general:
            # Coincidencia por texto idéntico
            if pedido.get_mensaje() and pedido.get_mensaje().get_text().strip() == texto_nuevo:
                return True, f"Existe un pedido con el mismo texto exacto (ID: {pedido.get_id()})."

            # Coincidencia por cliente y hora
            if pedido.get_cliente() and pedido.get_cliente().get_id() == cedula_nueva:
                if pedido.get_hora() == hora_nueva:
                    return True, f"El cliente {cedula_nueva} ya tiene un pedido para las {hora_nueva} (ID: {pedido.get_id()})."

        return False, ""

    # Registrar pedidos incompletos
    def registrar_incompleto(self, datos_parser: dict) -> None:
        self.pedidos_incompletos.append(datos_parser)

    # Retorna lista de pedidos incompletos
    def obtener_incompletos(self) -> list[dict]:
        return self.pedidos_incompletos

    # confirmar y encolar pedido completo
    def registrar_pedido_completo(self, pedido:Pedido) -> int:
        self.historial.append(pedido)
        pos = self.cola.enqueue(pedido)
        return pos

    # Marcar pedido como entregado
    def marcar_como_entregado(self, id_pedido:int) -> bool:
        pedido = self.cola.dequeue_by_id(id_pedido)

        # Si el pedido existe, se marca como 'entregado'
        if pedido:
            pedido.set_estado("Entregado")
            return True
        
        return False

    # Marcar pedido como cancelado
    def marcar_como_cancelado(self, id_pedido:int, motivo:str) -> bool:
        pedido = self.cola.dequeue_by_id(id_pedido)

        # Si el pedido existe, se marca como 'Cancelado''
        if pedido:
            pedido.set_estado(f"Cancelado: {motivo.strip}")
            return True
        
        return False    

    