# Proyectito: pedidos por chat (terminal)

Programa de terminal en Python para registrar los pedidos de un restaurante
que llegan por chat. Sin interfaz gráfica ni base de datos: los datos se
guardan en archivos JSON.

Requisitos: **Python 3.10 o superior**, solo biblioteca estándar (no hay que instalar nada).

## Estructura

```
parser_mensajes/        Parser de mensajes (Juan)
  normalizar.py         minúsculas, acentos, plurales
  campos.py             cédula, nombres, fecha y hora
  platos.py             catálogo con alias y reconocimiento de platos/cantidades
  parser.py             analizar_mensaje(), calcular_faltantes(), mensajes_para_cliente(), resumen_para_operador()
  completar.py          completar_pedido() y funciones para corregir un pedido incompleto
  entrada.py            lectura de mensajes pegados en varias líneas y del lote de prueba
datos/menu.json         menú de ejemplo (con alias por plato)
pruebas/mensajes_prueba.txt   lote de mensajes de prueba
tests/test_parser.py    pruebas automáticas
probar_parser.py        prueba del parser por terminal
```

## Cómo probar

```bash
python probar_parser.py
```

Elige `1`, pega el mensaje del chat y escribe `FIN` en una línea sola
(o Ctrl+Z y Enter en Windows / Ctrl+D en Linux y Mac).

```bash
python probar_parser.py --lote
```

```bash
python -m unittest discover tests
```

## Formato del mensaje (propuesta, confirmar con mensajes reales)

```
Cédula: V-12.345.678
Nombres: Juan Carlos
Apellidos: Pérez Gómez
Dirección: Av. Bolívar, edificio Sol, piso 3
Fecha: 15/11/2026
Hora: 1:30 pm
Pedido:
- 2 hamburguesas clásicas (sin cebolla)
- 1 refresco
- 3 empanadas de queso
```

Lo que también entiende:

- **Etiquetas alternativas**: `CI`, `C.I.`, `Nombre`, `Nombre completo`, `Cliente`, `Dir`,
  `Para`, `Fecha y hora`, `Platos`, `Orden`… Cada campo va en una sola línea.
- **Texto libre**: `soy Pedro Ramírez, mi CI es V-15.222.333, quiero 2 empanadas de carne
  y una coca cola para hoy a la 1:30 pm` (la dirección sí debe ir con su etiqueta).
- **Chat copiado de WhatsApp** (`[12/11/26, 11:05] Maria: ...`): se quita el encabezado
  y, si el mensaje no dice fecha u hora, se usa la de recepción (con aviso).
- **Fechas**: `15/11/2026`, `15-11-26`, `20 de diciembre`, `hoy`, `mañana`, `pasado mañana`.
- **Horas**: `13:30`, `1:30 pm`, `7pm`, `a las 8`, `1:30 de la tarde`.
- **Cantidades**: `2 hamburguesas`, `2x papas`, `refresco x3`, `pizza 2`, `dos`, `una`, `media docena`.
- **Varios platos por línea**: separados por coma, `;`, `+` o `y` antes de una cantidad.
- **Platos fuera del menú**: van a `extras` y no impiden registrar el pedido.
- **Variaciones**: lo que va entre paréntesis o tras `sin`, `extra`, `con extra`, `poco`…
- **Errores de tipeo y alias**: `hamburgesa`, `piza peperoni`, `coca cola` → Refresco.
- **"Lo de siempre"** (`lo mismo`, `lo de la otra vez`, `lo usual`…): se marca
  `lo_de_siempre = True` y no se exige la lista de platos.

## Cómo usarlo desde otros módulos

