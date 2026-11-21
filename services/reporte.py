from models.detalle_pedido import DetallePedido
from datetime import date
import os
import sys
import subprocess

ESTADO_VENDIDO = "Entregado"


def generar_reporte_del_dia(sistema_datos, fecha=None):
    """Genera el reporte de ventas del día y devuelve su texto.

    Cuenta como venta cada pedido ENTREGADO con fecha de hoy (o la fecha dada).
    Incluye unidades y monto por plato, ordenados de más a menos vendido.
    """
    fecha_actual = fecha or date.today()
    # Nombre del plato -> [unidades, monto]
    ventas = {}
    pedidos = sistema_datos["pedidos"]
    unidades_totales = 0
    monto_total = 0.0
    entregados = 0
    cancelados = 0

    for pedido in pedidos:
        if pedido.get_fecha() != fecha_actual.isoformat():
            continue
        if pedido.get_estado().startswith("Cancelado"):
            cancelados += 1
            continue
        if pedido.get_estado() != ESTADO_VENDIDO:
            continue
        entregados += 1

        for detalle in pedido.get_detalles():
            cantidad = detalle.get_cantidad()
            subtotal = detalle.calcular_subtotal()
            nombre_plato = detalle.get_plato().get_name()

            unidades_totales += cantidad
            monto_total += subtotal
            fila = ventas.setdefault(nombre_plato, [0, 0.0])
            fila[0] += cantidad
            fila[1] += subtotal

    # Rankear los platos en orden descendente por los más vendidos (y por monto si empatan)
    ventas_ordenadas = sorted(ventas.items(), key=lambda item: (item[1][0], item[1][1]), reverse=True)

    lineas = [
        "=" * 60,
        f"REPORTE DE VENTAS DEL {fecha_actual.strftime('%d/%m/%Y')}",
        f"Pedidos entregados: {entregados}    Cancelados: {cancelados}",
        "=" * 60,
        f"{'#':<3} {'PLATO':<30} | {'UNIDADES':>8} | {'MONTO':>10}",
        "-" * 60,
    ]
    for puesto, (plato, (unidades, monto)) in enumerate(ventas_ordenadas, 1):
        lineas.append(f"{puesto:<3} {plato:<30} | {unidades:>8} | {monto:>10.2f}")
    if not ventas_ordenadas:
        lineas.append("(no hubo ventas entregadas hoy)")
    lineas += [
        "-" * 60,
        f"{'':<3} {'TOTAL':<30} | {unidades_totales:>8} | {monto_total:>10.2f}",
        "=" * 60,
    ]
    texto = "\n".join(lineas)

    # Definir la carpeta y asegurarse de que exista
    nombre_carpeta = "registros"
    os.makedirs(nombre_carpeta, exist_ok=True)
    
    nombre_archivo = f"reporte_del_dia_{fecha_actual}.txt"
    ruta_archivo = os.path.join(nombre_carpeta, nombre_archivo)

    with open(ruta_archivo, "w", encoding="utf-8") as file:
        file.write(texto + "\n")

    print(texto)
    print(f"\nGuardado en {ruta_archivo}")

    if not sys.stdout.isatty():   # en pruebas o redirigido: no abrir ventanas
        return texto
    try:
        if sys.platform == "win32":
            os.startfile(ruta_archivo)
        elif sys.platform == "darwin":  # macOS
            subprocess.run(["open", ruta_archivo])
        else:  # Linux
            subprocess.run(["xdg-open", ruta_archivo])
    except Exception as e:
        print(f"No se pudo abrir el archivo automáticamente: {e}")
    return texto