import os
from datetime import date

from parser_mensajes import Catalogo, analizar_mensaje, calcular_faltantes, confirmar_pedido, leer_mensaje_pegado
from models.pedido import Pedido
from models.plato import Plato
from models.mensaje_chat import Mensaje
from services.cola_pedidos import ColaPedidos
from services.gestor_pedidos import GestorPedidos
from services.clientes_service import ClientesService
from services.directorio_clientes import (
    GestorClientes, mostrar_directorio_clientes, pedir_y_consultar_historial
)
from services.persistencia import cargar_todo, guardar_todo
from services.reporte import generar_reporte_del_dia
from utils import estilo as e
from utils.consola import limpiar_pantalla, pausar
from utils.validaciones import (
    leer_opcion_menu, leer_entero, leer_float_positivo, leer_texto_no_vacio, confirmar_accion
)

RUTA_MENU = "./datos/menu.json" # ruta medida desde el directorio actual
RUTA_COMANDAS = os.path.join("registros", "comandas.txt")

# (tecla, texto) del menú principal
OPCIONES_MENU = [
    ("1", "Pegar y procesar un mensaje de chat"),
    ("2", "Ver cola de pedidos pendientes"),
    ("3", "Comandas para cocina"),
    ("4", "Cambiar estado de un pedido (entregar / cancelar)"),
    ("5", "Registrar pago a un pedido"),
    ("6", "Bandeja de pedidos incompletos"),
    ("7", "Clientes: directorio, historial y promociones"),
    ("8", "Mostrar catálogo de platos"),
    ("9", "Cerrar turno y generar reporte del día"),
    ("0", "Salir"),
]


def mostrar_menu_principal(cola: ColaPedidos, gestor: GestorPedidos):
    print()
    print(e.titulo("Sistema de pedidos por chat"))
    estado = f"{len(cola)} en cola"
    if gestor.pedidos_incompletos:
        estado += f" · {len(gestor.pedidos_incompletos)} en la bandeja"
    print(e.tenue(f"  {date.today().strftime('%d/%m/%Y')} · {estado}"))
    print()
    for tecla, texto in OPCIONES_MENU:
        print(e.opcion(tecla, e.tenue(texto) if tecla == "0" else texto))
    print(e.cierre())


def encabezado(texto: str):
    print()
    print(e.titulo(texto))


def mostrar_catalogo(catalogo: Catalogo):
    encabezado("Catálogo de platos")
    for plato in catalogo.platos.values():
        izquierda = f"  {e.tenue(plato['id'])}  {plato['nombre']}"
        precio = f"{plato['precio']:.2f}"
        print(izquierda + " " * max(1, e.ANCHO - len(plato['id']) - len(plato['nombre']) - len(precio) - 4) + precio)
    print(e.cierre())


def leer_id_pedido(prompt: str) -> str:
    """Acepta el ID con o sin '#': '12' y '#12' son el mismo pedido."""
    id_ped = leer_texto_no_vacio(e.pregunta(prompt)).strip()
    return id_ped if id_ped.startswith("#") else "#" + id_ped


def fecha_corta(fecha_iso: str) -> str:
    try:
        return date.fromisoformat(fecha_iso).strftime("%d/%m")
    except (TypeError, ValueError):
        return fecha_iso or "-"


def mostrar_ticket(pedido: Pedido, posicion: int, promo: str):
    """Lo único que queda en pantalla después de registrar un pedido."""
    cliente = pedido.get_cliente()
    print()
    print(e.titulo(f"Pedido {pedido.get_id()} registrado"))
    print(e.campo("Cliente", f"{cliente.get_names()} {cliente.get_last_names() or ''}".strip()))
    print(e.campo("Cédula", cliente.get_id()))
    print(e.campo("Entrega", f"{fecha_corta(pedido.get_fecha())} · {pedido.get_hora()}"))
    print(e.campo("Dirección", pedido.get_direccion()))
    print()
    for detalle in pedido.get_detalles():
        variacion = e.tenue(f"  ({detalle.get_variacion()})") if detalle.get_variacion() else ""
        print(f"   {detalle.get_cantidad():>2} × {detalle.get_plato().get_name()}{variacion}")
    for extra in pedido.get_extras():
        print(e.magenta(f"    +  {extra} (extra, fuera del menú)"))
    print("  " + e.negrita(f"Total: {pedido.calcular_monto_total():.2f}"))
    print()
    print("  " + e.ok(f"Turno en la cola: {posicion + 1}"))
    print("  " + e.info(f"Promoción: {promo}"))
    print(e.cierre())


