# sheets-chatclipy-webhook

Sempre que um sistema externo grava uma linha nova na planilha, dispara o
envio de um template do WhatsApp oficial via API pública do Chatclipy
(`POST /public-api/templates/send`). O nome do template e quais campos da
linha viram parâmetros (`{{1}}`, `{{2}}`, ...) são configuráveis a qualquer
momento pela tela `/admin`, sem precisar reiniciar o container.

## Arquitetura

```
Sistema externo -> POST no Web App do Apps Script (função doPost já existente)
                -> Apps Script grava a linha (appendRow) e chama o webhook
                   com nome/email/whatsapp/faturamento/perfil/decisao
                -> serviço Python (Docker) normaliza o telefone,
                   checa se já foi enviado, monta os parâmetros conforme
                   configurado em /admin
                -> POST /public-api/templates/send no Chatclipy
```

A planilha já é alimentada por um `doPost(e)` no Apps Script (Web App) que
outro sistema chama via HTTP. Gatilhos como `onEdit`/`onChange`/
`onFormSubmit` **não disparam de forma confiável quando a escrita vem de
fora via API** — por isso o disparo do webhook é feito diretamente dentro
desse `doPost`, logo após o `appendRow`, e não por um gatilho separado. Não
há chamada à Google Sheets API pelo lado do Python: o próprio Apps Script já
tem os valores em mãos (veio no corpo do POST que ele recebeu) e manda tudo
no corpo do webhook — não precisa service account nem credenciais do Google.

## Estrutura da planilha

| Coluna | Conteúdo |
|---|---|
| A | Data de envio |
| B | Nome -> vira `contact.name` (sempre) e opcionalmente parâmetro do template |
| C | E-mail -> vira `contact.email` (sempre) e opcionalmente parâmetro do template |
| D | WhatsApp -> vira `contact.number` (normalizado, sempre obrigatório) |
| E | Faturamento -> disponível como parâmetro do template |
| F | Perfil -> disponível como parâmetro do template |
| G | Decisão -> disponível como parâmetro do template |

`Nome` e `WhatsApp` são sempre obrigatórios pra disparar (linha incompleta é
ignorada). Quais desses 6 campos entram como `parameters` do template — e em
qual ordem — é definido na tela `/admin`, não no código.

## Setup

### 1. Variáveis de ambiente

```bash
cp .env.example .env
```

Preencha:
- `CHATCLIPY_API_TOKEN`: o `apiToken` da empresa (Configurações > Tokens de
  Aplicações no painel do Chatclipy).
- `CHATCLIPY_WHATSAPP_ID`: PK interna da conexão WhatsApp oficial que vai
  disparar (mesmo valor pra todas as linhas).
- `CHATCLIPY_TEMPLATE_NAME`: nome do template aprovado na Meta (valor
  inicial — depois pode ser trocado em `/admin` sem reiniciar nada).
- `WEBHOOK_SHARED_SECRET`: gere um valor aleatório forte (ex:
  `openssl rand -hex 32`) — vai ser o mesmo valor usado no Apps Script.
- `ADMIN_USERNAME` / `ADMIN_PASSWORD`: credenciais de acesso à tela
  `/admin` (HTTP Basic Auth). Gere uma senha forte.

### 2. Subir o container

```bash
docker compose up --build -d
docker compose logs -f
```

O serviço expõe:
- `GET /healthz` — checagem de saúde.
- `POST /sheet-webhook` — chamado pelo Apps Script.
- `GET`/`POST /admin` — tela pra trocar o nome do template e os parâmetros
  (protegida por usuário/senha).

Ele precisa estar acessível publicamente via HTTPS (o Apps Script chama de
fora do Google), então coloque atrás do reverse proxy/ingress/domínio que
vocês já usam.

## Trocando o template e os parâmetros

Acesse `https://<seu-domínio>/admin` (usuário/senha de `ADMIN_USERNAME`/
`ADMIN_PASSWORD`). Lá dá pra:
- Trocar o nome do template a qualquer momento.
- Escolher quais campos (`Nome`, `E-mail`, `WhatsApp`, `Faturamento`,
  `Perfil`, `Decisão`) preenchem `{{1}}`, `{{2}}`, ... do template, e em
  qual ordem — adicionando ou removendo linhas de parâmetro na própria
  página.

A configuração fica salva no mesmo SQLite do estado de envio (`STATE_DB_PATH`),
então sobrevive a reinícios do container.

### 3. Apps Script (editar o `doPost` existente)

1. Na planilha, abra **Extensões > Apps Script** — lá já deve estar o
   `doPost(e)` que grava a linha.
2. Adicione a função `sendToWebhook_` e a chamada a ela logo depois do
   `appendRow`, como em `apps_script/Code.gs` (esse arquivo já mostra o
   `doPost` original com a única mudança necessária).
3. Em **Configurações do projeto > Propriedades do script**, adicione:
   - `WEBHOOK_URL`: URL pública do endpoint, ex:
     `https://seu-dominio/sheet-webhook`
   - `WEBHOOK_SECRET`: o mesmo valor de `WEBHOOK_SHARED_SECRET` do `.env`
4. Reimplante o Web App (**Implantar > Gerenciar implantações > Editar >
   Nova versão**) pra a mudança valer pro sistema externo que já chama esse
   endpoint.

Falha ao chamar o webhook não derruba o `doPost` original — a linha é gravada
na planilha independente do resultado do envio do template (só fica
registrado no log do Apps Script).

## Idempotência

O estado de "já enviado" fica num SQLite (`STATE_DB_PATH`, montado como
volume em `./data`), indexado pelo número normalizado. Isso evita reenviar o
template se o mesmo número aparecer em duas linhas diferentes.

## Validações

- Linhas sem `Nome` ou `WhatsApp` são ignoradas (`incomplete_row`).
- Números que não têm 10-13 dígitos após normalização são ignorados
  (`invalid_phone`) — cobre casos como `#ERROR!` digitado no campo.
- Números são normalizados removendo tudo que não é dígito e prefixando
  `55` quando faltar o código do país.

## Testando localmente sem esperar uma chamada real

```bash
curl -X POST http://localhost:8000/sheet-webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: <o valor de WEBHOOK_SHARED_SECRET>" \
  -d '{"row": 5, "nome": "Fulano", "email": "fulano@gmail.com", "whatsapp": "48988888888"}'
```
