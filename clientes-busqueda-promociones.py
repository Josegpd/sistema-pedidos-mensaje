# Registro de un nuevo cliente en la base de datos
registro_cliente = {}

    # Condicion de la cedula del cliente. 
cedula = input('Ingrese su numero de cedula: ')
while len(cedula) < 6 or len(cedula) > 8 or cedula.isdigit() == False: 
      cedula = input('Por favor, ingrese un numero de cedula valido:')

    #Validacion del nombre: no puede estar vacio y debe contener solo letras.
nombre = input('Ingrese su nombre: ').strip()
while nombre == "" or any(caracter.isdigit() for caracter in nombre):
    nombre = input('Por favor, ingrese un nombre valido: ').strip()

    # Validacion del apellido: no puede estar vacio y debe contener solo letras.
apellido = input('Ingrese su apellido: ').strip()
while apellido == ""  or any(caracter.isdigit() for caracter in apellido):
    apellido = input('Por favor, ingrese un apellido valido: ').strip()
    
    # Validacion de la direccion: no puede estar vacio y debe conntener solo letras y numeros. 
direccion = input('Ingrese su direccion: '). strip()
while direccion == "":
    direccion = input('Por favor, ingrese una direccion valida:').strip()
    

    # Base donde se guardara los datos  del cliente.
registro_cliente[cedula] = {"Nombre": nombre,
                         "Apellido": apellido,
                         "Cedula": cedula, 
                         "Direccion": direccion,
                         "Historial_pedidos": []}


print('¡Ha registrado con exito al cliente!')

# Busqueda rapida por numero de cedula y listado de sus pedidos.

input_cedula = input('Ingrese su numero de cedula para buscar sus pedidos:')

if input_cedula in registro_cliente:
   cliente = registro_cliente[input_cedula]
   print("\n--- CLIENTE ENCONTRADO EN EL SISTEMA!---")
   print("Nombre del cliente:", cliente["Nombre"])
   print("Apellido del cliente:", cliente["Apellido"])
   print("Cedula del cliente:", cliente["Cedula"])
   print("Direccion del cliente:", cliente["Direccion"])
   print("Historial de pedidos:", cliente["Historial_pedidos"])
    
    # Lo de siempre con el historial de pedidos. 
   moda = 0 
   plato_frecuente = ""
 
   if len(cliente["Historial_pedidos"]) > 0:
      for plato in cliente["Historial_pedidos"]: 
          conteo = cliente["Historial_pedidos"].count(plato)
          if  conteo > moda:
              moda =  conteo
              plato_frecuente = plato
      print("El plato mas pedido por el cliente es: ", plato_frecuente)
   else:
      print('\n[AVISO]: el cliente con cedula', input_cedula, 'no  tiene pedidos registrados en el historial.')  
      print('Por favor, proceda a registrar un nuevo pedido para el cliente.')
    
    # Clasificacion nuevo/recurrente/inactivo y sugerencia de promocion

   if len(cliente["Historial_pedidos"])  == 0:
       print('El cliente es inactivo.')
       print('PROMOCION: envio gratis en su proximo pedido.')
   elif len(cliente['Historial_pedidos']) == 1:
       print('El cliente es nuevo.')
       print('PROMOCION: 10% de descuento en su pedido  actual.')
   elif len(cliente['Historial_pedidos']) > 10:
       print('El cliente es recurrente.')
       print('PROMO por  FIDELIDAD: Bebida gratis en su pedido actual.')
   else:
       print('El cliente es recurrente.')
       print('PROMOCION: 5% de descuento en su pedido actual.')

else: 
    print("\n[AVISO]: El cliente con cedula", input_cedula, "no esta registrado en la base de datos.")
    print("Por favor, proceda a registrar al nuevo cliente.")





