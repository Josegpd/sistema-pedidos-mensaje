# Registro de un nuevo cliente en la base de datos
registro_cliente = {}
    # Condicion de la cedula del cliente. 
cedula = input('Ingrese su numero de cedula: ')
while len(cedula) < 6 or len(cedula) > 8 or cedula.isdigit() == False: 
      cedula = input('Por favor, ingrese un numero de cedula valido:')


    # Base donde se guardara los datos  del cliente.
registro_cliente[cedula] = {"Nombre": input("Ingrese su nombre: "),
                    "Apellido": input("Ingrese su apellido: "),
                    "Cedula": cedula, 
                    "Direccion": input("Ingrese su direccion: "),
                    "Historial_pedidos": []}


print('¡Se ha registrado con exito! Por favor, realice su orden de compra y disfrute de nuestras promociones')


# Busqueda rapida por numero de cedula y listado de sus pedidos.

input_cedula = input('Ingrese su numero de cedula para buscar sus pedidos:')
if input_cedula in registro_cliente:
   cliente = registro_cliente[input_cedula]
   print("Bienvenido", cliente["Nombre"], "estos son sus pedidos:", cliente["Historial_pedidos"])
else: 
    print("No se encontraron pedidos para la cedula ingresada. Por favor, registre su orden de compra.")