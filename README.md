# sheets-chatclipy-webhook

Sempre que uma linha nova é criada na planilha (via Google Forms), dispara o
envio de um template do WhatsApp oficial via API pública do Chatclipy
(`POST /public-api/templates/send`), usando `Nome`, `E-mail` e `WhatsApp` da
linha.

## Arquitetura

```
Google Forms -> grava linha no Sheets
             -> Apps Script (onFormSubmit) chama o webhook
             -> serviço Python (Docker) relê a linha via Sheets API
             -> normaliza telefone, checa se já foi enviado
             -> POST /public-api/templates/send no Chatclipy
```

## Estrutura da planilha esperada

| Coluna | Conteúdo |
|---|---|
| A | Timestamp (gerado pelo Forms) |
| B | Nome -> vira `contact.name` e `parameters[0]` (`{{1}}` do template) |
| C | E-mail -> vira `contact.email` |
| D | WhatsApp -> vira `contact.number` (normalizado) |
| E-G | Outros campos do formulário (não usados no envio) |

## Setup

### 1. Service account do Google

1. Crie um service account no Google Cloud com acesso à Sheets API.
2. Baixe o JSON da chave e salve em `credentials/service-account.json`
   (esse arquivo é ignorado pelo git, nunca commitar).
3. Compartilhe a planilha com o e-mail do service account (permissão de
   leitura já basta).

### 2. Variáveis de ambiente

```bash
cp .env.example .env
```

Preencha:
- `CHATCLIPY_API_TOKEN`: o `apiToken` da empresa (Configurações > Tokens de
  Aplicações no painel do Chatclipy).
- `CHATCLIPY_WHATSAPP_ID`: PK interna da conexão WhatsApp oficial que vai
  disparar (mesmo valor pra todas as linhas).
- `CHATCLIPY_TEMPLATE_NAME`: nome do template aprovado na Meta.
- `GOOGLE_SHEETS_SPREADSHEET_ID`: o ID da planilha (parte da URL entre
  `/d/` e `/edit`).
- `WEBHOOK_SHARED_SECRET`: gere um valor aleatório forte (ex:
  `openssl rand -hex 32`) — vai ser o mesmo valor usado no Apps Script.

### 3. Subir o container

```bash
docker compose up --build -d
docker compose logs -f
```

O serviço expõe:
- `GET /healthz` — checagem de saúde.
- `POST /sheet-webhook` — recebido pelo Apps Script.

Ele precisa estar acessível publicamente via HTTPS (o Google chama de fora),
então coloque atrás do reverse proxy/ingress/domínio que vocês já usam.

### 4. Apps Script

1. Na planilha, abra **Extensões > Apps Script**.
2. Cole o conteúdo de `apps_script/Code.gs`.
3. Em **Configurações do projeto > Propriedades do script**, adicione:
   - `WEBHOOK_URL`: URL pública do endpoint, ex:
     `https://seu-dominio/sheet-webhook`
   - `WEBHOOK_SECRET`: o mesmo valor de `WEBHOOK_SHARED_SECRET` do `.env`
4. Em **Acionadores** (ícone de relógio), adicione um gatilho instalável:
   - Função: `onFormSubmit`
   - Origem do evento: Do Google Sheets
   - Tipo de evento: Ao enviar o formulário
5. Autorize o script quando solicitado.

## Idempotência

O estado de "já enviado" fica num SQLite (`STATE_DB_PATH`, montado como
volume em `./data`), indexado pelo número normalizado. Isso evita reenviar o
template se a mesma linha for editada de novo ou se o mesmo número aparecer
em duas linhas diferentes (submissões duplicadas do formulário).

## Validações

- Linhas sem `Nome` ou `WhatsApp` são ignoradas (`incomplete_row`).
- Números que não têm 10-13 dígitos após normalização são ignorados
  (`invalid_phone`) — cobre casos como `#ERROR!` digitado no campo.
- Números são normalizados removendo tudo que não é dígito e prefixando
  `55` quando faltar o código do país.

## Testando localmente sem esperar o Forms

```bash
curl -X POST http://localhost:8000/sheet-webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: <o valor de WEBHOOK_SHARED_SECRET>" \
  -d '{"sheetName": "Respostas ao formulário 1", "row": 5}'
```
