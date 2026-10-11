# Contrato de dados: sgmaforms ↔ sgm-app

Este arquivo documenta a dependência estrutural entre dois repositórios
que NÃO compartilham código, apenas uma planilha Google Sheets em comum.

- `sgmaforms/app.py` — formulário público, ESCREVE na aba `CADASTROS`.
- `sgm-app/app.py` — painel administrativo, LÊ e ESCREVE (atualiza o `STATUS`)
  na aba `CADASTROS`; além disso é o único dono da aba de dados principal e da
  aba `SEQUENCIA`.

Não existe checagem automática entre os dois. Se você alterar qualquer
item abaixo em um dos repositórios, precisa replicar manualmente no outro,
ou o painel administrativo vai falhar (com erro visível) ou passar a
ignorar solicitações silenciosamente (sem erro nenhum — pior caso).

A planilha tem **três abas com função definida**. Qualquer outra aba é ignorada pelo código.

---

## 1. Aba de dados principal (ordens de serviço)

- **Deve ser a PRIMEIRA aba da planilha** (índice 0), com qualquer nome.
  O código a seleciona pela posição, não pelo nome. **Reordenar as abas quebra o app**
  (ele passaria a ler/gravar em outra aba).
- Uma linha por serviço. Uma OS com vários serviços ocupa várias linhas com o mesmo número em `OS`.
- Cabeçalho na linha 1, com estes nomes EXATOS (acentos, espaços e parênteses incluídos):

| Coluna               | Observação                                              |
|----------------------|---------------------------------------------------------|
| `OS`                 | número da OS (vem da aba `SEQUENCIA`)                  |
| `DATA`               | gravada como texto `AAAA-MM-DD` nas OS novas            |
| `MARCA`              |                                                         |
| `MODELO`             |                                                         |
| `KM ATUAL`           | numérico                                                |
| `PROPRIETÁRIO`       |                                                         |
| `PLACA`              |                                                         |
| `ANO DE FABRICAÇÃO`  | numérico                                                |
| `CHASSI`             |                                                         |
| `SERVIÇO`            |                                                         |
| `DEFEITO`            |                                                         |
| `DIAGNÓSTICO`        |                                                         |
| `SERVIÇO EXECUTADO`  |                                                         |
| `CUSTO (R$)`         | numérico                                                |
| `PAGAMENTO (R$)`     | numérico                                                |
| `MECÂNICO`           | deve coincidir com os nomes do app (`LISTA_MECANICOS`)  |
| `EDITADO_POR`        | preenchida só ao editar uma OS                          |
| `DATA_EDICAO`        | preenchida só ao editar uma OS                          |

### Como o app grava nesta aba

| Operação              | Como grava                                                                 | Risco |
|-----------------------|-----------------------------------------------------------------------------|-------|
| **Registrar OS** (novo)| **Append** de linhas no fim, alinhado pelo cabeçalho (valores `RAW`)       | Baixo. Não reescreve nada. Se uma coluna de `OS` a `MECÂNICO` faltar no cabeçalho, a gravação é recusada com erro explícito. |
| **Editar OS**         | Localiza o **nº real da linha** na planilha, confere se ela continua igual à de quando a edição foi aberta e grava **só as células alteradas** (mais `EDITADO_POR` e `DATA_EDICAO`) numa única chamada | Baixo. Se outra pessoa alterou a mesma linha, a edição é recusada e nada é gravado. Resta uma janela de milissegundos entre a conferência e a gravação. |

---

## 2. Aba `SEQUENCIA` (reserva de números de OS)

Garante número de OS único mesmo com usuários salvando ao mesmo tempo: cada reserva é um
*append* e o Google Sheets devolve a linha atribuída; o número da OS é derivado dessa linha.

| Célula / linha | Conteúdo                                                        |
|----------------|------------------------------------------------------------------|
| `A1:C1`        | `OS`, `RESERVADO_EM`, `RESERVADO_POR`                            |
| `A2`           | **semente**: último número de OS já usado (use `0` em planilha nova) |
| linha `N ≥ 3`  | uma reserva. Número da OS = `A2 + (N − 2)`                        |

Regras (quebrar qualquer uma gera números repetidos ou erro ao salvar):

