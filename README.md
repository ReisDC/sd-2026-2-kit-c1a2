# Serviço de Inferência Distribuído — C1.A2

**Sistemas Distribuídos e Computação em Nuvem · FAESA · 2026/2**

Serviço que recebe um texto e devolve uma classificação de sentimento
(positivo/negativo), exposto por **duas interfaces de comunicação** (REST e
gRPC) e processado de forma **assíncrona** por um worker consumindo uma fila
Redis — para que o cliente nunca fique bloqueado esperando a inferência.

## Arquitetura

```
                         ┌──────────────┐
        HTTP/JSON        │              │
   ──────────────────►   │  api_rest.py │──┐
   POST /predict          (FastAPI)      │  │ enfileira
   GET  /resultado/{id}  │              │  │ tarefa
                         └──────────────┘  │
                                            ▼
                                     ┌─────────────┐
        gRPC                        │    Redis    │
   ──────────────────►   ┌──────────┤  (fila +    │
   Prever / PreverLote    │          │  resultados)│
                         │          └─────────────┘
              ┌──────────▼───┐             ▲
              │servidor_grpc │             │ grava
              │   .py        │             │ resultado
              └──────┬───────┘             │
                     │            ┌────────┴───────┐
                     └───────────►│   worker.py    │
                    carrega modelo│ (consome fila, │
                    uma vez       │ retry + DLQ)   │
                                  └────────────────┘
```

- **`app/api_rest.py`** — interface REST (FastAPI). Recebe o texto, valida,
  enfileira a tarefa no Redis e devolve o `id` imediatamente (HTTP 202), sem
  esperar a inferência. Também expõe `/predict-sync` (chamada síncrona direta
  ao modelo, sem fila) e `/saude`.
- **`app/servidor_grpc.py`** — interface gRPC equivalente, com os métodos
  `Prever` (um texto) e `PreverLote` (vários textos em uma chamada). Chama o
  modelo diretamente, sem passar pela fila — é uma via síncrona alternativa
  ao REST.
- **`app/worker.py`** — processo separado que consome a fila Redis, roda a
  inferência e grava o resultado. Em caso de falha, tenta novamente até 3
  vezes; se ainda assim falhar, move a tarefa para uma fila de descarte
  (`tarefas:descarte`) e marca o resultado como erro.
- **`app/fila.py`** — encapsula o acesso ao Redis (enfileirar tarefa, ler
  próxima tarefa, gravar/consultar resultado).
- **`app/modelo.py`** — carrega/treina o classificador de sentimento uma
  única vez por processo (na subida do REST, do worker e do gRPC), nunca a
  cada requisição.

Tanto o REST quanto o gRPC usam a mesma instância de `ModeloSentimento`
(mesmo pipeline treinado salvo em `app/modelo.joblib`), então os dois
devolvem o mesmo resultado para o mesmo texto.

### Por que fila em vez de chamada direta no REST?

O `POST /predict` não pode travar o cliente esperando a inferência (que pode
demorar, enfileirar picos de carga, etc.). Por isso ele só grava a tarefa no
Redis e devolve o `id` na hora; quem processa de fato é o `worker.py`,
rodando em outro processo, que pode ser escalado independentemente do
serviço REST.

## Como executar do zero

```bash
# 1. Clone o repositório e entre na pasta
git clone https://github.com/ReisDC/sd-2026-2-kit-c1a2.git
cd sd-2026-2-kit-c1a2

# 2. Crie e ative o ambiente virtual (requer Python 3.12 - veja o FAQ abaixo)
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Suba o Redis (fila) em um terminal
docker compose up -d

# 5. Gere os stubs do gRPC (necessário antes de rodar o servidor gRPC)
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/inferencia.proto
# (ou: bash scripts/gerar_stubs.sh)

# 6. Em um terminal, rode a API REST
uvicorn app.api_rest:app --reload --port 8000
# docs interativas em http://localhost:8000/docs

# 7. Em outro terminal, rode o worker (obrigatório para o fluxo assíncrono)
python -m app.worker

# 8. Em outro terminal, rode o servidor gRPC
python -m app.servidor_grpc
```

Encerre cada processo com `Ctrl+C`. Para derrubar o Redis: `docker compose down`.

### FAQ: "pip install" travou compilando pacote (Linux, macOS ou Windows)

Este projeto foi testado com **Python 3.12**. Se o `python` do seu sistema for
outra versão (ex. 3.13, comum em distros Linux recentes, mas pode acontecer
em qualquer sistema operacional), o `pip install` pode não encontrar wheel
pré-compilado para `scikit-learn`/`numpy` naquela versão/plataforma e tentar
compilar tudo do zero a partir do código-fonte — o que é lento e pode falhar
por falta de compilador/headers (em qualquer SO).

