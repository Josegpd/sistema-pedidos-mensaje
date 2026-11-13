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

    def a_dict(self):
        # Guardamos el ID del plato para poder buscarlo después en el menu
        return {
            "id_plato": self.__plato.get_id() if hasattr(self.__plato, "get_id") else None,
            "cantidad": self.__cantidad,
            "precio_unitario": self.__precio_unitario
        }

    @classmethod
    def desde_dict(cls, d, menu_obj):
        id_plato = d.get("id_plato")
        cantidad = d.get("cantidad")
        precio_unit = d.get("precio_unitario")
        
        # Enlazamos de nuevo con el objeto Plato real usando el Menu cargado en memoria
        plato_obj = menu_obj.buscar_plato(id_plato)
        
        return cls(plato=plato_obj, cantidad=cantidad)