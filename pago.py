class Pago:
    def __init__(self, id: str, cliente, fecha: str, metodo_pago: str, monto: float):
        self.__id = id
        self.__client = cliente
        self.__date = fecha
        self.__pay_method = metodo_pago
        self.__amount = monto

    def get_id(self):
        return self.__id

    def get_client(self):
        return self.__client

    def get_date(self):
        return self.__date

    def get_pay_method(self):
        return self.__pay_method

    def get_monto(self):
        return self.__amount

    def __str__(self):
        return (
            f"==================================================\n"
            f"\nPago #{self.__id}\n"
            f"==================================================\n"
            f"\nFecha: {self.__date}\n"
            f"Cliente: {self.__client.get_names} {self.__client.get_last_names}\n"
            f"Método de pago: {self.__pay_method}\n"
            f"Monto: {self.__amount}"
        )