"""
Interface REST do servico de inferencia.

O QUE JA ESTA PRONTO:
  - carregamento do modelo UMA vez, na subida (nao a cada requisicao)
  - rota sincrona /predict-sync, usada no laboratorio da Aula 6

O QUE VOCE PRECISA FAZER (TAREFAS.md, itens 1 e 2):
  - POST /predict  -> colocar na fila e devolver o id
  - GET  /resultado/{id} -> devolver o resultado quando estiver pronto

Rodar:  uvicorn app.api_rest:app --reload --port 8000
Docs:   http://localhost:8000/docs
"""
import time
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.modelo import carregar_modelo
from app.fila import enfileirar

app = FastAPI(title="Servico de Inferencia - C1.A2", version="0.1.0")

modelo = None


class Entrada(BaseModel):
    texto: str


@app.on_event("startup")
def _subir():
    """Carrega o modelo UMA vez. Este e o ponto-chave da Aula 6."""
    global modelo
    inicio = time.time()
    modelo = carregar_modelo()
    print(f"[startup] modelo carregado em {time.time() - inicio:.3f}s")


@app.get("/saude")
def saude():
    return {"status": "ok", "modelo_carregado": modelo is not None}


@app.post("/predict-sync")
def predict_sync(entrada: Entrada):
    """Inferencia SINCRONA: o cliente espera a resposta. Lab da Aula 6."""
    if not entrada.texto.strip():
        raise HTTPException(status_code=400, detail="texto vazio")
    inicio = time.time()
    resultado = modelo.prever(entrada.texto)
    resultado["tempo_ms"] = round((time.time() - inicio) * 1000, 2)
    return resultado


# ------------------------------------------------------------------
# TAREFA 1 - submissao assincrona
# ------------------------------------------------------------------
@app.post("/predict", status_code=202)
def predict(entrada: Entrada):
     """Deve enfileirar a tarefa e devolver {"id": ...} SEM esperar."""
     if not entrada.texto.strip():
         raise HTTPException(status_code=400, detail="texto vazio")

     # Gera um ID único para a tarefa
     tarefa_id = str(uuid.uuid4())

     # Enfileira no broker sem precessar a IA por agora
     enfileirar(tarefa_id, entrada.texto)

     # Retorna imediatamente com o ID e status HTTP 202
     return {"id": tarefa_id}


# ------------------------------------------------------------------
# TAREFA 2 - consulta do resultado
# ------------------------------------------------------------------
# @app.get("/resultado/{tarefa_id}")
# def resultado(tarefa_id: str):
#     """Deve devolver o resultado; 404 se o id nao existir."""
#     # DICA: use app.fila.buscar_resultado(tarefa_id)
#     raise NotImplementedError("implemente a consulta de resultado")
