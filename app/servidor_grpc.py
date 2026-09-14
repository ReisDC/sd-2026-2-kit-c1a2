"""
Interface gRPC do servico de inferencia.

PRE-REQUISITO: gerar os stubs antes de rodar (veja scripts/gerar_stubs).

O QUE JA ESTA PRONTO: os metodos Prever e PreverLote (TAREFAS.md, item 4).

Rodar:  python -m app.servidor_grpc
"""
import logging
import time
import uuid
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("grpc")


class ServicoInferencia(inferencia_pb2_grpc.InferenciaServicer):

    def __init__(self):
        logger.info("carregando modelo...")
        self.modelo = carregar_modelo()
        logger.info("modelo pronto")

    def Prever(self, request, context):
        requisicao_id = str(uuid.uuid4())
        inicio = time.time()
        r = self.modelo.prever(request.texto)
        tempo_ms = round((time.time() - inicio) * 1000, 2)
        logger.info(
            "id=%s metodo=Prever tamanho_entrada=%d tempo_ms=%s",
            requisicao_id, len(request.texto), tempo_ms,
        )
        return inferencia_pb2.RespostaPrever(
            texto=r["texto"], sentimento=r["sentimento"], confianca=r["confianca"]
        )

    def PreverLote(self, request, context):
        requisicao_id = str(uuid.uuid4())
        inicio = time.time()
        respostas = []
        for texto in request.textos:
            r = self.modelo.prever(texto)
            respostas.append(
                inferencia_pb2.RespostaPrever(
                    texto=r["texto"], sentimento=r["sentimento"], confianca=r["confianca"]
                )
            )
        tempo_ms = round((time.time() - inicio) * 1000, 2)
        tamanho_entrada = sum(len(t) for t in request.textos)
        logger.info(
            "id=%s metodo=PreverLote qtd_textos=%d tamanho_entrada=%d tempo_ms=%s",
            requisicao_id, len(request.textos), tamanho_entrada, tempo_ms,
        )
        return inferencia_pb2.RespostaLote(resultados=respostas)


def servir(porta: int = 50051):
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inferencia_pb2_grpc.add_InferenciaServicer_to_server(
        ServicoInferencia(), servidor)
    servidor.add_insecure_port(f"[::]:{porta}")
    servidor.start()
    logger.info("escutando na porta %d", porta)
    servidor.wait_for_termination()


if __name__ == "__main__":
    servir()
