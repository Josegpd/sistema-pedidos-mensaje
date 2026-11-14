def leer_opcion_menu(prompt: str, opciones_validas: list[str]) -> str:

    # Solicita una opción hasta que coincida con una de las permitidas
    while True:
        valor = input(prompt).strip().lstrip("\ufeff")
        if valor in opciones_validas:
            return valor
        print(f"Opción no válida. Ingrese una de las opciones: {', '.join(opciones_validas)}")

def leer_entero(prompt: str, min_val: int = None, max_val: int = None) -> int:

    # Solicita un entero validando rango y evitando caídas por ValueError
    while True:
        entrada = input(prompt).strip()
        try:
            num = int(entrada)
            if min_val is not None and num < min_val:
                print(f"Debe ser mayor o igual a {min_val}.")
                continue
            if max_val is not None and num > max_val:
                print(f"Debe ser menor o igual a {max_val}.")
                continue
            return num
        except ValueError:
            print("Entrada inválida. Ingrese un número entero.")

def leer_float_positivo(prompt: str) -> float:
    # Solicita un monto monetario mayor a 0
    while True:
        entrada = input(prompt).strip().replace(",", ".")
        try:
            monto = float(entrada)
            if monto <= 0:
                print("El monto debe ser un número positivo.")
                continue
            return monto
        except ValueError:
            print("Ingrese un valor numérico válido (ejemplo: 12.50).")

def leer_texto_no_vacio(prompt: str) -> str:
    # Solicita un texto que no puede quedar en blanco
    while True:
        texto = input(prompt).strip()
        if texto:
            return texto
        print("Este campo no puede estar vacío.")

def confirmar_accion(prompt: str) -> bool:
    # Solicita confirmación s/n
    while True:
        resp = input(f"{prompt} (s/n): ").strip().lower()
        if resp in ("s", "si", "sí", "Sí"):
            return True
        if resp in ("n", "no", "No"):
            return False
        print("Responda con 's' o 'n'.")