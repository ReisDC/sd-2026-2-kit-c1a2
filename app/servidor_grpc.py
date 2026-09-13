"""
Interface gRPC do servico de inferencia.

PRE-REQUISITO: gerar os stubs antes de rodar (veja scripts/gerar_stubs).

O QUE JA ESTA PRONTO: o metodo Prever.
O QUE VOCE PRECISA FAZER (TAREFAS.md, item 4): o metodo PreverLote.

Rodar:  python -m app.servidor_grpc
"""
from concurrent import futures
from fastapi import FastAPI, HTTPException
import logging

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

app = FastAPI()

@app.post("/infer")
async def infer(texto: str):
    if not texto:
        raise HTTPException(
            status_code=400,
            detail="O texto não pode estar vazio"
        )

try:
    resultado = modelo.predict(texto)
except Exception as e:
    logger.error(f"Erro na inferência: {e}")
    raise HTTPException(
        status_code=500,
        detail="Erro interno ao executar a inferência"
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

logger.info("Requisição recebida na rota /infer")

@app.post("/infer")
async def infer(texto: str):

    logger.info(f"Requisição recebida: texto='{texto}'")

    if not texto:
        logger.warning("Requisição rejeitada: texto vazio")
        raise HTTPException(
            status_code=400,
            detail="O texto não pode estar vazio"
        )

    try:
        # processamento
        resultado = modelo.predict(texto)

        logger.info("Inferência realizada com sucesso")

        return {"resultado": resultado}

    except Exception as e:
        logger.error(f"Erro durante a inferência: {e}")

        raise HTTPException(
            status_code=500,
            detail="Erro interno no servidor"
        )


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
