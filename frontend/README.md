# Localer frontend

React map interface for Localer. Project-level setup, environment variables,
data-source behavior, and production notes live in the root
[`README.md`](../README.md).

```bash
cp .env.example .env
npx -y yarn@1.22.22 install --frozen-lockfile
npx -y yarn@1.22.22 start
```

Use `npm run build` for a production bundle. When the frontend and API share
an origin, omit `REACT_APP_BACKEND_URL`; requests will use `/api`.
