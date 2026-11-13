from detalle_pedido import DetallePedido
from mensaje_chat import Mensaje
from pago import Pago
from random import randint

class Pedido:
    
    # Constructor
    def __init__(self, hora: str, fecha: str, total: float, cliente, mensaje, estado: str = "Pendiente"):
        self.__id = randint(1, 1000000) # id unico para ese pedido
        self.__hour = hora
        self.__date = fecha
        self.__total = total
        self.__client = cliente # Datos del cliente
        self.__message = mensaje # Datos del mensaje recibido
        self.__details = [] # Lista de detalles del pedido
        self.__pay_data = [] # Pedido sin pagos
        self.__status = estado

        self.__client.push_new_order(self) # Agregar la orden al historial del cliente

    def get_id(self):
        return "#" + str(self.__id)

    def get_hora(self):
        return self.__hour

    def get_fecha(self):
        return self.__date

    def get_estado(self):
        return self.__status

    def set_estado(self, new_status):
        self.__status = new_status

    def get_total(self):
        return self.__total
    
    def get_detalles(self):
        return self.__details

    def get_cliente(self):
        return self.__client
    
    def get_datos_pago(self):
        return self.__pay_data

    def get_mensaje(self):
        return self.__message

    def agregar_detalle(self, plato, cantidad: int):
        detalle = DetallePedido(plato, cantidad)
        self.__details.append(detalle)
    
    def quitar_ultimo_detalle(self):
        if len(self.__details) == 0:
            print("No hay detalles en el pedido para eliminar.")
        else:
            self.__details.pop()

    # Insertar un pago
    def push_pago(self, pay):
        self.__pay_data.append(pay)

    # Eliminar el ultimo pago hecho
    def pop_pago(self):
        if len(self.__pay_data) == 0:
            print(f"No hay pagos asociados al pedido #{self.__id} de {self.__client.get_id()}")
        else:
            self.__pay_data.pop()

    # Calcular el costo de cada comida del pedido
    def calcular_monto_total(self) -> float:
        return sum(comida.get_price() for comida in self.__details)

    # Devoler el saldo restante a pagar
    def calcular_saldo_restante(self) -> float:
        total_pagado = sum(pago.get_monto() for pago in self.__pay_data)
        return self.__total - total_pagado

    def __str__(self):
        detalles_str = "\n".join([f" - {d}" for d in self.__details])
        return (
            f"==================================================\n"
            f"Pedido N-{self.__id} [{self.__status}]\n"
            f"==================================================\n"
            f"Fecha: {self.__date} | Hora: {self.__hour}\n"
            f"Cliente: {self.__client.get_names()} {self.__client.get_last_names()}\n"
            f"Detalle de Platos:\n{detalles_str}\n"
            f"Total a pagar: ${self.calcular_monto_total():.2f}"
        )

    def a_dict(self):
        return {
            "id": self.__id,
            "hora": self.__hour,
            "fecha": self.__date,
            "total": self.__total,
            "id_cliente": self.__client.get_id() if self.__client else None,
            "mensaje": self.__message.a_dict() if self.__message else None,
            "detalles": [detalle.a_dict() for detalle in self.__details],
            "pagos": [pago.a_dict() for pago in self.__pay_data],
            "estado": self.__status
        }

    @classmethod
    def desde_dict(cls, d, clientes_dict, menu_obj):
        id_cliente = d.get("id_cliente")
        cliente = clientes_dict.get(id_cliente)
        
        # Reconstruir mensaje
        msg_dict = d.get("mensaje")
        mensaje = Mensaje.desde_dict(msg_dict) if msg_dict else None
        
        pedido = cls(
            hora = d.get("hora"),
            fecha = d.get("fecha"),
            total = d.get("total"),
            cliente = cliente,
            mensaje = mensaje,
            estado = d.get("estado", "Pendiente")
        )
        # Asignar el ID exacto que tenia guardado
        pedido.__id = d.get("id")
        
        # Reconstruir detalles con el menu
        for det_dict in d.get("detalles", []):
            detalle = DetallePedido.desde_dict(det_dict, menu_obj)
            pedido.__details.append(detalle)
        
        # Reconstruir pagos con el diccionario de clientes
        for pago_dict in d.get("pagos", []):
            pago = Pago.desde_dict(pago_dict, clientes_dict)
            pedido.__pay_data.append(pago)
        
        return pedido