def crear_y_encolar(datos_pedido: dict, gestor: GestorPedidos, clientes_srv: ClientesService) -> Pedido:
    """Convierte un pedido ya confirmado (dict del parser) en objetos y lo pone en la cola."""
    c_info = datos_pedido["cliente"]
    cliente_obj = clientes_srv.registrar_o_actualizar(
        c_info["cedula"], c_info["nombres"], c_info.get("apellidos") or "", c_info["direccion"]
    )
    # La promoción se calcula con el historial ANTES de sumar este pedido
    promo = clientes_srv.obtener_promocion(cliente_obj)

    msg_obj = Mensaje(id_msg=str(len(gestor.historial) + 1), texto=datos_pedido.get("texto_original") or "",
                      fecha_recepcion=datos_pedido.get("fecha_recepcion") or "")
    nuevo_pedido = Pedido(
        hora=datos_pedido["hora"],
        fecha=datos_pedido["fecha"],
        total=datos_pedido["total_estimado"],
        cliente=cliente_obj,
        mensaje=msg_obj,
        estado="Pendiente",
        direccion=c_info["direccion"]
    )
    for p in datos_pedido["platos"]:
        nuevo_pedido.agregar_detalle(Plato(p["id_plato"], p["nombre"], p["precio"]), p["cantidad"],
                                     p.get("variacion") or "")
    for extra in datos_pedido.get("extras", []):
        nuevo_pedido.agregar_extra(extra["texto"])

    pos = gestor.registrar_pedido_completo(nuevo_pedido)
    # Pantalla limpia: solo el comprobante del pedido recién registrado
    limpiar_pantalla()
    mostrar_ticket(nuevo_pedido, pos, promo)
    return nuevo_pedido


def opcion_procesar_mensaje(catalogo: Catalogo, gestor: GestorPedidos, clientes_srv: ClientesService):
    encabezado("Nuevo mensaje de chat")
    texto = leer_mensaje_pegado()
    if not texto:
        print("  " + e.aviso("No se ingresó ningún texto."))
        return

    # Parsear
    datos_pedido = analizar_mensaje(texto, catalogo)

    # Verificar duplicados
    es_dup, motivo_dup = gestor.es_duplicado(datos_pedido)
    if es_dup:
        print("\n  " + e.aviso(f"Posible duplicado: {motivo_dup}"))
        if not confirmar_accion(e.pregunta("¿Desea procesarlo de todos modos?")):
            print("  " + e.tenue("Operación cancelada."))
            return

    # Completar con los datos del cliente registrado
    c_info = datos_pedido["cliente"]
    cedula = c_info.get("cedula")
    cliente_existente = None

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
            calcular_faltantes(datos_pedido)

    # "Lo de siempre": los platos de su último pedido no cancelado
    if datos_pedido.get("lo_de_siempre"):
        detalles_previos = clientes_srv.resolver_lo_de_siempre(cliente_existente) if cliente_existente else None
        if detalles_previos:
            datos_pedido["platos"] += [
                {"id_plato": d.get_plato().get_id(), "nombre": d.get_plato().get_name(),
                 "cantidad": d.get_cantidad(), "precio": d.get_precio_unitario(), "variacion": d.get_variacion(),
                 "texto": "lo de siempre"}
                for d in detalles_previos
            ]
            datos_pedido["advertencias"].append("\"Lo de siempre\": se copiaron los platos de su último pedido.")
        else:
            datos_pedido["advertencias"].append("Pidió \"lo de siempre\" pero no tiene pedidos previos: pregúntele los platos.")
        datos_pedido["lo_de_siempre"] = False
        calcular_faltantes(datos_pedido)

    # Completar lo que falte, mostrar el resumen y dejar corregir antes de aceptar
    if confirmar_pedido(datos_pedido, catalogo):
        crear_y_encolar(datos_pedido, gestor, clientes_srv)
    elif not datos_pedido.get("completo") and confirmar_accion(
            e.pregunta("¿Guardar el pedido en la bandeja de incompletos para terminarlo después?")):
        gestor.registrar_incompleto(datos_pedido)
        print("  " + e.ok("Guardado en la bandeja de incompletos."))