Se você não tem Python 3.12 instalado (ou não sabe qual versão tem), use o
[uv](https://docs.astral.sh/uv/) para baixar o 3.12 e criar o venv com ele,
sem precisar instalar nada manualmente no sistema:

```bash
# instala o uv, se ainda não tiver
# Linux/macOS:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# baixa o Python 3.12 (isolado, não mexe no python do sistema)
uv python install 3.12

# cria o venv já usando o 3.12
uv venv --python 3.12 venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# instala as dependências (mais rápido que pip também)
uv pip install -r requirements.txt
```

O restante dos passos (Redis, stubs, rodar os serviços) é o mesmo, nas duas
plataformas.

## Testando

### REST — fluxo assíncrono (fila)

```bash
# envia a tarefa, recebe o id na hora (202 Accepted)
curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"texto": "o atendimento foi otimo"}'
# -> {"id": "..."}

# consulta o resultado pelo id (pode responder 404 se ainda não existir/for inválido,
# ou o status "na_fila" enquanto o worker não processou)
curl http://localhost:8000/resultado/<id>
```

### REST — fluxo síncrono (sem fila, direto no modelo)

```bash
curl -X POST http://localhost:8000/predict-sync \
     -H "Content-Type: application/json" \
     -d '{"texto": "o atendimento foi otimo"}'
```

Ou use o cliente pronto:

```bash
python exemplos/cliente_rest.py "o atendimento foi otimo"
```

### gRPC

Use qualquer cliente gRPC (ex. [grpcurl](https://github.com/fullstorydev/grpcurl))
ou um cliente Python simples com os stubs gerados no passo 5:

```python
import grpc, inferencia_pb2, inferencia_pb2_grpc

canal = grpc.insecure_channel("localhost:50051")
stub = inferencia_pb2_grpc.InferenciaStub(canal)

print(stub.Prever(inferencia_pb2.PedidoPrever(texto="muito bom")))
print(stub.PreverLote(inferencia_pb2.PedidoLote(textos=["muito bom", "pessimo"])))
```

## Resiliência

- **Retentativas**: se a inferência falhar no worker, a tarefa volta para o
  fim da fila e é reprocessada (até 3 tentativas no total).
- **Dead-letter**: após a 3ª falha consecutiva, a tarefa é movida para a fila
  `tarefas:descarte` no Redis e o resultado consultável via
  `GET /resultado/{id}` fica com `"status": "erro"`, preservando o motivo da
  falha.
- **Validação de entrada**: texto vazio é rejeitado com `400` tanto em
  `/predict` quanto em `/predict-sync`.

## Logging

Todos os serviços (REST, worker e gRPC) registram cada requisição/tarefa
processada com `id`, tamanho da entrada (em caracteres/bytes) e tempo de
resposta:

- **REST**: um middleware único loga toda requisição HTTP (`id`, método,
  rota, tamanho do corpo, status e tempo de resposta) e devolve o `id` também
  no header `X-Request-ID` da resposta.
- **Worker**: loga cada tentativa de processamento (`id` da tarefa, tamanho
  do texto, número da tentativa) e o desfecho (concluída, reenfileirada ou
  enviada para descarte), com o tempo de resposta quando aplicável.
- **gRPC**: cada chamada (`Prever`/`PreverLote`) gera um `id` interno e loga
  tamanho da entrada e tempo de resposta.

## Estrutura do projeto

```
sd-2026-2-kit-c1a2/
├── app/
│   ├── modelo.py           # classificador de sentimento (treina/carrega uma vez)
│   ├── fila.py             # auxiliares de fila e resultados (Redis)
│   ├── api_rest.py         # interface REST (FastAPI) + log de requisições
│   ├── worker.py           # consumidor da fila: inferência, retry e dead-letter
│   └── servidor_grpc.py    # interface gRPC (Prever e PreverLote)
├── proto/inferencia.proto  # contrato gRPC
├── exemplos/cliente_rest.py
├── scripts/gerar_stubs.*   # atalhos para gerar os stubs do gRPC
├── docker-compose.yml      # sobe o Redis
└── requirements.txt
```

## Requisitos

- Python 3.12+
- Docker (para o Redis via `docker-compose.yml`)

Tudo roda 100% offline — o modelo é treinado localmente na primeira execução
e salvo em `app/modelo.joblib`.
