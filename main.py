from parser_mensajes import Catalogo, analizar_mensaje, calcular_faltantes, leer_mensaje_pegado, resumen_para_operador
from models.pedido import Pedido
from models.plato import Plato
from models.mensaje_chat import Mensaje
from services.cola_pedidos import ColaPedidos
from services.gestor_pedidos import GestorPedidos
from services.clientes_service import ClientesService
from services.reporte import generar_reporte_del_dia
from utils.validaciones import (
    leer_opcion_menu, leer_entero, leer_float_positivo, leer_texto_no_vacio, confirmar_accion
)

RUTA_MENU = "./datos/menu.json" # ruta medida desde el directorio actual

def mostrar_menu_principal():
    print("\n" + "=" * 55)
    print("       SISTEMA DE GESTIÓN DE PEDIDOS POR CHAT ")
    print("=" * 55)
    print(" 1) Pegar y procesar nuevo mensaje de chat")
    print(" 2) Ver cola de pedidos pendientes (orden de llegada)")
    print(" 3) Cambiar estado de un pedido (Entregar / Cancelar)")
    print(" 4) Registrar pago a un pedido")
    print(" 5) Bandeja de pedidos incompletos")
    print(" 6) Consultar cliente / promociones")
    print(" 7) Mostrar catálogo de platos")
    print(" 8) Cerrar turno y generar reporte de ventas del día")
    print(" 0) Salir")
    print("=" * 55)

def opcion_procesar_mensaje(catalogo: Catalogo, gestor: GestorPedidos, clientes_srv: ClientesService):
    print("\n--- NUEVO MENSAJE DE CHAT ---")
    print("Pegue el mensaje del cliente y finalice escribiendo 'FIN' en una línea sola:")
    texto = leer_mensaje_pegado()
    if not texto:
        print("⚠️ No se ingresó ningún texto.")
        return

    # Parsear 
    datos_pedido = analizar_mensaje(texto, catalogo)

    # Verificar duplicados 
    es_dup, motivo_dup = gestor.es_duplicado(datos_pedido)
    if es_dup:
        print(f"\n ALERTA DE DUPLICADO: {motivo_dup}")
        if not confirmar_accion("¿Desea continuar y procesarlo de todos modos?"):
            print("Operación cancelada.")
            return

    # Validar / Autocompletar datos del cliente con Sonia
    c_info = datos_pedido["cliente"]
    cedula = c_info.get("cedula")

    if cedula:
        cliente_existente = clientes_srv.buscar_por_cedula(cedula)
        if cliente_existente:
            # Rellenar datos faltantes desde el registro
            if not c_info.get("nombres"):
                c_info["nombres"] = cliente_existente.get_names()
            if not c_info.get("apellidos"):
                c_info["apellidos"] = cliente_existente.get_last_names()
            if not c_info.get("direccion"):
                c_info["direccion"] = cliente_existente.get_address()
            # Recalcular faltantes 
            calcular_faltantes(datos_pedido)
        else:
            # Cliente nuevo
            if c_info.get("nombres") and c_info.get("direccion"):
                clientes_srv.registrar_o_actualizar(
                    cedula, c_info["nombres"], c_info.get("apellidos", ""), c_info["direccion"]
                )

    # 4. Manejo de 'Lo de siempre' 
    if datos_pedido.get("lo_de_siempre"):
        if cedula and cliente_existente:
            detalles_previos = clientes_srv.resolver_lo_de_siempre(cliente_existente)
            if detalles_previos:
                print("Resolviendo 'Lo de siempre' con el historial del cliente...")
                datos_pedido["platos"] = [
                    {"id_plato": d.get_plato().get_name(), "nombre": d.get_plato().get_name(),
                     "cantidad": d.get_cantidad(), "precio": d.get_precio_unitario(), "variacion": None}
                    for d in detalles_previos
                ]
                calcular_faltantes(datos_pedido)
            else:
                print("El cliente pidió 'Lo de siempre' pero no registra pedidos previos.")
        else:
            print("No se puede resolver 'Lo de siempre' sin cédula registrada.")

    # Resumen para operador del sistema
    print("\n" + resumen_para_operador(datos_pedido))

    if not datos_pedido.get("completo"):
        print("\nEl pedido tiene campos faltantes o no reconocidos.")
        print(f"Campos faltantes: {datos_pedido.get('faltantes')}")
        if confirmar_accion("¿Desea enviar este pedido a la bandeja de incompletos?"):
            gestor.registrar_incompleto(datos_pedido)
            print("Guardado en pedidos incompletos.")
        return

    # Instanciar modelos y encolar
    cliente_obj = clientes_srv.registrar_o_actualizar(
        c_info["cedula"], c_info["nombres"], c_info.get("apellidos", ""), c_info["direccion"]
    )
    msg_obj = Mensaje(id_msg=str(len(gestor.historial_general) + 1), texto=texto, fecha_recepcion=datos_pedido.get("fecha_recepcion") or "")

    nuevo_pedido = Pedido(
        hora=datos_pedido["hora"],
        fecha=datos_pedido["fecha"],
        total=datos_pedido["total_estimado"],
        cliente=cliente_obj,
        mensaje=msg_obj,
        estado="Pendiente"
    )

    for p in datos_pedido["platos"]:
        plato_obj = Plato(nombre=p["nombre"], precio=p["precio"])
        nuevo_pedido.agregar_detalle(plato_obj, p["cantidad"])

    pos = gestor.registrar_pedido_completo(nuevo_pedido)
    print(f"\nPedido registrado con éxito! ID: {nuevo_pedido.get_id()} (Turno en cola: {pos + 1})")

    # 7. Sugerencia de Promoción de Sonia
    promo = clientes_srv.obtener_promocion(cliente_obj)
    print(f"Promoción sugerida para el cliente: {promo}")

