from clases.detalle_pedido import DetallePedido
from datetime import date
import os
import sys
import subprocess

def generar_reporte_del_dia(sistema_datos):
    ventas = {}
    # Obtener la lista de pedidos
    pedidos = sistema_datos["pedidos"]
    ventas_totales = 0

    for pedido in pedidos:
        if pedido.get_estado() in ("Pagado", "pagado"):
            # Tomar la lista de pedidos
            detalles_pedido = pedido.get_detalles()
            
            for detalle in detalles_pedido:
                cantidad = detalle.get_cantidad()
                nombre_plato = detalle.get_plato().get_name()
                
                # Sumar al total general
                ventas_totales += cantidad

                if nombre_plato in ventas:
                    # Contar una venta mas del plato
                    ventas[nombre_plato] += + cantidad
                else:
                    # Primera venta del plato
                    ventas[nombre_plato] = cantidad

    # Obtener la fecha del dia actual
    fecha_actual = date.today()

    # Definir la carpeta y asegurarse de que exista
    nombre_carpeta = "registros"
    os.makedirs(nombre_carpeta, exist_ok=True)
    
    nombre_archivo = f"reporte_del_dia_{fecha_actual}.txt"
    ruta_archivo = os.path.join(nombre_carpeta, nombre_archivo)

    with open(ruta_archivo, "w", encoding="utf-8") as file:
        # Rankear los platos en orden descendente por los mas vendidos
        ventas_ordenadas = sorted(ventas.items(), key=lambda item: item[1], reverse=True)

        # Encabezado de la tabla
        file.write("=" * 50 + "\n")
        file.write(f"{'NOMBRE DEL PLATO':<35} | {'VENTAS'}\n")
        file.write("-" * 50 + "\n")
        
        # Filas de platos vendidos
        for plato, venta in ventas_ordenadas:
            file.write(f"{plato:<35} | {venta}\n")
            
        # Pie de la tabla y totales
        file.write("-" * 50 + "\n")
        file.write(f"{'VENTAS TOTALES':<35} | {ventas_totales}\n")
        file.write("=" * 50 + "\n")

    try:
        if sys.platform == "win32":
            os.startfile(ruta_archivo)
        elif sys.platform == "darwin":  # macOS
            subprocess.run(["open", ruta_archivo])
        else:  # Linux
            subprocess.run(["xdg-open", ruta_archivo])
    except Exception as e:
        print(f"No se pudo abrir el archivo automáticamente: {e}")