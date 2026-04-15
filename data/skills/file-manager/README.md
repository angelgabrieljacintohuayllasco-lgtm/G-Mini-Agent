# file-manager

Skill bundled de ejemplo para el runtime de skills de G-Mini.

## Tool: `inspect_text_file`

Entrada JSON:

```json
{
  "path": "C:\\Users\\PC\\Desktop\\nota.txt",
  "max_preview_chars": 240
}
```

O tambien:

```json
{
  "text": "contenido inline"
}
```

Salida:
- `source`: `path` o `inline`
- `path`: ruta resuelta si aplica
- `exists`: si el archivo existia
- `chars`, `words`, `lines`
- `preview`