def opcion_ver_cola(cola: ColaPedidos):
    encabezado("Cola de pedidos pendientes")
    pendientes = cola.get_all()
    if not pendientes:
        print("  " + e.tenue("No hay pedidos pendientes."))
        print(e.cierre())
        return

    for i, p in enumerate(pendientes, 1):
        cli = p.get_cliente()
        saldo = max(0.0, p.calcular_saldo_restante())
        estado_pago = e.verde("pagado") if saldo <= 0 else e.amarillo(f"debe {saldo:.2f}")
        print(f"  {e.negrita(str(i) + '.')} {e.cian(p.get_id())}  {fecha_corta(p.get_fecha())} {p.get_hora()}  "
              f"{cli.get_names()} {cli.get_last_names() or ''}".rstrip())
        print(e.tenue(f"      {p.get_direccion() or cli.get_address()}")
              + f"  ·  total {p.calcular_monto_total():.2f}  ·  " + estado_pago)
    print(e.cierre())


def texto_comandas(pendientes: list[Pedido]) -> str:
    """Comandas en texto plano (para el archivo que puede abrir o imprimir la cocina)."""
    lineas = [f"COMANDAS PENDIENTES ({len(pendientes)}) - {date.today().strftime('%d/%m/%Y')}", "=" * 50]
    for p in pendientes:
        lineas.append(f"{p.get_id()}  |  {fecha_corta(p.get_fecha())} {p.get_hora()}  |  {p.get_cliente().get_names()}")
        for d in p.get_detalles():
            variacion = f"  -> {d.get_variacion()}" if d.get_variacion() else ""
            lineas.append(f"   {d.get_cantidad():>2} x {d.get_plato().get_name()}{variacion}")
        for extra in p.get_extras():
            lineas.append(f"    + EXTRA (consultar): {extra}")
        lineas.append(f"   Entregar en: {p.get_direccion()}")
        lineas.append("-" * 50)
    return "\n".join(lineas)


def opcion_comandas(cola: ColaPedidos):
    """Vista para la cocina: qué preparar, en qué orden y con qué variaciones."""
    encabezado("Comandas para cocina")
    pendientes = cola.get_all()
    if not pendientes:
        print("  " + e.tenue("No hay nada que preparar."))
        print(e.cierre())
        return

    for p in pendientes:
        print(f"  {e.negrita(e.cian(p.get_id()))}  {e.negrita(fecha_corta(p.get_fecha()) + ' ' + p.get_hora())}"
              f"  {e.tenue(p.get_cliente().get_names())}")
        for d in p.get_detalles():
            variacion = "  " + e.amarillo(f"→ {d.get_variacion()}") if d.get_variacion() else ""
            print(f"     {e.negrita(str(d.get_cantidad()) + ' ×')} {d.get_plato().get_name()}{variacion}")
        for extra in p.get_extras():
            print(e.magenta(f"     + extra (consultar): {extra}"))
        print(e.tenue(f"     Entregar en: {p.get_direccion()}"))
        print(e.separador())

    os.makedirs(os.path.dirname(RUTA_COMANDAS), exist_ok=True)
    with open(RUTA_COMANDAS, "w", encoding="utf-8") as archivo:
        archivo.write(texto_comandas(pendientes) + "\n")
    print("  " + e.info(f"También se guardaron en {RUTA_COMANDAS} para abrir o imprimir en la cocina."))
    print(e.cierre())


