"""Consome a fila, salva resultados e trata falhas de inferência.

Rodar: python -m app.worker
"""
import json
import time

from app import fila
from app.modelo import carregar_modelo

MAX_TENTATIVAS = 3
FILA_DESCARTE = "tarefas:descarte"


def processar_tarefa(tarefa, modelo):
    tentativa = tarefa.get("tentativas", 0) + 1
    tarefa["tentativas"] = tentativa
    tarefa_id = tarefa["id"]
    print(f"[worker] processando {tarefa_id}, tentativa {tentativa}")
    inicio = time.time()

    try:
        resultado = modelo.prever(tarefa["texto"])
    except Exception as erro:
        print(f"[worker] ERRO em {tarefa_id}: {erro}")
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
            print(f"[worker] tarefa {tarefa_id} enviada para descarte")
        else:
            print(f"[worker] tarefa {tarefa_id} reenfileirada")
        return

    resultado["status"] = "pronto"
    resultado["tentativas"] = tentativa
    resultado["tempo_ms"] = round((time.time() - inicio) * 1000, 2)
    fila.guardar_resultado(tarefa_id, resultado)


def main():
    print("[worker] carregando modelo...")
    modelo = carregar_modelo()
    print("[worker] pronto. aguardando tarefas (Ctrl+C para sair)")

    while True:
        tarefa = fila.proxima_tarefa(timeout=5)
        if tarefa is not None:
            processar_tarefa(tarefa, modelo)


if __name__ == "__main__":
    main()
