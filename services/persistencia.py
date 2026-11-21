import os
import json
from models.cliente import Cliente
from models.pedido import Pedido
from models.pago import Pago
from models.menu import Menu
from models.plato import Plato

# Definir la carpeta donde se almacenarán los archivos JSON de forma ordenada
CARPETA_DATOS = "datos"

# Construir las rutas relativas usando os.path.join (similar a reporte.py)
RUTAS = {
    "clientes": os.path.join(CARPETA_DATOS, "clientes.json"),
    "menu": os.path.join(CARPETA_DATOS, "menu.json"),
    "pedidos": os.path.join(CARPETA_DATOS, "pedidos.json"),
    "pagos": os.path.join(CARPETA_DATOS, "pagos.json"),
    "platos": os.path.join(CARPETA_DATOS, "platos.json"),
}

def cargar_json(ruta, por_defecto):
    """
    Carga un archivo JSON de forma segura.
    Si el archivo no existe o está corrupto, devuelve el valor por_defecto.
    """
    if not os.path.exists(ruta):
        return por_defecto
    
    try:
        with open(ruta, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[Advertencia] El archivo '{ruta}' está corrupto o no se pudo leer. Se inicializará con datos vacíos. (Detalle: {e})")
        return por_defecto

def guardar_json(ruta, datos):
    """
    Guarda datos en un archivo JSON con formato legible.
    Asegura que la carpeta contenedora exista antes de escribir el archivo.
    """
    try:
        # Asegurarse de que la carpeta exista antes de guardar (como en reporte.py)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        
        with open(ruta, "w", encoding="utf-8") as file:
            json.dump(datos, file, indent=4, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"[Error] No se pudo guardar el archivo '{ruta}'. (Detalle: {e})")
        return False

"""
    Carga todos los datos desde los archivos JSON y arma los índices 
    o diccionarios necesarios usando los métodos desde_dict() de las clases.
"""
def cargar_todo():
    # Cargar datos crudos manejando errores con valores por defecto
    datos_clientes = cargar_json(RUTAS["clientes"], [])
    datos_menu = cargar_json(RUTAS["menu"], [])
    datos_pedidos = cargar_json(RUTAS["pedidos"], [])
    datos_pagos = cargar_json(RUTAS["pagos"], [])
    datos_platos = cargar_json(RUTAS["platos"], [])

    # Reconstruir los objetos   
    clientes = {}
    for c_dict in datos_clientes:
        cliente = Cliente.desde_dict(c_dict)
        clientes[cliente.get_id()] = cliente

    menu = Menu.desde_dict(datos_menu)

    pedidos = []
    for p_dict in datos_pedidos:
        pedido = Pedido.desde_dict(p_dict, clientes, menu)
        pedidos.append(pedido)

    pagos = []
    for pago_dict in datos_pagos:
        pago = Pago.desde_dict(pago_dict, clientes)
        pagos.append(pago)

    platos = []
    for plato_dict in datos_platos:
        plato = Plato.desde_dict(plato_dict)
        platos.append(plato)

    # Retornamos un contenedor o diccionario con todos los modelos listos para usar en memoria
    return {
        "clientes": clientes,
        "menu": menu,
        "pedidos": pedidos,
        "pagos": pagos,
        "platos": platos,
    }

"""
    Convierte los objetos en memoria a diccionarios mediante a_dict() y los
    guarda con guardar_json().

    Recibe un diccionario con estas claves (todas opcionales):
        "clientes": dict {id: Cliente}
        "pedidos":  lista de Pedido (cada pedido incluye sus pagos y detalles)
        "pagos":    lista de Pago      (solo si se lleva una lista aparte)
        "platos":   lista de Plato     (solo si se lleva una lista aparte)

    Las claves que no vengan se omiten, así no se sobrescriben archivos que
    el programa no manejó en esta sesión.

    NOTA: el menú (datos/menu.json) NO se guarda aquí. Es un archivo de
    configuración que el programa solo lee; Plato.a_dict() no incluye los
    alias, así que guardarlo los borraría y el parser dejaría de reconocer
    los platos.
"""
def guardar_todo(sistema_datos):
    if "clientes" in sistema_datos:
        lista_clientes = [c.a_dict() for c in sistema_datos["clientes"].values()]
        guardar_json(RUTAS["clientes"], lista_clientes)

    if "pedidos" in sistema_datos:
        lista_pedidos = [p.a_dict() for p in sistema_datos["pedidos"]]
        guardar_json(RUTAS["pedidos"], lista_pedidos)

    if "pagos" in sistema_datos:
        lista_pagos = [p.a_dict() for p in sistema_datos["pagos"]]
        guardar_json(RUTAS["pagos"], lista_pagos)

    if "platos" in sistema_datos:
        lista_platos = [p.a_dict() for p in sistema_datos["platos"]]
        guardar_json(RUTAS["platos"], lista_platos)