This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

Para abrir la interfaz local usando la API existente de Content Factory:

```bash
npm run dev:remote -- --hostname 127.0.0.1 --port 3001
```

Abre [Música](http://localhost:3001/dashboard/music). Este comando establece
`NEXT_PUBLIC_VPS_API_URL=https://api.valtyk.com` para el proceso de desarrollo;
conserva las demás variables y no modifica los archivos de credenciales.
La caché de la PWA se omite durante desarrollo para cargar siempre el código actual.
Los botones de generación siguen usando la configuración y los proveedores de la API.

Para comprobar la caché del service worker: `npm run test:service-worker`.

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.js`. The page auto-updates as you edit the file.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