1. **Nunca edite `A2`** depois que o sistema estiver em uso.
2. **Nunca apague, ordene ou insira linhas** no meio da aba.
3. Se uma OS não for salva depois de reservada, o número fica "queimado" (buraco na sequência). É esperado.
4. Se a aba não existir ou `A2` não for um número, o app recusa salvar e mostra o motivo.
5. Se o número reservado já existir na aba de dados (semente desatualizada), o app recusa salvar e não grava nada.

---

## 3. Aba `CADASTROS` (solicitações de clientes)

- Constante correspondente no `sgm-app/app.py`: `WORKSHEET_SOLICITACOES`
- Constante correspondente no `sgmaforms/app.py`: usada diretamente como
  string literal em `conn.read(worksheet="CADASTROS", ...)` e
  `conn.update(worksheet="CADASTROS", ...)`.

### Colunas (ordem e nomes EXATOS, incluindo acentos e espaços)

| Coluna                  | Preenchido por      | Lido por (sgm-app)                          |
|--------------------------|---------------------|----------------------------------------------|
| `NOME`                  | sgmaforms           | `row['NOME']` → pré-preenche PROPRIETÁRIO    |
| `TELEFONE`              | sgmaforms           | `row['TELEFONE']` (exibição)                  |
| `PLACA`                 | sgmaforms           | `row['PLACA']` → pré-preenche PLACA          |
| `DEFEITO RELATADO`      | sgmaforms           | `row['DEFEITO RELATADO']` → pré-preenche DIAGNÓSTICO |
| `DATA DA SOLICITAÇÃO`   | sgmaforms (automático) | exibição apenas                           |
| `STATUS`                | ambos (ver abaixo)  | filtro de pendentes, atualização de status    |

### Valores válidos de `STATUS`

| Valor        | Definido por                              | Significado                          |
|--------------|--------------------------------------------|----------------------------------------|
| `pendente`   | sgmaforms, no momento do envio             | Aguardando análise do admin           |
| `aceita`     | sgm-app, botão "ACEITAR E PREENCHER O.S"   | Admin aceitou, ainda preenchendo a OS |
| `recusada`   | sgm-app, botão "RECUSAR"                   | Admin recusou o pedido                |

**Atenção:** o filtro de pendentes no `sgm-app` compara a string em
minúsculas (`.str.lower() == "pendente"`), então variações de
maiúsculo/minúsculo não quebram — mas mudar a palavra em si (ex:
`"aguardando"`) quebra o filtro silenciosamente.

---

## Riscos e limitações conhecidos (não resolvidos)

### Rastreabilidade
Não há vínculo automático entre uma solicitação aceita e o número de OS
gerado depois. O status muda para `aceita`, mas não fica registrado qual
OS resultou daquele pedido. Rastreabilidade completa exigiria alterar o
fluxo de salvamento de OS para escrever de volta na aba `CADASTROS`.

### Concorrência em `CADASTROS`
Pelas regras acima, tanto o `sgmaforms` quanto o painel gravam em `CADASTROS`
com `conn.update(...)`, que **reescreve a aba inteira** (apaga e escreve).
Consequências prováveis, a **confirmar no código do `sgmaforms`**:

- duas solicitações enviadas ao mesmo tempo podem se sobrescrever (uma se perde);
- uma solicitação enviada enquanto o admin aceita/recusa outra pode desfazer a mudança de `STATUS`;
- se a leitura falhar no momento do envio e o código tratar isso como "aba vazia",
  a aba inteira pode ser apagada.

### Dados pessoais
`CADASTROS` guarda nome, telefone e placa de pessoas que preencheram um formulário público
na internet. Isso é dado pessoal (LGPD): a oficina é a responsável pelo tratamento.
Não há proteção contra envios em massa (spam) documentada.

---

## Antes de alterar qualquer coisa na estrutura acima

1. Decida a mudança nos dois repositórios ao mesmo tempo, não em sessões separadas.
2. Atualize este arquivo.
3. Teste o fluxo completo numa **cópia** da planilha:
   formulário → aba `CADASTROS` → painel admin → aceitar/recusar → registrar OS (append + `SEQUENCIA`) → editar OS.
