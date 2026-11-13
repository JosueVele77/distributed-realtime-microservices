import grpc

import validador_pagos_pb2 as pagos_pb2
import validador_pagos_pb2_grpc as pagos_grpc

DIRECCION_SERVIDOR = "localhost:50051"


class ClienteValidadorPagos:

    def __init__(self, canal):
        self._stub = pagos_grpc.ValidadorPagosStub(canal)

    def verificar(self, nombre_caso, solicitud):
        print(f"\n=== {nombre_caso} ===")
        try:
            resultado = self._stub.VerificarTransaccion(solicitud)
            print(f"Aprobado: {resultado.aprobado}")
            print(f"Código de autorización: {resultado.codigo_autorizacion}")
            print(f"Motivo de rechazo: {resultado.motivo_rechazo}")
        except grpc.RpcError as e:
            print(f"Código de error: {e.code()}")
            print(f"Detalle: {e.details()}")


def ejecutar_casos_de_prueba():
    casos = {
        "Pago exitoso": pagos_pb2.SolicitudPago(
            id_transaccion="TX-001",
            numero_tarjeta="4111111111111111",
            monto=250.00,
            codigo_moneda="USD",
            pais_origen="MX",
        ),
        "Argumento inválido (monto negativo)": pagos_pb2.SolicitudPago(
            id_transaccion="TX-002",
            numero_tarjeta="4111111111111111",
            monto=-50.00,
            codigo_moneda="USD",
            pais_origen="US",
        ),
        "Tarjeta denegada (lista negra)": pagos_pb2.SolicitudPago(
            id_transaccion="TX-003",
            numero_tarjeta="4000123456789012",
            monto=100.00,
            codigo_moneda="USD",
            pais_origen="US",
        ),
    }

    with grpc.insecure_channel(DIRECCION_SERVIDOR) as canal:
        cliente = ClienteValidadorPagos(canal)
        for nombre_caso, solicitud in casos.items():
            cliente.verificar(nombre_caso, solicitud)


if __name__ == "__main__":
    ejecutar_casos_de_prueba()
