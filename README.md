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
  parser.py             analizar_mensaje(), calcular_faltantes(), resumen_para_operador()
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
pedido["ambiguos"]       # [{"texto", "cantidad", "variacion", "opciones": [{"id", "nombre"}]}]
pedido["no_reconocidos"] # [{"texto", "cantidad", "variacion"}]
pedido["faltantes"]      # ["direccion", "hora", ...]
pedido["advertencias"]   # avisos para el operador
pedido["completo"]       # True si no falta nada y no hay ambigüedades
pedido["fecha_recepcion"], pedido["texto_original"]   # para MensajeChat
```

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
