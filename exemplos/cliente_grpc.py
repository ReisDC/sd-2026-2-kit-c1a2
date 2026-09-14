"""Cliente gRPC de exemplo. Rode com o servico no ar (python -m app.servidor_grpc)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import grpc
import inferencia_pb2
import inferencia_pb2_grpc

ENDERECO = "localhost:50051"


def prever(stub, texto):
    r = stub.Prever(inferencia_pb2.PedidoPrever(texto=texto))
    print("prever:", r)


def prever_lote(stub, textos):
    r = stub.PreverLote(inferencia_pb2.PedidoLote(textos=textos))
    print("prever_lote:", r)


if __name__ == "__main__":
    texto = " ".join(sys.argv[1:]) or "o atendimento foi muito bom"

    canal = grpc.insecure_channel(ENDERECO)
    stub = inferencia_pb2_grpc.InferenciaStub(canal)

    try:
        prever(stub, texto)
        prever_lote(stub, [texto, "pessimo"])
    except grpc.RpcError as e:
        print(f"erro ao chamar o servico gRPC em {ENDERECO}:", e.details())
