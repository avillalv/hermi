# Hermi

A collaborative trip planner for iOS and the web. The spec, design kit and build prompts are in `app-buildout/`.

Set up and run (Windows or Linux; needs Node 22.12+, uv, and native PostgreSQL 18, no Docker):

1. Put the `postgres` password in `pgpass.conf` (`%APPDATA%\postgresql\pgpass.conf` on Windows, `~/.pgpass` elsewhere) as `localhost:5432:*:postgres:<password>`.
2. `npm install`, then `npm run doctor` to see what is set and what is missing (it never prints values).
3. `npm run setup` creates `.env` with generated secrets (never overwrites), installs dependencies, runs `db:init`, migrates and seeds when those exist.
4. `npm run dev` serves the API on http://127.0.0.1:8100 and the web app on http://localhost:5173. `npm start` serves a production build instead.
5. `npm run lint`, `npm test`, `npm run test:e2e:smoke` (needs `npm run dev` running).

`npm run db:init` runs `infra/db/bootstrap.sql` on its own; it is safe to repeat. Only `hermi` and `hermi_*` databases are touched.
