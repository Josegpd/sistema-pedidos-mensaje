from datetime import datetime
from models.pedido import Pedido
from models.cliente import Cliente
from models.pago import Pago
from .cola_pedidos import ColaPedidos
from parser_mensajes import calcular_faltantes

class GestorPedidos:
    def __init__(self, cola:ColaPedidos):
        self.cola = cola
        self.historial:list[Pedido] = []
        self.pedidos_incompletos:list[dict] = []

    # Deteccion de duplicados
    def es_duplicado(self, datos_parser: dict) -> tuple[bool, str]:
        cedula_nueva = datos_parser.get("cliente", {}).get("cedula")
        fecha_nueva = datos_parser.get("fecha")
        hora_nueva = datos_parser.get("hora")
        texto_nuevo = (datos_parser.get("texto_original") or "").strip()

        for pedido in self.historial:
            # Un pedido cancelado no cuenta: el cliente puede volver a pedir lo mismo
            if (pedido.get_estado() or "").startswith("Cancelado"):
                continue

            # Coincidencia por texto idéntico
            if texto_nuevo and pedido.get_mensaje() and pedido.get_mensaje().get_text().strip() == texto_nuevo:
                return True, f"Existe un pedido con el mismo texto exacto (ID: {pedido.get_id()})."

            # Coincidencia por cliente, fecha y hora
            if cedula_nueva and pedido.get_cliente() and pedido.get_cliente().get_id() == cedula_nueva:
                if pedido.get_fecha() == fecha_nueva and pedido.get_hora() == hora_nueva:
                    return True, (f"El cliente {cedula_nueva} ya tiene un pedido para el {fecha_nueva} "
                                  f"a las {hora_nueva} (ID: {pedido.get_id()}).")

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
    def marcar_como_entregado(self, id_pedido:str) -> bool:
        pedido = self.cola.dequeue_by_id(id_pedido)

        # Si el pedido existe, se marca como 'entregado'
        if pedido:
            pedido.set_estado("Entregado")
            return True
        
        return False

    # Marcar pedido como cancelado
    def marcar_como_cancelado(self, id_pedido:str, motivo:str) -> bool:
        pedido = self.cola.dequeue_by_id(id_pedido)

        # Si el pedido existe, se marca como 'Cancelado''
        if pedido:
            pedido.set_estado(f"Cancelado: {motivo.strip()}")
            return True
        
        return False    

    def registro_de_pagos(self, pedido:Pedido, metodo_pago:str, referencia:str, monto:float) -> tuple[bool, float, str]:

        saldo_pendiente = pedido.calcular_saldo_restante()

        # A un pedido cancelado no se le registran pagos
        if (pedido.get_estado() or "").startswith("Cancelado"):
            return False, saldo_pendiente, "El pedido está cancelado; no se le pueden registrar pagos"

        # Si no hay saldo pendiente
        if saldo_pendiente <= 0:
            return False, 0.0, "El pedido ya se encuentra completamente pagado"

        # Validar que el monto no sea negativo ni cero
        if monto <= 0:
            return False, saldo_pendiente, "El monto debe ser mayor a cero"

        # No se puede pagar más de lo que se debe
        if monto > saldo_pendiente + 0.001:
            return False, saldo_pendiente, f"El monto supera el saldo pendiente (${saldo_pendiente:.2f})"

        # Establecer fecha de pago como la actual
        fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M")

        pago = Pago(
            id=referencia,
            cliente=pedido.get_cliente(),
            fecha=fecha_pago,
            metodo_pago=metodo_pago,
            monto=monto
        )

        pedido.push_pago(pago)
        nuevo_saldo = pedido.calcular_saldo_restante()

        # Pago registrado exitosamente
        return True, max(0.0,nuevo_saldo), "Pago registrado exitosamente"

    # Búsqueda de pedido por ID en el historial
    def buscar_en_historial(self, id_pedido: str) -> Pedido | None:
        objetivo = id_pedido.strip()
        for p in self.historial:
            if str(p.get_id()).strip() == objetivo:
                return p

        # Retorna None si el pedido no existe
        return None

    