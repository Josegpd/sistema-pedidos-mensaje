class Cliente:

    def __init__(self, id: str, nombres: str, apellidos: str,
                 direccion: str):
        self.__id = id
        self.__names = nombres
        self.__last_names = apellidos
        self.__address = direccion
        self.__order_history = [] # comienza sin pedidos

    def get_id(self):
        return self.__id

    def get_names(self):
        return self.__names

    def get_last_names(self):
        return self.__last_names

    def get_address(self):
        return self.__address

    def get_order_history(self):
        return self.__order_history

    # Insertar una orden
    def push_new_order(self, order):
        self.__order_history.append(order)

    # Eliminar la ultima orden del historial
    def pop_last_order(self):
        if len(self.__order_history) == 0:
            print("No se pueden eliminar pedidos, el historial esta vacio")
        else:
            self.__order_history.pop()

    # Obtener la cantidad de dinero gastado
    def get_total_expense(self):
        return sum(pedido.get_total() for pedido in self.__order_history)