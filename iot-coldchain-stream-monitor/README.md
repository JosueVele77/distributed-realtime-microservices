# Monitor de Cadena de Frío con gRPC (Server Streaming)

Microservicio gRPC con patrón **Server Streaming**. El cliente envía **una sola petición** de suscripción a un camión y el servidor le responde con un **flujo continuo** de lecturas de sus sensores (temperatura, ubicación y hora). Cuando la temperatura sale del rango permitido, la lectura llega marcada como alerta crítica.

> **Contexto:** una empresa de logística farmacéutica transporta vacunas que deben mantenerse entre **2 °C y 8 °C**. La central de monitoreo se suscribe a la telemetría de cada camión para reaccionar de inmediato si se rompe la cadena de frío.

---

## Tecnologías utilizadas

| Tecnología | Uso en el proyecto |
|---|---|
| **Python 3** | Lenguaje del servidor y del cliente |
| **gRPC** (`grpcio`) | Comunicación RPC sobre HTTP/2 con streaming del servidor al cliente |
| **Protocol Buffers** (`protobuf`) | Definición del contrato y serialización binaria de los mensajes |
| **grpcio-tools** | Compilador `protoc` que genera el código Python a partir del `.proto` |
| **concurrent.futures** | `ThreadPoolExecutor` con el que el servidor atiende varias suscripciones a la vez |
| **random** | Simulación de la temperatura y de la ubicación del camión |
| **time** | `time.sleep(intervalo_segundos)` entre cada lectura enviada |
| **datetime** | `timestamp` de cada lectura |

---

## Estructura del proyecto

```
iot-coldchain-stream-monitor/
├── protos/
│   └── monitor_cadena_frio.proto      # Contrato del servicio (mensajes y RPC)
├── monitor_cadena_frio_pb2.py         # Generado: clases de los mensajes
├── monitor_cadena_frio_pb2_grpc.py    # Generado: stub del cliente y base del servidor
├── servidor.py                        # Servidor gRPC que emite la telemetría con yield
├── cliente.py                         # Cliente que consume el stream y resalta las alertas
├── requirements.txt                   # Dependencias
└── README.md
```

---

## Contrato del servicio (`.proto`)

```proto
service MonitorCadenaFrio {
  rpc TransmitirTelemetria (SuscripcionCamion) returns (stream LecturaSensor);
}

message SuscripcionCamion {
  string id_camion = 1;
  int32 intervalo_segundos = 2;
}

message LecturaSensor {
  string id_camion = 1;
  double temperatura_celsius = 2;
  double latitud = 3;
  double longitud = 4;
  string timestamp = 5;
  bool alerta_critica = 6;
}
```

La palabra `stream` en la respuesta es lo que convierte al RPC en **Server Streaming**.

---

## Reglas de negocio

| # | Condición | Respuesta |
|---|---|---|
| 1 | `id_camion` no es `CAM-001` ni `CAM-002` | Error `NOT_FOUND`: *"Camión <id> no encontrado"* |
| 2 | Camión válido | El servidor emite una `LecturaSensor` con `yield` cada `intervalo_segundos` mientras el cliente siga conectado |
| 3 | Temperatura `< 2.0 °C` o `> 8.0 °C` | La lectura se envía con `alerta_critica = true` |

---

## Clases principales

- **`ServicioMonitorCadenaFrio`** (`servidor.py`): implementa el RPC `TransmitirTelemetria`. Valida el camión, genera lecturas simuladas y las emite con `yield` dentro de un bucle con `time.sleep`.
- **`ClienteMonitorCadenaFrio`** (`cliente.py`): se suscribe al camión y consume el stream con `for respuesta in stub.TransmitirTelemetria(peticion):`. Muestra en **rojo** las lecturas con alerta crítica y captura los errores con `except grpc.RpcError as e`.

---

## Configuración fácil de editar

Los valores que más se suelen cambiar están como constantes al inicio de cada archivo:

| Archivo | Constante | Para qué sirve |
|---|---|---|
| `servidor.py` | `DIRECCION` | Puerto del servidor (`50052`) |
| `servidor.py` | `TEMPERATURA_MINIMA` / `TEMPERATURA_MAXIMA` | Rango permitido de la cadena de frío |
| `servidor.py` | `CAMIONES` | Camiones registrados y su ubicación inicial |
| `cliente.py` | `ID_CAMION` | Camión al que se suscribe el cliente |
| `cliente.py` | `INTERVALO_SEGUNDOS` | Cada cuántos segundos llega una lectura |

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
pip install -r iot-coldchain-stream-monitor/requirements.txt
```

**3. (Opcional) Regenerar el código gRPC**

Solo hace falta si se modifica el archivo `.proto`. Se ejecuta dentro de `iot-coldchain-stream-monitor/`:

```bash
python -m grpc_tools.protoc -I protos --python_out=. --grpc_python_out=. protos/monitor_cadena_frio.proto
```

---

## Ejecución

Se usan **dos terminales**, ambas dentro de `iot-coldchain-stream-monitor/` y con el entorno virtual activo.

**Terminal 1: levantar el servidor**

```bash
python servidor.py
```

```
Servidor MonitorCadenaFrio escuchando en [::]:50052
```

**Terminal 2: ejecutar el cliente**

```bash
python cliente.py
```

El stream es continuo: las lecturas siguen llegando hasta que se presiona **Ctrl+C** en el cliente.

---

## Resultado esperado

Suscripción a `CAM-001`. Las lecturas con alerta crítica se ven en **rojo** en la consola:

```
Suscrito a la telemetría de CAM-001 (Ctrl+C para detener)

[2026-11-16T17:21:49] CAM-001 |  2.44 °C | (19.4284, -99.1331)
[2026-11-16T17:21:50] CAM-001 |  2.75 °C | (19.4392, -99.1251)
[2026-11-16T17:21:51] CAM-001 |  1.50 °C | (19.4231, -99.1369) | ¡ALERTA CRÍTICA: temperatura fuera de rango!
[2026-11-16T17:21:52] CAM-001 |  9.68 °C | (19.4284, -99.1356) | ¡ALERTA CRÍTICA: temperatura fuera de rango!

Monitoreo detenido
```

Suscripción a un camión que no existe (por ejemplo, `ID_CAMION = "CAM-999"`):

```
Suscrito a la telemetría de CAM-999 (Ctrl+C para detener)

Código de error: StatusCode.NOT_FOUND
Detalle: Camión CAM-999 no encontrado
```

> Las temperaturas y coordenadas son aleatorias, así que cambian en cada ejecución. El color rojo usa códigos ANSI, que se ven en Windows Terminal, en la consola de PyCharm y en las terminales de Linux y macOS.
