"""
Interface gRPC do servico de inferencia.

PRE-REQUISITO: gerar os stubs antes de rodar (veja scripts/gerar_stubs).

O QUE JA ESTA PRONTO: os metodos Prever e PreverLote (TAREFAS.md, item 4).

Rodar:  python -m app.servidor_grpc
"""
from concurrent import futures

import grpc

from app.modelo import carregar_modelo

try:
    import inferencia_pb2
    import inferencia_pb2_grpc
except ImportError:  # pragma: no cover
    raise SystemExit(
        "Stubs nao encontrados. Rode antes:\n"
        "  python -m grpc_tools.protoc -I proto --python_out=. "
        "--grpc_python_out=. proto/inferencia.proto"
    )


class ServicoInferencia(inferencia_pb2_grpc.InferenciaServicer):

    def __init__(self):
        print("[grpc] carregando modelo...")
        self.modelo = carregar_modelo()
        print("[grpc] modelo pronto")

    def Prever(self, request, context):
        r = self.modelo.prever(request.texto)
        return inferencia_pb2.RespostaPrever(
            texto=r["texto"], sentimento=r["sentimento"], confianca=r["confianca"]
        )

    def PreverLote(self, request, context):
        respostas = []
        for texto in request.textos:
            r = self.modelo.prever(texto)
            respostas.append(
                inferencia_pb2.RespostaPrever(
                    texto=r["texto"], sentimento=r["sentimento"], confianca=r["confianca"]
                )
            )
        return inferencia_pb2.RespostaLote(resultados=respostas)


def servir(porta: int = 50051):
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inferencia_pb2_grpc.add_InferenciaServicer_to_server(
        ServicoInferencia(), servidor)
    servidor.add_insecure_port(f"[::]:{porta}")
    servidor.start()
    print(f"[grpc] escutando na porta {porta}")
    servidor.wait_for_termination()


if __name__ == "__main__":
    servir()
