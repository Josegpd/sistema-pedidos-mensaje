from models.pedido import Pedido

class ColaPedidos:
    def __init__(self):
        self.pedidos_pendientes:list[Pedido] = []

    # Encolar pedido
    def enqueue(self, pedido:Pedido)->int:

        # El pedido quedará en su orden cronológico como 'Pendiente' 
        pedido.set_estado("Pendiente")

        pos = self.__search_position(pedido.get_hora())
        self.pedidos_pendientes.insert(pos, pedido)
        return pos # Posición (índice) en la que quedó el pedido


    # Convertir tiempo de 'HH:MM' a minutos
    def __change_hours_to_minutes(self, hora_str:str)->int:
        partes = hora_str.strip().split(':')

        # partes[0] = 'HH' y partes[1] = 'MM'
        return int(partes[0])*60 + int(partes[1])

    # Buscar el índice para insertar un nuevo elemento a través de búsqueda binaria
    def __search_position(self, hora_nuevo_str:str)->int:
        valor_nuevo = self.__change_hours_to_minutes(hora_nuevo_str)
        inicio = 0
        fin = len(self.pedidos_pendientes)

        # Búsqueda binaria: el pedido va después de los que tienen la misma hora o una anterior
        while inicio < fin:
            medio = (inicio + fin) // 2
            hora_medio = self.__change_hours_to_minutes(self.pedidos_pendientes[medio].get_hora())

            if hora_medio <= valor_nuevo:
                inicio = medio + 1
            else:
                fin = medio

        return inicio
        
    def is_empty(self)->bool:
        return len(self.pedidos_pendientes) == 0
    
    def dequeue(self):
        if self.is_empty():
            print("No hay pedidos pendientes")

        return self.pedidos_pendientes.pop(0)

    # Extrae y retorna un pedido de la cola por ID
    def dequeue_by_id(self, id_pedido:str)-> Pedido | None:
        for i, pedido in enumerate(self.pedidos_pendientes):
            if pedido.get_id() == id_pedido:
                return self.pedidos_pendientes.pop(i) # Se elimina el pedido encontrado y se retorna

        # retorna nulo si no encuentra el pedido
        return None

    # Consulta un pedido en la cola por ID sin extraerlo
    def get_by_id(self, id_pedido:str) -> Pedido | None:
        for pedido in self.pedidos_pendientes:
            if pedido.get_id() == id_pedido:
                return pedido

        return None # Se retorna None si no hay ningún pedido con el ID pasado como parámetro

    # Retorna la lista de pedidos pendientes
    def get_all(self) -> list[Pedido]:
        return list(self.pedidos_pendientes)

    # Método len sobrecargado
    def __len__(self) -> int:
        return len(self.pedidos_pendientes)
