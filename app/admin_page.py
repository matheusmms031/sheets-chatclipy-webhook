import html

from .template_config import AVAILABLE_FIELDS

_PAGE = """<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Configuração do template — Chatclipy</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }
  label { display: block; margin-top: 16px; font-weight: 600; }
  input[type=text] { width: 100%; padding: 8px; font-size: 1rem; box-sizing: border-box; }
  .param-row { display: flex; gap: 8px; margin-top: 8px; align-items: center; }
  select { flex: 1; padding: 6px; }
  button { padding: 6px 10px; cursor: pointer; }
  .message { background: #e6ffed; border: 1px solid #34a853; padding: 8px 12px; border-radius: 4px; }
  .message.error { background: #fce8e6; border-color: #d93025; }
  .actions { margin-top: 24px; display: flex; gap: 8px; }
  .hint { color: #666; font-size: 0.9rem; }
</style>
</head>
<body>
  <h1>Configuração do template</h1>
  __MESSAGE__
  <form method="post" action="/admin">
    <label for="template_name">Nome do template (aprovado na Meta)</label>
    <input type="text" id="template_name" name="template_name" value="__TEMPLATE_NAME__" required>

    <label>Parâmetros do template (na ordem: {{1}}, {{2}}, ...)</label>
    <div id="params">__ROWS__</div>
    <div class="actions">
      <button type="button" onclick="addParam()">+ Adicionar parâmetro</button>
    </div>
    <p class="hint">Cada parâmetro escolhido preenche, em ordem, os placeholders do corpo do template aprovado na Meta.</p>

    <div class="actions">
      <button type="submit">Salvar</button>
    </div>
  </form>

  <template id="param-template">__PARAM_ROW_TEMPLATE__</template>
  <script>
    function addParam() {
      var tpl = document.getElementById('param-template').content.cloneNode(true);
      document.getElementById('params').appendChild(tpl);
    }
  </script>
</body>
</html>
"""


def _select_row(selected: str) -> str:
    options = "".join(
        '<option value="{key}"{sel}>{label}</option>'.format(
            key=key,
            sel=" selected" if key == selected else "",
            label=html.escape(label),
        )
        for key, label in AVAILABLE_FIELDS.items()
    )
    return (
        '<div class="param-row">'
        f'<select name="parameters">{options}</select>'
        '<button type="button" onclick="this.parentElement.remove()">Remover</button>'
        "</div>"
    )


def render_admin_page(
    template_name: str, parameters: list[str], message: str = "", is_error: bool = False
) -> str:
    fallback_field = next(iter(AVAILABLE_FIELDS))
    rows_html = "".join(_select_row(p) for p in parameters) or _select_row(fallback_field)
    message_html = ""
    if message:
        css_class = "message error" if is_error else "message"
        message_html = f'<p class="{css_class}">{html.escape(message)}</p>'

    page = _PAGE
    page = page.replace("__TEMPLATE_NAME__", html.escape(template_name))
    page = page.replace("__ROWS__", rows_html)
    page = page.replace("__MESSAGE__", message_html)
    page = page.replace("__PARAM_ROW_TEMPLATE__", _select_row(fallback_field))
    return page
