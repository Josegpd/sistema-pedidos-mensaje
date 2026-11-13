class Plato:
    def __init__(self, nombre: str, precio: float):
        self.__name = nombre # Incluye si el plato tiene una variacion
        self.__price = precio
        self.__orders = []

    def get_name(self):
        return self.__name

    def get_price(self):
        return self.__price

    def set_name(self, new_name: str):
        self.__name = new_name

    def set_price(self, new_price: int):
        self.__price = new_price

    def push_new_order(self, order):
        self.__orders.append(order)

    def pop_last_order(self):
        if len(self.__orders) == 0:
            print("El plato no tiene pedidos, no se pueden eliminar pedidos")
        else:
            self.__orders.pop()

    def __str__(self):
        return self.__name