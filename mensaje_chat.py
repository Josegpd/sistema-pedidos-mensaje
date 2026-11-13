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

    def a_dict(self):
        """Convierte el mensaje a diccionario."""
        return {
            "id": self.__id,
            "texto": self.__text,
            "fecha_recepcion": self.__reception_date,
            "estado": self.__status
        }

    @classmethod
    def desde_dict(cls, d):
        """Reconstruye el mensaje desde un diccionario."""
        if not d:
            return None
        return cls(
            id_msg = d.get("id"),
            texto = d.get("texto"),
            fecha_recepcion = d.get("fecha_recepcion"),
            estado = d.get("estado", "Recibido")
        )