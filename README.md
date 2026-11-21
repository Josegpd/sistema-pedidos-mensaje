# Sistema de pedidos por chat

Programa de terminal en Python para gestionar los pedidos que un restaurante recibe
por chat (WhatsApp). El operador pega el mensaje del cliente y el programa lo
interpreta, pregunta lo que falte, muestra un resumen para confirmar, ordena los
pedidos por hora de entrega y lleva pagos, estados, clientes y el reporte del día.

Sin interfaz gráfica ni base de datos: todo corre en la terminal y los datos se
guardan en archivos JSON.

**Requisitos:** Python 3.10 o superior. Solo usa la biblioteca estándar, no hay que instalar nada.

## Cómo usarlo

Desde la carpeta del proyecto:

```bash
python main.py
```

Al abrirse carga los clientes, pedidos y pedidos a medias guardados en sesiones anteriores.

| Opción | Qué hace |
|---|---|
| **1. Procesar mensaje** | Se pega el mensaje del chat y se termina con `FIN`. El programa completa los datos si el cliente ya está registrado, resuelve "lo de siempre", pregunta lo que falte, muestra el resumen para confirmar o corregir y lo pone en la cola. Al final queda el comprobante con la promoción sugerida |
| **2. Ver cola** | Pedidos pendientes ordenados por fecha y hora de entrega, con dirección y saldo |
| **3. Comandas para cocina** | Qué preparar y en qué orden, con variaciones ("sin cebolla") y extras. También se guarda en `registros/comandas.txt` para abrir o imprimir |
| **4. Cambiar estado** | Marcar un pedido como entregado, o cancelado con motivo. Sale de la cola y queda en el historial |
| **5. Registrar pago** | Método, referencia y monto. No permite pagar de más ni pagar un pedido cancelado |
| **6. Bandeja de incompletos** | Pedidos que quedaron a medias; se terminan con el mismo flujo de la opción 1 |
| **7. Clientes** | Directorio, historial de compras (por cédula o nombre), clasificación y promoción |
| **8. Catálogo** | Menú con precios |
| **9. Reporte del día** | Pedidos entregados hoy: ranking de platos con unidades y monto, total cobrado y por cobrar. Se guarda en `registros/` |
| **0. Salir** | Guarda y cierra |

El programa también guarda después de cada operación y al cerrarse con Ctrl+C.

## Recorrido de un pedido

1. El cliente escribe por WhatsApp y el operador copia y pega el mensaje.
2. Se extraen cédula, nombre, dirección, fecha, hora y platos.
3. Si la cédula ya está registrada, se completan nombre y dirección desde el registro.
4. Si falta algo o está mal escrito, el programa lo pregunta hasta que el dato sea válido
   y sugiere las frases para pedírselo al cliente.
5. Se muestra el resumen: **Confirmar**, **Corregir un dato** o **Cancelar**.
6. Al confirmar, el pedido entra a la cola como **Pendiente** en su posición según fecha y hora.
7. Luego pasa a **Entregado** o **Cancelado**; los pagos se registran aparte.

## Formato del mensaje

El formato recomendado es:

```
Cédula: V-12.345.678
Nombre: Juan Pérez
Dirección: Av. Bolívar, edificio Sol, piso 3
Fecha: 15/11/2026
Hora: 1:30 pm
Pedido:
- 2 hamburguesas (sin cebolla)
- 1 refresco
- 3 empanadas de queso
```

Pero también entiende:

- **Otras etiquetas**: `CI`, `C.I.`, `Nombre completo`, `Cliente`, `Dir`, `Vivo en`, `Para`, `Platos`, `Orden`…
- **Texto libre**: `Hola, soy Pedro Ramírez, CI 15222333, quiero 2 empanadas de carne y una coca cola para hoy a la 1:30 pm`.
- **Chat copiado de WhatsApp** con sus encabezados (`[12/11/26, 11:05] Maria: ...`).
- **Fechas**: `15/11/2026`, `15-11-26`, `20 de diciembre`, `hoy`, `mañana`, `pasado mañana`.
- **Horas**: `13:30`, `1:30 pm`, `7pm`, `a las 8`, `1:30 de la tarde`.
- **Cantidades**: `2 hamburguesas`, `2x papas`, `refresco x3`, `dos pizzas`, `media docena`.
- **Variaciones**: lo que va entre paréntesis o después de `sin`, `extra`, `poco`…
- **Errores de tipeo y alias**: `hamburgesa`, `piza peperoni`, `coca cola` → Refresco.
- **"Lo de siempre"** (`lo mismo`, `lo de la otra vez`…): repite el último pedido del cliente.