def opcion_cambiar_estado(gestor: GestorPedidos):
    encabezado("Cambiar estado de un pedido")
    id_ped = leer_id_pedido("ID del pedido (ej. #12):")
    pedido = gestor.cola.get_by_id(id_ped)

    if not pedido:
        print("  " + e.error(f"El pedido {id_ped} no está en la cola de pendientes."))
        return

    print(f"  Pedido {e.cian(pedido.get_id())} · {pedido.get_cliente().get_names()}")
    print(e.opcion(1, e.verde("Marcar como ENTREGADO")))
    print(e.opcion(2, e.rojo("Marcar como CANCELADO") + e.tenue(" (pide motivo)")))
    sub_op = leer_opcion_menu(e.pregunta("Opción:"), ["1", "2"])

    if sub_op == "1":
        gestor.marcar_como_entregado(id_ped)
        print("  " + e.ok(f"Pedido {id_ped} entregado. Salió de la cola."))
    else:
        motivo = leer_texto_no_vacio(e.pregunta("Motivo de la cancelación:"))
        gestor.marcar_como_cancelado(id_ped, motivo)
        print("  " + e.ok(f"Pedido {id_ped} cancelado ({motivo}). Salió de la cola."))


def opcion_registrar_pago(gestor: GestorPedidos):
    encabezado("Registrar pago")
    id_ped = leer_id_pedido("ID del pedido:")
    pedido = gestor.buscar_en_historial(id_ped)

    if not pedido:
        print("  " + e.error(f"Pedido {id_ped} no encontrado."))
        return

    if pedido.get_estado().startswith("Cancelado"):
        print("  " + e.error(f"El pedido {id_ped} está cancelado ({pedido.get_estado()}); no se le pueden registrar pagos."))
        return

    saldo = pedido.calcular_saldo_restante()
    print(e.campo("Total", f"{pedido.calcular_monto_total():.2f}"))
    print(e.campo("Saldo", f"{saldo:.2f}"))

    if saldo <= 0:
        print("  " + e.ok("Este pedido ya está totalmente pagado."))
        return

    print(e.tenue("  Métodos: Efectivo, Pago Móvil, Punto, Transferencia, Zelle"))
    metodo = leer_texto_no_vacio(e.pregunta("Método de pago:"))
    referencia = leer_texto_no_vacio(e.pregunta("Referencia / comprobante:"))
    monto = leer_float_positivo(e.pregunta(f"Monto (máx {saldo:.2f}):"))

    ok, nuevo_saldo, msg = gestor.registro_de_pagos(pedido, metodo, referencia, monto)
    if ok:
        print("  " + e.ok(f"{msg}. Saldo restante: {nuevo_saldo:.2f}"))
    else:
        print("  " + e.error(msg))


def opcion_pedidos_incompletos(gestor: GestorPedidos, catalogo: Catalogo, clientes_srv: ClientesService):
    incompletos = gestor.obtener_incompletos()
    encabezado(f"Bandeja de incompletos ({len(incompletos)})")
    if not incompletos:
        print("  " + e.tenue("No hay pedidos incompletos."))
        print(e.cierre())
        return

    for idx, inc in enumerate(incompletos, 1):
        faltan = ", ".join(inc.get("faltantes", [])) or "platos ambiguos"
        texto = " ".join((inc.get("texto_original") or "").split())[:40]
        print(e.opcion(idx, f"{texto}…  " + e.rojo(f"falta: {faltan}")))
    print(e.opcion(0, e.tenue("Volver")))
    print(e.cierre())

    sel = leer_entero(e.pregunta("¿Cuál completar?"), 0, len(incompletos))
    if sel == 0:
        return

    p_incompleto = incompletos[sel - 1]
    # Pregunta lo que falta (validando cada dato), muestra el resumen y deja corregir
    if confirmar_pedido(p_incompleto, catalogo):
        incompletos.pop(sel - 1)
        crear_y_encolar(p_incompleto, gestor, clientes_srv)
    else:
        print("  " + e.tenue("El pedido sigue en la bandeja de incompletos."))


def opcion_consultar_cliente(clientes_srv: ClientesService):
    ced = leer_texto_no_vacio(e.pregunta("Cédula del cliente:"))
    c = clientes_srv.buscar_por_cedula(ced)
    if c:
        print(e.campo("Cliente", f"{c.get_names()} {c.get_last_names() or ''}".strip()))
        print(e.campo("Dirección", c.get_address()))
        print(e.campo("Pedidos", str(len(c.get_order_history()))))
        print("  " + e.info(clientes_srv.obtener_promocion(c)))
    else:
        print("  " + e.error("Cliente no encontrado en el sistema."))


