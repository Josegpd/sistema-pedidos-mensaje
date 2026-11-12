# Registro de un nuevo cliente en la base de datos

# Condicion de la cedula del cliente. 
cedula = input('Ingrese su numero de cedula: ')
while len(cedula) < 6 or len(cedula) > 8: 
      cedula = input('El numero de cedula debe tener entre 6 y 8 digitos. Por favor, intente de nuevo:')


# Base donde se guardara los datos  del cliente.
registro_cliente = {"Nombre": input("Ingrese sus nombres: "),
                    "Apellido": input("Ingrese sus  apellidos: "),
                    "Cedula": cedula, 
                    "Direccion": input("Ingrese su direccion: "),
                    "Historial_pedidos": []}


print('¡Se ha registrado con exito! Por favor, realice su orden de compra y disfrute de nuestras promociones')