def opcion_ver_cola(cola: ColaPedidos):
    print("\n--- COLA DE PEDIDOS PENDIENTES (Orden Cronológico) ---")
    pendientes = cola.get_all()
    if not pendientes:
        print("No hay pedidos pendientes en cola.")
        return

    for i, p in enumerate(pendientes, 1):
        cli = p.get_cliente()
        print(f"#{i} | ID: {p.get_id()} | Hora: {p.get_hora()} | Cliente: {cli.get_names()} {cli.get_last_names()} | Total: ${p.calcular_monto_total():.2f} | Saldo Pendiente: ${p.calcular_saldo_restante():.2f}")

def opcion_cambiar_estado(gestor: GestorPedidos):
    print("\n--- CAMBIO DE ESTADO DE PEDIDO ---")
    id_ped = leer_texto_no_vacio("Ingrese el ID del pedido (ej. #12345): ")
    pedido = gestor.cola.buscar_por_id(id_ped)

    if not pedido:
        print(f"El pedido {id_ped} no se encuentra en la cola de pendientes.")
        return

    print(f"Pedido seleccionado: {pedido.get_id()} - Cliente: {pedido.get_cliente().get_names()}")
    print("1) Marcar como ENTREGADO")
    print("2) Marcar como CANCELADO (requiere motivo)")
    sub_op = leer_opcion_menu("Seleccione acción: ", ["1", "2"])

    if sub_op == "1":
        gestor.marcar_como_entregado(id_ped)
        print(f"Pedido {id_ped} entregado exitosamente. Retirado de la cola activa.")
    else:
        motivo = leer_texto_no_vacio("Ingrese el motivo de la cancelación: ")
        gestor.marcar_como_cancelado(id_ped, motivo)
        print(f"Pedido {id_ped} cancelado por: '{motivo}'. Retirado de la cola activa.")

def opcion_registrar_pago(gestor: GestorPedidos):
    print("\n--- REGISTRO DE PAGOS ---")
    id_ped = leer_texto_no_vacio("Ingrese el ID del pedido a abonar: ")
    pedido = gestor.buscar_en_historial(id_ped)

    if not pedido:
        print(f"Pedido {id_ped} no encontrado.")
        return

    saldo = pedido.calcular_saldo_restante()
    print(f"Total del pedido: ${pedido.calcular_monto_total():.2f} | Saldo restante: ${saldo:.2f}")

    if saldo <= 0:
        print("Este pedido ya está totalmente pagado.")
        return

    print("Métodos: Efectivo, Pago Móvil, Punto, Transferencia, Zelle")
    metodo = leer_texto_no_vacio("Método de pago: ")
    referencia = leer_texto_no_vacio("Referencia / Comprobante: ")
    monto = leer_float_positivo(f"Monto a pagar (máx ${saldo:.2f}): ")

    ok, nuevo_saldo, msg = gestor.registrar_pago(pedido, metodo, referencia, monto)
    if ok:
        print(f"{msg} Saldo restante actual: ${nuevo_saldo:.2f}")
    else:
        print(f"Error: {msg}")

