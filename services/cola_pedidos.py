from models.pedido import Pedido

class ColaPedidos:
    def __init__(self):
        self.pedidos_pendientes:list[Pedido] = []

    # Encolar pedido
    def enqueue(self, pedido:Pedido)->None:

        # El pedido quedará en su orden cronológico como 'Pendiente' 
        pedido.set_estado("Pendiente")

        pos = self.__search_position(pedido.get_hora())
        self.pedidos_pendientes.insert(pos, pedido)



    # Convertir tiempo de 'HH:MM' a minutos
    def __change_hours_to_minutes(self, hora_str:str)->int:
        partes = hora_str.strip().split(':')

        # partes[0] = 'HH' y partes[1] = 'MM'
        return int(partes[0])*60 + int(partes[1])

    # Buscar el índice para insertar un nuevo elemento a través de búsqueda binaria
    def __search_position(self, hora_nuevo_str:str)->int:
        valor_nuevo = self.__change_hours_to_minutes(hora_nuevo_str)
        inicio = 0
        fin = len(self.pedidos_pendientes)-1

    # Método auxiliar que realiza la búsqueda binaria
    def __binary_search(self, x, inicio:int, fin:int):
        medio = (inicio+fin) // 2
        hora_medio = self.__change_hours_to_minutes(self.pedidos_pendientes[medio].get_hora())

        # El dato fue encontrado
        if hora_medio == x:
            return medio

        # El dato se encuentra en la mitad izquierda
        elif hora_medio < x:
            return self.__binary_search(x, inicio, medio-1)

        # El dato se encuentra en la mitad derecha
        else:
            return self.__binary_search(x,medio+1, fin)
        
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
        len(self.pedidos_pendientes)
