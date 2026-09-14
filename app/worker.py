"""Consome a fila, salva resultados e trata falhas de inferência.

Rodar: python -m app.worker
"""
import json
import logging
import time

from app import fila
from app.modelo import carregar_modelo

MAX_TENTATIVAS = 3
FILA_DESCARTE = "tarefas:descarte"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("worker")


def processar_tarefa(tarefa, modelo):
    tentativa = tarefa.get("tentativas", 0) + 1
    tarefa["tentativas"] = tentativa
    tarefa_id = tarefa["id"]
    tamanho_entrada = len(tarefa["texto"])
    logger.info(
        "id=%s tamanho_entrada=%d tentativa=%d - processando",
        tarefa_id, tamanho_entrada, tentativa,
    )
    inicio = time.time()

    try:
        resultado = modelo.prever(tarefa["texto"])
    except Exception as erro:
        tempo_ms = round((time.time() - inicio) * 1000, 2)
        logger.error(
            "id=%s tamanho_entrada=%d tentativa=%d tempo_ms=%s - erro: %s",
            tarefa_id, tamanho_entrada, tentativa, tempo_ms, erro,
        )
        tarefa["ultimo_erro"] = str(erro)

        if tentativa < MAX_TENTATIVAS:
            destino = fila.FILA_TAREFAS
            estado = {"status": "na_fila", "tentativas": tentativa}
        else:
            destino = FILA_DESCARTE
            estado = {
                "status": "erro",
                "tentativas": tentativa,
                "erro": "Inferência falhou após 3 tentativas",
            }

        # Grava o estado e move a tarefa na mesma transação.
        with fila.cliente().pipeline(transaction=True) as transacao:
            transacao.set(fila.PREFIXO_RESULTADO + tarefa_id, json.dumps(estado))
            transacao.rpush(destino, json.dumps(tarefa))
            transacao.execute()

        if destino == FILA_DESCARTE:
            logger.warning("id=%s - enviada para descarte", tarefa_id)
        else:
            logger.info("id=%s - reenfileirada", tarefa_id)
        return

    tempo_ms = round((time.time() - inicio) * 1000, 2)
    resultado["status"] = "pronto"
    resultado["tentativas"] = tentativa
    resultado["tempo_ms"] = tempo_ms
    fila.guardar_resultado(tarefa_id, resultado)
    logger.info(
        "id=%s tamanho_entrada=%d tentativa=%d tempo_ms=%s - concluida",
        tarefa_id, tamanho_entrada, tentativa, tempo_ms,
    )


def main():
    logger.info("carregando modelo...")
    modelo = carregar_modelo()
    logger.info("pronto. aguardando tarefas (Ctrl+C para sair)")

    while True:
        tarefa = fila.proxima_tarefa(timeout=5)
        if tarefa is not None:
            processar_tarefa(tarefa, modelo)


if __name__ == "__main__":
    main()