def opcion_pedidos_incompletos(gestor: GestorPedidos, catalogo: Catalogo, clientes_srv: ClientesService):
    incompletos = gestor.obtener_incompletos()
    if not incompletos:
        print("\nNo hay pedidos incompletos pendientes de revisión.")
        return

    print(f"\n--- BANDEJA DE PEDIDOS INCOMPLETOS ({len(incompletos)}) ---")
    for idx, inc in enumerate(incompletos):
        faltan = ", ".join(inc.get("faltantes", []))
        print(f"[{idx + 1}] Texto: {inc.get('texto_original')[:40]}... | Faltan: {faltan}")

    sel = leer_entero("Seleccione el número de pedido a completar (0 para volver): ", 0, len(incompletos))
    if sel == 0:
        return

    p_incompleto = incompletos[sel - 1]
    print("\nCompletando datos faltantes:")
    for campo in list(p_incompleto.get("faltantes", [])):
        valor = leer_texto_no_vacio(f"Ingrese '{campo}' faltante: ")
        if campo in ("cedula", "nombres", "apellidos", "direccion"):
            p_incompleto["cliente"][campo] = valor
        elif campo == "hora":
            p_incompleto["hora"] = valor
        elif campo == "fecha":
            p_incompleto["fecha"] = valor

    calcular_faltantes(p_incompleto)
    if p_incompleto.get("completo"):
        print("Todos los datos han sido completados.")
        incompletos.pop(sel - 1)
        # Proceder a encolar
        c_info = p_incompleto["cliente"]
        cli = clientes_srv.registrar_o_actualizar(c_info["cedula"], c_info["nombres"], c_info.get("apellidos", ""), c_info["direccion"])
        msg = Mensaje(id_msg=str(len(gestor.historial_general) + 1), texto=p_incompleto["texto_original"], fecha_recepcion="")
        nuevo = Pedido(hora=p_incompleto["hora"], fecha=p_incompleto["fecha"], total=p_incompleto["total_estimado"], cliente=cli, mensaje=msg)
        for pl in p_incompleto["platos"]:
            nuevo.agregar_detalle(Plato(pl["nombre"], pl["precio"]), pl["cantidad"])
        gestor.registrar_pedido_completo(nuevo)
        print(f"Pedido encolado exitosamente con ID: {nuevo.get_id()}")
    else:
        print(f"Aún faltan campos: {p_incompleto.get('faltantes')}")

def main():
    try:
        catalogo = Catalogo.desde_archivo(RUTA_MENU)
    except Exception as e:
        print(f"Error al cargar menú ({RUTA_MENU}): {e}")
        return

    cola = ColaPedidos()
    gestor = GestorPedidos(cola)
    clientes_srv = ClientesService()

    while True:
        mostrar_menu_principal()
        opcion = leer_opcion_menu("Seleccione una opción: ", ["1", "2", "3", "4", "5", "6", "7", "8", "0"])

        if opcion == "1":
            opcion_procesar_mensaje(catalogo, gestor, clientes_srv)
        elif opcion == "2":
            opcion_ver_cola(cola)
        elif opcion == "3":
            opcion_cambiar_estado(gestor)
        elif opcion == "4":
            opcion_registrar_pago(gestor)
        elif opcion == "5":
            opcion_pedidos_incompletos(gestor, catalogo, clientes_srv)
        elif opcion == "6":
            ced = leer_texto_no_vacio("Ingrese cédula del cliente: ")
            c = clientes_srv.buscar_por_cedula(ced)
            if c:
                print(f"Cliente: {c.get_names()} {c.get_last_names()} | Dir: {c.get_address()}")
                print(f"Historial: {len(c.get_order_history())} pedidos.")
                print(f"Sugerencia: {clientes_srv.obtener_promocion(c)}")
            else:
                print("Cliente no encontrado en el sistema.")
        elif opcion == "7":
            catalogo.mostrar_menu() if hasattr(catalogo, "mostrar_menu") else print(catalogo)
        elif opcion == "8":
            print("\nGenerando reporte del día...")
            datos_sistema = {"pedidos": gestor.historial_general}
            try:
                generar_reporte_del_dia(datos_sistema)
                print("Reporte generado exitosamente.")
            except Exception as err:
                print(f"Error generando reporte: {err}")
        elif opcion == "0":
            if confirmar_accion("¿Seguro que desea salir del sistema?"):
                print("\nCerrando sistema. ¡Buen turno!")
                break

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nOperación interrumpida. Saliendo...")

    