def opcion_clientes(clientes_srv: ClientesService):
    directorio = GestorClientes(clientes_srv)
    encabezado("Clientes")
    print(e.opcion(1, "Ver directorio de clientes registrados"))
    print(e.opcion(2, "Historial de compras (por cédula o nombre)"))
    print(e.opcion(3, "Consultar cliente y promoción (por cédula)"))
    print(e.opcion(0, e.tenue("Volver")))
    print(e.cierre())
    sub_op = leer_opcion_menu(e.pregunta("Opción:"), ["1", "2", "3", "0"])

    if sub_op == "1":
        mostrar_directorio_clientes(directorio)
    elif sub_op == "2":
        pedir_y_consultar_historial(directorio)
    elif sub_op == "3":
        opcion_consultar_cliente(clientes_srv)


def main():
    try:
        catalogo = Catalogo.desde_archivo(RUTA_MENU)
    except Exception as err:
        print(e.error(f"Error al cargar menú ({RUTA_MENU}): {err}"))
        return

    # Recuperar lo guardado en sesiones anteriores
    datos = cargar_todo()
    cola = ColaPedidos()
    gestor = GestorPedidos(cola)
    gestor.historial = datos["pedidos"]
    gestor.pedidos_incompletos = datos["incompletos"]
    for pedido in gestor.historial:
        if pedido.get_estado() == "Pendiente":
            cola.enqueue(pedido)
    clientes_srv = ClientesService(datos["clientes"])
    if gestor.historial or clientes_srv.clientes or gestor.pedidos_incompletos:
        print("  " + e.ok(f"Datos cargados: {len(clientes_srv.clientes)} clientes, {len(gestor.historial)} pedidos "
                          f"({len(cola)} en cola, {len(gestor.pedidos_incompletos)} en la bandeja)."))
        pausar()

    def guardar():
        guardar_todo({"clientes": clientes_srv.clientes, "pedidos": gestor.historial,
                      "incompletos": gestor.pedidos_incompletos})

    try:
        bucle_principal(catalogo, cola, gestor, clientes_srv, guardar)
    except (KeyboardInterrupt, EOFError):
        print("\n\n" + e.aviso("Operación interrumpida. Guardando y saliendo..."))
    finally:
        guardar()


def bucle_principal(catalogo, cola, gestor, clientes_srv, guardar):
    teclas = [tecla for tecla, _ in OPCIONES_MENU]
    while True:
        limpiar_pantalla()
        mostrar_menu_principal(cola, gestor)
        opcion = leer_opcion_menu(e.pregunta("Opción:"), teclas)
        limpiar_pantalla()

        if opcion == "1":
            opcion_procesar_mensaje(catalogo, gestor, clientes_srv)
        elif opcion == "2":
            opcion_ver_cola(cola)
        elif opcion == "3":
            opcion_comandas(cola)
        elif opcion == "4":
            opcion_cambiar_estado(gestor)
        elif opcion == "5":
            opcion_registrar_pago(gestor)
        elif opcion == "6":
            opcion_pedidos_incompletos(gestor, catalogo, clientes_srv)
        elif opcion == "7":
            opcion_clientes(clientes_srv)
        elif opcion == "8":
            mostrar_catalogo(catalogo)
        elif opcion == "9":
            encabezado("Reporte del día")
            try:
                generar_reporte_del_dia({"pedidos": gestor.historial})
            except Exception as err:
                print("  " + e.error(f"Error generando reporte: {err}"))
        elif opcion == "0":
            if confirmar_accion(e.pregunta("¿Seguro que desea salir del sistema?")):
                print("\n" + e.tenue("Cerrando sistema. ¡Buen turno!"))
                break
            continue  # no se canceló nada que leer: se vuelve directo al menú

        # Guardar después de cada operación: si se va la luz no se pierde el turno
        guardar()
        # Deja el resultado a la vista hasta que el operador lo lea; luego se
        # borra y el menú vuelve a mostrarse solo.
        pausar()


if __name__ == "__main__":
    # Las rutas (datos/, registros/) son relativas a la carpeta del proyecto
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nOperación interrumpida. Saliendo...")
