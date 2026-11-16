import grpc

import monitor_cadena_frio_pb2 as cadena_frio_pb2
import monitor_cadena_frio_pb2_grpc as cadena_frio_grpc

DIRECCION_SERVIDOR = "localhost:50052"
ID_CAMION = "CAM-003"
INTERVALO_SEGUNDOS = 1

ROJO = "\033[91m"
RESET = "\033[0m"


class ClienteMonitorCadenaFrio:

    def __init__(self, canal):
        self._stub = cadena_frio_grpc.MonitorCadenaFrioStub(canal)

    def monitorear(self, id_camion, intervalo_segundos):
        peticion = cadena_frio_pb2.SuscripcionCamion(
            id_camion=id_camion,
            intervalo_segundos=intervalo_segundos,
        )
        print(f"Suscrito a la telemetría de {id_camion} (Ctrl+C para detener)\n")
        try:
            for respuesta in self._stub.TransmitirTelemetria(peticion):
                self._mostrar_lectura(respuesta)
        except grpc.RpcError as e:
            print(f"Código de error: {e.code()}")
            print(f"Detalle: {e.details()}")
        except KeyboardInterrupt:
            print("\nMonitoreo detenido")

    @staticmethod
    def _mostrar_lectura(lectura):
        texto = (
            f"[{lectura.timestamp}] {lectura.id_camion} | "
            f"{lectura.temperatura_celsius:5.2f} °C | "
            f"({lectura.latitud:.4f}, {lectura.longitud:.4f})"
        )
        if lectura.alerta_critica:
            print(f"{ROJO}{texto} | ¡ALERTA CRÍTICA: temperatura fuera de rango!{RESET}")
        else:
            print(texto)


def iniciar_monitoreo():
    with grpc.insecure_channel(DIRECCION_SERVIDOR) as canal:
        ClienteMonitorCadenaFrio(canal).monitorear(ID_CAMION, INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    iniciar_monitoreo()
