
# How to Use

En cualquier proyecto git:

```sh
export GEMINI_API_KEY=tu_key
```
o

```
$env:GEMINI_API_KEY=""

```
llmwikidoc init       # instala hook + crea wiki/
git commit -m "..."   # → hook → llmwikidoc ingest → wiki actualizada
llmwikidoc query "¿qué hace UserService?"
llmwikidoc status
```