```python
from parser_mensajes import Catalogo, analizar_mensaje, calcular_faltantes, leer_mensaje_pegado

catalogo = Catalogo.desde_archivo("datos/menu.json")   # o Catalogo(lista_de_dicts_del_menu)
pedido = analizar_mensaje(leer_mensaje_pegado(), catalogo)

pedido["cliente"]        # {"cedula": "V-12345678", "nombres", "apellidos", "direccion"}
pedido["fecha"]          # "2026-11-15"  (formato ISO: se ordena bien como texto)
pedido["hora"]           # "13:30"
pedido["platos"]         # [{"id_plato", "nombre", "cantidad", "precio", "variacion", "texto"}]
pedido["total_estimado"]
pedido["lo_de_siempre"]  # True -> buscar en el historial del cliente (Sonia)
pedido["extras"]         # [{"texto", "cantidad", "variacion"}] lo que no está en el menú (no suma al total)
pedido["ambiguos"]       # [{"texto", "cantidad", "variacion", "opciones": [{"id", "nombre", "precio"}]}]
pedido["invalidos"]      # {"hora": "No entendimos la hora 'x'. Escríbala así: ..."}
pedido["faltantes"]      # ["direccion", "hora", ...] (incluye los inválidos)
pedido["advertencias"]   # avisos internos para el operador
pedido["completo"]       # True si no falta nada y no hay platos ambiguos (los extras no impiden)
pedido["fecha_recepcion"], pedido["texto_original"]   # para MensajeChat
```

### Qué es obligatorio

| Dato | Regla |
|---|---|
| Platos | **obligatorio**: al menos uno entendido (o "lo de siempre") y ningún ambiguo |
| Nombre | **obligatorio** |
| Dirección | **obligatoria** |
| Fecha y hora | si no vienen se asume el momento actual (o el de recepción del chat); si vienen mal escritas se preguntan |
| Cédula y apellido | opcionales; si vienen mal escritas se descartan y queda el aviso para el cliente |

### Pedidos incompletos: solo pasan datos correctos

Un dato mal escrito (cédula `123`, hora `cuando puedan`, fecha que ya pasó, nombre con
números…) **no se guarda**: queda en `None`, aparece en `faltantes` y su explicación en
`invalidos`. Así, cuando `completo` es True, todos los datos están validados y normalizados.

```python
for frase in mensajes_para_cliente(pedido):   # lo que hay que decirle al cliente
    print(frase)
# Faltó en su pedido: la dirección de entrega y la hora de entrega.
# No entendimos la fecha 'el finde'. Escríbala así: 15/11/2026, 'hoy' o 'mañana'.
# ¿Cuál '2 pizzas' desea? Tenemos: Pizza margarita o Pizza pepperoni.
# '1 sushi' no es parte de nuestro menú; lo anotamos como extra (sujeto a disponibilidad).

completar_pedido(pedido, catalogo)   # pregunta al operador solo lo que falta, valida cada
                                     # respuesta y deja elegir la opción de los ambiguos.
                                     # 'cancelar' lo deja pendiente. Devuelve True si quedó completo.
```

Funciones sueltas, por si el menú quiere preguntar a su manera:
`completar_campo(pedido, campo, valor)` (devuelve el error o None),
`resolver_ambiguo(pedido, indice, id_plato)` (`None` = pasarlo a extras),
`agregar_platos(pedido, "2 hamburguesas", catalogo)` y `validar_campo(campo, valor, hoy)`.

Notas para el equipo:

- **Cédula** siempre como `"V-12345678"` / `"E-12345678"` (sin puntos).
- El parser solo ve el mensaje. Si el cliente ya está registrado, sus nombres y dirección
  se rellenan desde el registro y luego se llama a `calcular_faltantes(pedido)` para
  actualizar `faltantes` y `completo` (lo mismo después de que el operador complete datos).
- La **detección de duplicados** se hace al registrar el pedido: dos mensajes iguales
  producen el mismo `cliente`, `fecha`, `hora` y `platos`.
- El **menú** debe tener por plato: `id`, `nombre`, `precio` y opcionalmente `alias`
  (lista de otras formas de llamarlo). Si un alias se repite en dos platos (p. ej. `pizza`),
  ese texto queda como ambiguo y el operador elige.

## Equipo

- Juan: parser de mensajes
- José: modelos, persistencia y cierre
- Yosgluis: cola, estados y esqueleto del programa
- Sonia: clientes, búsqueda y promociones
