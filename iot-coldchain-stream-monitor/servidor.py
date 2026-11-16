import random
import time
from concurrent import futures
from datetime import datetime

import grpc

import monitor_cadena_frio_pb2 as cadena_frio_pb2
import monitor_cadena_frio_pb2_grpc as cadena_frio_grpc

DIRECCION = "[::]:50052"
TEMPERATURA_MINIMA = 2.0
TEMPERATURA_MAXIMA = 8.0

# Camiones registrados y su ubicación inicial (latitud, longitud)
CAMIONES = {
    "CAM-001": (19.4326, -99.1332),
    "CAM-002": (25.6866, -100.3161),
    "CAM-003": (20.6597, -103.3496),
}


class ServicioMonitorCadenaFrio(cadena_frio_grpc.MonitorCadenaFrioServicer):

    def TransmitirTelemetria(self, suscripcion, contexto):
        if suscripcion.id_camion not in CAMIONES:
            contexto.set_code(grpc.StatusCode.NOT_FOUND)
            contexto.set_details(f"Camión {suscripcion.id_camion} no encontrado")
            return

        while contexto.is_active():
            yield self._generar_lectura(suscripcion.id_camion)
            time.sleep(suscripcion.intervalo_segundos)

    def _generar_lectura(self, id_camion):
        latitud, longitud = CAMIONES[id_camion]
        temperatura = round(random.uniform(0.0, 10.0), 2)
        return cadena_frio_pb2.LecturaSensor(
            id_camion=id_camion,
            temperatura_celsius=temperatura,
            latitud=latitud + random.uniform(-0.01, 0.01),
            longitud=longitud + random.uniform(-0.01, 0.01),
            timestamp=datetime.now().isoformat(timespec="seconds"),
            alerta_critica=self._es_alerta_critica(temperatura),
        )

    @staticmethod
    def _es_alerta_critica(temperatura):
        return temperatura < TEMPERATURA_MINIMA or temperatura > TEMPERATURA_MAXIMA


def iniciar_servidor():
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    cadena_frio_grpc.add_MonitorCadenaFrioServicer_to_server(ServicioMonitorCadenaFrio(), servidor)
    servidor.add_insecure_port(DIRECCION)
    servidor.start()
    print(f"Servidor MonitorCadenaFrio escuchando en {DIRECCION}")
    servidor.wait_for_termination()


if __name__ == "__main__":
    iniciar_servidor()
