class Mensaje:

    def __init__(self, id_msg: str, texto: str, fecha_recepcion: str, estado: str = "Recibido"):
        self.__id = id_msg
        self.__text = texto
        self.__reception_date = fecha_recepcion
        self.__status = estado

    def get_id(self):
        return self.__id

    def get_text(self):
        return self.__text

    def get_reception_date(self):
        return self.__reception_date

    def get_status(self):
        return self.__status

    def marcar_como_leido(self):
        self.__status = "Leído"