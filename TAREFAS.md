# TAREFAS - Trabalho C1.A2

Marque conforme for concluindo. Cada item aponta o arquivo e a aula de referencia.

## Nucleo obrigatorio (e o que define a nota)

- [X] **1. Submissao assincrona** - `app/api_rest.py`
      Criar `POST /predict` que enfileira a tarefa e devolve `{"id": ...}` com status 202,
      SEM esperar a inferencia terminar. (Aula 8)

- [ ] **2. Consulta de resultado** - `app/api_rest.py`
      Criar `GET /resultado/{id}` que devolve o resultado, ou 404 se o id nao existir. (Aula 5)

- [ ] **3. Worker grava o resultado** - `app/worker.py`
      Substituir o `raise NotImplementedError` por `fila.guardar_resultado(...)`. (Aula 8)

- [ ] **4. Metodo gRPC PreverLote** - `app/servidor_grpc.py` + `proto/inferencia.proto`
      Implementar o metodo que recebe varios textos e devolve varias respostas. (Aula 4)

- [ ] **5. Tratamento de erro** - `app/worker.py`
      Retentativa em caso de falha e, apos 3 tentativas, mandar para uma fila de
      descarte (dead-letter). (Aula 8)

- [ ] **6. Log de requisicoes** - todos os servicos
      Registrar cada requisicao recebida (id, tamanho da entrada, tempo de resposta).

- [ ] **7. README proprio**
      Reescrever o README explicando SUA arquitetura e como executar do zero.

## Extensoes opcionais (nao valem nota extra)

- [ ] Subir 2+ workers e demonstrar a divisao de carga
- [ ] Cache de resultados para textos repetidos
- [ ] Medir e expor a latencia media das inferencias
- [ ] Processamento em lote pela interface REST

## Antes de entregar

- [ ] Apague a pasta, clone do zero e siga o SEU README - funciona?
- [ ] As duas interfaces (REST e gRPC) devolvem o mesmo resultado para o mesmo texto?
- [ ] O modelo e carregado UMA vez (e nao a cada requisicao)?
- [ ] Ha commits ao longo do periodo (e nao um unico commit no final)?
