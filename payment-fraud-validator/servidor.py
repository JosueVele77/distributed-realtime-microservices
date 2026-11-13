import uuid
from concurrent import futures

import grpc

import validador_pagos_pb2 as pagos_pb2
import validador_pagos_pb2_grpc as pagos_grpc

DIRECCION = "[::]:50051"
LONGITUD_TARJETA = 16
PREFIJO_LISTA_NEGRA = "4000"
MONTO_LIMITE_USD = 10_000
PAISES_EMISORES = {"US", "MX"}


class ServicioValidadorPagos(pagos_grpc.ValidadorPagosServicer):

    def VerificarTransaccion(self, solicitud, contexto):
        if not self._datos_validos(solicitud):
            contexto.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            contexto.set_details("Monto o número de tarjeta inválido")
            return pagos_pb2.ResultadoPago()

        if solicitud.numero_tarjeta.startswith(PREFIJO_LISTA_NEGRA):
            contexto.set_code(grpc.StatusCode.PERMISSION_DENIED)
            contexto.set_details("Tarjeta bloqueada por fraude")
            return pagos_pb2.ResultadoPago()

        if self._viola_politica_fraude(solicitud):
            return pagos_pb2.ResultadoPago(
                aprobado=False,
                motivo_rechazo="Rechazado por política de fraude: país de origen no coincide con el emisor",
            )

        return pagos_pb2.ResultadoPago(
            aprobado=True,
            codigo_autorizacion=self._generar_codigo_autorizacion(),
        )

    @staticmethod
    def _datos_validos(solicitud):
        tarjeta = solicitud.numero_tarjeta
        return solicitud.monto > 0 and len(tarjeta) == LONGITUD_TARJETA and tarjeta.isdigit()

    @staticmethod
    def _viola_politica_fraude(solicitud):
        return solicitud.monto > MONTO_LIMITE_USD and solicitud.pais_origen not in PAISES_EMISORES

    @staticmethod
    def _generar_codigo_autorizacion():
        return f"AUT-{uuid.uuid4().hex[:8].upper()}"


def iniciar_servidor():
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pagos_grpc.add_ValidadorPagosServicer_to_server(ServicioValidadorPagos(), servidor)
    servidor.add_insecure_port(DIRECCION)
    servidor.start()
    print(f"Servidor ValidadorPagos escuchando en {DIRECCION}")
    servidor.wait_for_termination()


if __name__ == "__main__":
    iniciar_servidor()
