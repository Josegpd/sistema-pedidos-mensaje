class Menu:
    def __init__(self):
        # Tabla Hash: La clave es el ID del plato y el valor es el objeto Plato
        self.__menu = {}

    def agregar_plato_al_menu(self, id_plato: str, plato):
        self.__menu[id_plato] = plato

    def buscar_plato(self, id_plato: str):
        # Búsqueda directa en O(1) usando la tabla hash
        return self.__menu.get(id_plato, None)

    def eliminar_plato_del_menu(self, id_plato: str):
        if id_plato in self.__menu:
            del self.__menu[id_plato]
        else:
            print(f"El plato con ID {id_plato} no existe en el menú.")

    def mostrar_menu(self):
        print("========================================")
        print("          MENÚ DE LA POLLERÍA           ")
        print("========================================")
        for id, plato in self.__menu.items():
            print(f"[{id}] {plato.get_name()} - ${plato.get_price():.2f}")
        print("========================================")