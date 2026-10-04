-- infra/db/bootstrap.sql (psql, as postgres). Idempotent: run it again at any time.
-- Spec: 03-database-schema.md section 6.1. Run it with `npm run db:init`.
-- The caller supplies the four passwords (migrate_pw, api_pw, worker_pw, admin_pw) and may set
-- main_db and test_db. Defaults are hermi and hermi_test. No secret lives in this file.
\if :{?main_db}
\else
  \set main_db hermi
\endif
\if :{?test_db}
\else
  \set test_db hermi_test
\endif

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hermi_owner')   THEN CREATE ROLE hermi_owner   NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hermi_app')     THEN CREATE ROLE hermi_app     NOLOGIN NOBYPASSRLS; END IF;  -- the API: subject to every policy
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hermi_worker')  THEN CREATE ROLE hermi_worker  NOLOGIN; END IF;                -- Procrastinate workers, scheduler, webhooks, import jobs
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hermi_admin')   THEN CREATE ROLE hermi_admin   NOLOGIN; END IF;                -- the admin console only
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hermi_definer') THEN CREATE ROLE hermi_definer NOLOGIN BYPASSRLS; END IF;      -- owns the SECURITY DEFINER functions
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hermi_migrate_login') THEN CREATE ROLE hermi_migrate_login LOGIN IN ROLE hermi_owner;  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hermi_api_login')     THEN CREATE ROLE hermi_api_login     LOGIN IN ROLE hermi_app;    END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hermi_worker_login')  THEN CREATE ROLE hermi_worker_login  LOGIN IN ROLE hermi_worker; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hermi_admin_login')   THEN CREATE ROLE hermi_admin_login   LOGIN IN ROLE hermi_admin;  END IF;
END $$;
GRANT hermi_owner  TO hermi_migrate_login;   -- idempotent: re-granting changes nothing
GRANT hermi_app    TO hermi_api_login;
GRANT hermi_worker TO hermi_worker_login;
GRANT hermi_admin  TO hermi_admin_login;
-- BYPASSRLS is a role attribute and is not inherited through membership, so it is set on the two login roles themselves.
ALTER ROLE hermi_worker_login BYPASSRLS;
ALTER ROLE hermi_admin_login  BYPASSRLS;
-- The four passwords come from the caller (psql variables), never from a file in the repo.
ALTER ROLE hermi_migrate_login PASSWORD :'migrate_pw';
ALTER ROLE hermi_api_login     PASSWORD :'api_pw';
ALTER ROLE hermi_worker_login  PASSWORD :'worker_pw';
ALTER ROLE hermi_admin_login   PASSWORD :'admin_pw';
ALTER ROLE hermi_migrate_login SET role hermi_owner;     -- every object a migration creates is owned by hermi_owner
GRANT hermi_definer TO hermi_owner;                      -- lets a migration run ALTER FUNCTION ... OWNER TO hermi_definer

SELECT format('CREATE DATABASE %I OWNER hermi_owner', :'main_db') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'main_db') \gexec
SELECT format('CREATE DATABASE %I OWNER hermi_owner', :'test_db') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'test_db') \gexec
-- Only the four login roles may connect.
REVOKE CONNECT ON DATABASE :"main_db" FROM PUBLIC;
REVOKE CONNECT ON DATABASE :"test_db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"main_db" TO hermi_migrate_login, hermi_api_login, hermi_worker_login, hermi_admin_login;
GRANT CONNECT ON DATABASE :"test_db" TO hermi_migrate_login, hermi_api_login, hermi_worker_login, hermi_admin_login;
-- A role can become the owner of a function in a schema only if it has CREATE there, so this runs in each database.
\connect :"main_db"
GRANT CREATE ON SCHEMA public TO hermi_definer;
\connect :"test_db"
GRANT CREATE ON SCHEMA public TO hermi_definer;
