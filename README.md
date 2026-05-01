
# How to Use

En cualquier proyecto git:

```sh
export GEMINI_API_KEY=tu_key
```
o

```
$env:GEMINI_API_KEY=""
```

Se requiere tener instalado Python version 3.13 o superior y ser la version activa. Para ello, en Windows debes ejecutar el siguiente comando en `Power Shell` 
```
winget install Python.Python.3.14
```

Luego se debe instalar el Wheel a través del siguiente comando:

```
python -m pip install https://github.com/ianache/llmwikidoc/releases/download/v0.1.0/llmwikidoc-0.1.0-py3-none-any.whl
```

> Alternativa: descargar el ejecutable para Windows

```
llmwikidoc init       # instala hook + crea wiki/
git commit -m "..."   # → hook → llmwikidoc ingest → wiki actualizada
llmwikidoc query "¿qué hace UserService?"
llmwikidoc status
```

El ejecutable llmwikidoc.exe existe dentro del .venv del proyecto, pero no está en el PATH del sistema. Hay dos opciones:

1. Opción A — Instalar globalmente con uv (recomendado)

```sh
uv tool install D:/01-CROSSNET/01-PROJECTS/08-llmwikidoc
```

2. Opción B — Usar siempre uv run desde el directorio del proyecto

```sh
uv run llmwikidoc init
```

3. Opción C — Añadir el venv al PATH temporalmente

```sh
export PATH="D:/01-CROSSNET/01-PROJECTS/08-llmwikidoc/.venv/Scripts:$PATH"
```
