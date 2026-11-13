import os
import json
from cliente import Cliente
from pedido import Pedido
from pago import Pago
from menu import Menu
from plato import Plato

def cargar_json(ruta, por_defecto):
    """
    Carga un archivo JSON de forma segura.
    Si el archivo no existe o esta corrupto, devuelve el valor por_defecto.
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
    """
    try:
        with open(ruta, "w", encoding="utf-8") as file:
            json.dump(datos, file, indent=4, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"[Error] No se pudo guardar el archivo '{ruta}'. (Detalle: {e})")
        return False

RUTAS = {
    "clientes": "clientes.json",
    "menu": "menu.json",
    "pedidos": "pedidos.json",
    "pagos": "pagos.json",
    "platos": "platos.json",
}

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
    Toma los diccionarios/listas en memoria, los convierte a diccionarios 
    mediante a_dict() y los guarda usando guardar_json().
"""
def guardar_todo(sistema_datos):
    # Convertir clientes de diccionario de objetos a lista de diccionarios
    lista_clientes = [cliente.a_dict() for cliente in sistema_datos["clientes"].values()]
    guardar_json(RUTAS["clientes"], lista_clientes)

    # Convertir menu
    menu = sistema_datos["menu"].a_dict()
    guardar_json(RUTAS["menu"], menu)

    # Convertir pedidos
    lista_pedidos = [pedido.a_dict() for pedido in sistema_datos["pedidos"]]
    guardar_json(RUTAS["pedidos"], lista_pedidos)

    # Convertir pagos
    lista_pagos = [pago.a_dict() for pago in sistema_datos["pagos"]]
    guardar_json(RUTAS["pagos"], lista_pagos)

    # Convertir platos
    lista_platos = [plato.a_dict() for plato in sistema_datos["platos"]]
    guardar_json(RUTAS["platos"], lista_platos)