class DetallePedido:
    def __init__(self, plato, cantidad: int):
        self.__plato = plato
        self.__cantidad = cantidad
        self.__precio_unitario = plato.get_price()  # Guardar el precio del momento

    def get_plato(self):
        return self.__plato

    def get_cantidad(self):
        return self.__cantidad

    def get_precio_unitario(self):
        return self.__precio_unitario

    def calcular_subtotal(self) -> float:
        return self.__cantidad * self.__precio_unitario

    def __str__(self):
        return f"{self.__cantidad}x {self.__plato.get_name()} (c/u: ${self.__precio_unitario:.2f}) -> Subtotal: ${self.calcular_subtotal():.2f}"