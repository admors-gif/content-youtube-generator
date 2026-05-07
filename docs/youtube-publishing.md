# Publicación Segura En YouTube

Content Factory publica por OAuth, nunca por contraseña. El flujo recomendado
para v1 es subir como privado, revisar en YouTube Studio y programar solo cuando
el usuario elige fecha.

## Variables De Entorno

Backend:

- `YOUTUBE_OAUTH_CLIENT_ID`
- `YOUTUBE_OAUTH_CLIENT_SECRET`
- `YOUTUBE_OAUTH_REDIRECT_URI`
- `CONTENT_FACTORY_YOUTUBE_STATE_SECRET`
- `CONTENT_FACTORY_YOUTUBE_TOKEN_SECRET`
- `CONTENT_FACTORY_WEB_URL`

`YOUTUBE_OAUTH_REDIRECT_URI` debe apuntar al backend:

```text
https://api.valtyk.com/youtube/oauth/callback
```

## Flujo

1. El usuario abre un proyecto completado y pulsa `Publicar en YouTube`.
2. Si no hay canal conectado, Content Factory llama `/youtube/oauth/start`.
3. Google devuelve al backend en `/youtube/oauth/callback`.
4. El backend guarda el canal y el refresh token encriptado en Firestore.
5. El usuario revisa título, descripción, tags, miniatura y programación.
6. El backend crea un job en `youtubePublishJobs` y sube el video como privado.
7. Si hay fecha, se envía `publishAt` y se mantiene `privacyStatus=private`.

## n8n

n8n es útil como capa operacional después del upload:

- avisar que un video quedó listo;
- registrar calendario editorial;
- crear tareas de revisión;
- enviar emails o mensajes internos;
- capturar métricas y alimentar CRM.

No es ideal como motor principal para subir videos grandes, porque el upload
resumable, los reintentos, tokens y archivos de 200MB+ son más confiables desde
el backend propio.

## Referencias

- Upload de video: https://developers.google.com/youtube/v3/docs/videos/insert
- Programación: https://developers.google.com/youtube/v3/docs/videos
- Miniaturas: https://developers.google.com/youtube/v3/docs/thumbnails/set
- Cuotas: https://developers.google.com/youtube/v3/determine_quota_cost
