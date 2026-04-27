# Content Factory - Tu Dosis Diaria

## Proyecto
Pipeline automatizado de generación de videos para YouTube.

## Setup
```bash
pip install -r requirements.txt
```

## Estructura
```
scripts/     - Pipeline de generación
prompts/     - System prompts para cada fase
output/      - Archivos generados (scripts, audio, clips, final)
config/      - Configuración del proyecto
n8n/         - Workflows de n8n exportados
```

## Seguridad
- Las API keys están en `.env` (NUNCA commitear)
- Regenerar keys si se exponen accidentalmente
