# Validador de Pagos con gRPC

Microservicio gRPC **unario** que valida una solicitud de pago con tarjeta de crédito antes de autorizarla y devuelve si la transacción fue **aprobada** o **rechazada**. Cuando la solicitud es inválida o la tarjeta está bloqueada, responde con el código de estado gRPC que corresponde.

> **Contexto:** una pasarela de pagos procesa miles de compras por minuto y el checkout necesita validar cada transacción en menos de 50 ms. Por eso se usa gRPC (HTTP/2) con Protobuf, que serializa en binario.

---

## Tecnologías utilizadas

| Tecnología | Uso en el proyecto |
|---|---|
| **Python 3** | Lenguaje del servidor y del cliente |
| **gRPC** (`grpcio`) | Comunicación RPC sobre HTTP/2 entre cliente y servidor |
| **Protocol Buffers** (`protobuf`) | Definición del contrato y serialización binaria de los mensajes |
| **grpcio-tools** | Compilador `protoc` que genera el código Python a partir del `.proto` |
| **concurrent.futures** | `ThreadPoolExecutor` con el que el servidor atiende solicitudes en paralelo |
| **uuid** | Generación del código de autorización de cada pago aprobado |

---

## Estructura del proyecto

```
payment-fraud-validator/
├── protos/
│   └── validador_pagos.proto      # Contrato del servicio (mensajes y RPC)
├── validador_pagos_pb2.py         # Generado: clases de los mensajes
├── validador_pagos_pb2_grpc.py    # Generado: stub del cliente y base del servidor
├── servidor.py                    # Servidor gRPC con las reglas de negocio
├── cliente.py                     # Cliente que ejecuta los casos de prueba
├── requirements.txt               # Dependencias
└── README.md
```

---

## Contrato del servicio (`.proto`)

```proto
service ValidadorPagos {
  rpc VerificarTransaccion (SolicitudPago) returns (ResultadoPago);
}

message SolicitudPago {
  string id_transaccion = 1;
  string numero_tarjeta = 2;
  double monto = 3;
  string codigo_moneda = 4;
  string pais_origen = 5;
}

message ResultadoPago {
  bool aprobado = 1;
  string codigo_autorizacion = 2;
  string motivo_rechazo = 3;
}
```

---

## Reglas de negocio

El servidor revisa las reglas en este orden:

| # | Condición | Respuesta |
|---|---|---|
| 1 | `monto <= 0` o `numero_tarjeta` no tiene 16 dígitos | Error `INVALID_ARGUMENT`: *"Monto o número de tarjeta inválido"* |
| 2 | La tarjeta inicia con `4000` (lista negra) | Error `PERMISSION_DENIED`: *"Tarjeta bloqueada por fraude"* |
| 3 | `monto > 10,000 USD` y `pais_origen` no es `US` ni `MX` | `aprobado = false` con el motivo de rechazo por política de fraude |
| 4 | Ninguna de las anteriores | `aprobado = true` con un código de autorización (`AUT-XXXXXXXX`) |

> Se asume que el monto viene en USD; no se convierte según `codigo_moneda`.

---

## Clases principales

- **`ServicioValidadorPagos`** (`servidor.py`): implementa el RPC `VerificarTransaccion` y aplica las reglas de negocio.
- **`ClienteValidadorPagos`** (`cliente.py`): envuelve el stub gRPC, envía la solicitud y captura los errores con `except grpc.RpcError as e`, mostrando `e.code()` y `e.details()`.

---

## Instalación

Desde la raíz del repositorio:

**1. Crear y activar un entorno virtual**

```bash
python -m venv .venv
```

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

**2. Instalar las dependencias**

```bash
pip install -r payment-fraud-validator/requirements.txt
```

**3. (Opcional) Regenerar el código gRPC**

Solo hace falta si se modifica el archivo `.proto`. Se ejecuta dentro de `payment-fraud-validator/`:

```bash
python -m grpc_tools.protoc -I protos --python_out=. --grpc_python_out=. protos/validador_pagos.proto
```

---

## Ejecución

Se usan **dos terminales**, ambas dentro de `payment-fraud-validator/` y con el entorno virtual activo.

**Terminal 1: levantar el servidor**

```bash
python servidor.py
```

```
Servidor ValidadorPagos escuchando en [::]:50051
```

**Terminal 2: ejecutar el cliente**

```bash
python cliente.py
```

---

## Casos de prueba y resultado esperado

| Caso | Tarjeta | Monto | País | Resultado |
|---|---|---|---|---|
| Pago exitoso | `4111111111111111` | 250.00 | MX | Aprobado |
| Argumento inválido | `4111111111111111` | -50.00 | US | `INVALID_ARGUMENT` |
| Tarjeta denegada | `4000123456789012` | 100.00 | US | `PERMISSION_DENIED` |

Salida del cliente:

```
=== Pago exitoso ===
Aprobado: True
Código de autorización: AUT-A178F363
Motivo de rechazo:

=== Argumento inválido (monto negativo) ===
Código de error: StatusCode.INVALID_ARGUMENT
Detalle: Monto o número de tarjeta inválido

=== Tarjeta denegada (lista negra) ===
Código de error: StatusCode.PERMISSION_DENIED
Detalle: Tarjeta bloqueada por fraude
```

> El código de autorización cambia en cada ejecución porque se genera con `uuid`.
