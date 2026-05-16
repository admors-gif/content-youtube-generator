# Content Factory PWA + App Nativa

## Objetivo

Content Factory ahora tiene una base movil en dos capas:

- **PWA instalable** desde navegador, usando Vercel como hosting principal.
- **Capacitor** para empaquetar la misma experiencia como app Android/iOS con notificaciones y deep links.

La v1 es interna/admin, online-first, y no cachea contenido privado de proyectos.

## PWA

Archivos principales:

- `web/app/manifest.js`: manifiesto instalable.
- `web/app/sw.js/route.js`: service worker con cache segura y Firebase Messaging.
- `web/app/offline/page.js`: fallback cuando no hay conexion.
- `web/components/PwaRuntime.js`: registro de service worker, prompt de instalacion y avisos.

Variables:

```env
NEXT_PUBLIC_PWA_ENABLED=true
NEXT_PUBLIC_FIREBASE_VAPID_KEY=...
CONTENT_FACTORY_NOTIFICATIONS_ENABLED=true
```

Comandos:

```bash
cd web
npm run pwa:assets
npm run pwa:audit
npm run lint
npm run build
```

## Notificaciones

Endpoints backend:

- `POST /notifications/register`
- `POST /notifications/unregister`
- `POST /notifications/test` admin-only

Firestore:

- `users/{uid}/notificationTokens/{tokenHash}`
- `notificationEvents/{eventId}`

Eventos actuales:

- Guion listo para revisar.
- Produccion completada.
- Produccion detenida/error.
- Shorts listos.
- Miniaturas listas.

Los errores de FCM no bloquean produccion. Tokens obsoletos se marcan inactivos.

## Capacitor

Configuracion:

- `web/capacitor.config.ts`
- App id: `com.valtyk.contentfactory`
- App name: `Content Factory`
- URL remota default: `https://content-youtube-generator.vercel.app`
- Shell local fallback: `web/mobile-shell/index.html`

Comandos:

```bash
cd web
npm run mobile:sync
npm run mobile:add:android
npm run mobile:android
```

Android ya queda generado en `web/android`.

iOS queda generado en `web/ios`, pero requiere Mac/Xcode para compilar, firmar y subir a TestFlight.

## Deep Links

Esquema nativo:

- `contentfactory://dashboard`
- `contentfactory://project/{projectId}`

Universal/app links previstos:

- `https://content-youtube-generator.vercel.app/dashboard/project/{projectId}`

Para Android App Links reales falta publicar `/.well-known/assetlinks.json` con el SHA-256 del certificado final.
Para iOS Universal Links reales falta `apple-app-site-association` y configurar Associated Domains en Xcode.

## Pendientes De Tiendas

Android:

- Configurar `google-services.json` si se usara FCM nativo en Play.
- Generar keystore de release.
- Obtener SHA-256 de firma.
- Crear AAB release.
- Probar push foreground/background en dispositivo real.

iOS:

- Abrir `web/ios/App/App.xcworkspace` en Xcode.
- Configurar Team, Bundle ID y APNs.
- Activar Push Notifications y Associated Domains.
- Probar en dispositivo fisico y TestFlight.

## Criterios De Aceptacion

- Chrome permite instalar la PWA.
- Safari iOS muestra instrucciones manuales.
- `/offline` aparece al navegar sin conexion.
- Dashboard movil usa top bar + drawer.
- Se puede crear y monitorear un proyecto desde celular.
- Un proyecto terminado dispara notificacion si el usuario activo avisos.
- Android abre la app y carga Content Factory desde produccion.