### Reglas de los datos

| Dato | Regla |
|---|---|
| Platos | Obligatorio. Si un nombre sirve para varios platos ("pizza") se pregunta cuál; lo que no está en el menú se anota como **extra** y no bloquea el pedido |
| Cédula, nombre y dirección | Obligatorios |
| Apellido | Opcional |
| Fecha y hora | Si no vienen se asume el momento actual; si vienen mal escritas se preguntan |

Un dato mal escrito (cédula `123`, hora `cuando puedan`, una fecha que ya pasó) nunca se
guarda: se pregunta de nuevo con un ejemplo del formato correcto.

## Clientes y promociones

| Clasificación | Regla | Promoción sugerida |
|---|---|---|
| Nuevo | Sin pedidos | 10% en su primer pedido |
| Inactivo | Más de 30 días sin pedir | 15% por volver |
| Ocasional | 1 o 2 pedidos | Envío gratis en el próximo |
| Recurrente | 3 a 10 pedidos | 5% de descuento |
| VIP | Más de 10 pedidos | Bebida gratis |

Los pedidos cancelados no cuentan para la clasificación ni para "lo de siempre".

## Estructura del proyecto

```
main.py                       menú principal y flujo del programa
parser_mensajes/              interpreta el mensaje del chat
  normalizar.py               minúsculas, acentos y plurales
  campos.py                   cédula, nombre, fecha, hora y validación de datos
  platos.py                   catálogo con alias; reconoce platos, cantidades y variaciones
  parser.py                   analizar_mensaje(): convierte el texto en un pedido
  completar.py                completar_pedido() y confirmar_pedido(): preguntar, resumir y corregir
  entrada.py                  lectura de mensajes pegados en varias líneas
models/                       Cliente, Pedido, DetallePedido, Plato, Menu, Pago, Mensaje
services/
  cola_pedidos.py             cola ordenada por fecha y hora (búsqueda binaria)
  gestor_pedidos.py           duplicados, incompletos, entregar, cancelar y pagos
  clientes_service.py         registro, "lo de siempre", clasificación y promociones
  directorio_clientes.py      directorio e historial de compras
  persistencia.py             carga y guardado de los archivos JSON
  reporte.py                  reporte de ventas del día
utils/
  estilo.py                   colores, recuadros y símbolos de la terminal
  consola.py                  limpiar pantalla y pausar
  validaciones.py             lectura validada de opciones, números y textos
datos/menu.json               menú del restaurante (con alias por plato)
pruebas/mensajes_prueba.txt   mensajes de ejemplo para el parser
tests/                        pruebas automáticas
probar_parser.py              herramienta para probar solo el parser
```

## Datos que guarda el programa

| Archivo | Contenido |
|---|---|
| `datos/menu.json` | Menú: `id`, `nombre`, `precio` y `alias` de cada plato. Se edita a mano; el programa solo lo lee |
| `datos/clientes.json` | Clientes registrados |
| `datos/pedidos.json` | Todos los pedidos con sus platos, variaciones, extras, pagos y estado |
| `datos/incompletos.json` | Pedidos a medias de la bandeja |
| `registros/reporte_del_dia_AAAA-MM-DD.txt` | Reporte de ventas de cada día |
| `registros/comandas.txt` | Últimas comandas mostradas para cocina |

Todos menos `menu.json` los crea el programa y no se suben al repositorio. Para empezar
desde cero basta con borrarlos.

## Pruebas

```bash
python -m unittest discover tests
```

Para probar solo el parser con mensajes propios o con el lote de ejemplos:

```bash
python probar_parser.py
```

```bash
python probar_parser.py --lote
```

## Equipo

- **Juan:** parser de mensajes e integración
- **José:** modelos, persistencia y reporte
- **Yosgluis:** cola, estados y menú principal
- **Sonia:** clientes, búsqueda y promociones
