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
            f"Cliente: {self.__client.get_names()} {self.__client.get_last_names()}\n"
            f"Método de pago: {self.__pay_method}\n"
            f"Monto: {self.__amount}"
        )

    def a_dict(self):
        return {
            "id": self.__id,
            "id_cliente": self.__client.get_id() if self.__client else None,
            "fecha": self.__date,
            "metodo_pago": self.__pay_method,
            "monto": self.__amount
        }

    @classmethod
    def desde_dict(cls, d, clientes_dict):
        id_cliente = d.get("id_cliente")
        cliente = clientes_dict.get(id_cliente)
        return cls(
            id=d.get("id"),
            cliente=cliente,
            fecha=d.get("fecha"),
            metodo_pago=d.get("metodo_pago"),
            monto=d.get("monto")
        )