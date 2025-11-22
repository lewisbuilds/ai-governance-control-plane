-- Database initialization for Continuous AI Governance Control Plane
-- Tables:
--  - model_lineage: records lineage and registration events for models
--  - audit_log: append-only audit log with hash chaining (prev_hash -> entry_hash)
--    Immutability is enforced at the API and reinforced with triggers to prevent UPDATE/DELETE.

create table if not exists model_lineage (
  id bigserial primary key,
  model_id text not null,
  version text not null,
  artifacts jsonb not null default '[]'::jsonb,
  created_by text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_lineage_model_id on model_lineage (model_id);
create index if not exists idx_lineage_created_at on model_lineage (created_at desc);

create table if not exists audit_log (
  id bigserial primary key,
  event_type text not null,
  subject text not null,
  decision boolean not null,
  details jsonb not null default '{}'::jsonb,
  prev_hash text not null,
  entry_hash text not null unique,
  created_at timestamptz not null default now()
);

create index if not exists idx_audit_created_at on audit_log (created_at desc);
create index if not exists idx_audit_subject on audit_log (subject);

-- Append-only enforcement for audit_log
create or replace function prevent_audit_update_delete() returns trigger as $$
begin
  if (TG_OP = 'UPDATE') then
    raise exception 'audit_log is append-only: UPDATE not allowed';
  elsif (TG_OP = 'DELETE') then
    raise exception 'audit_log is append-only: DELETE not allowed';
  end if;
  return null;
end;
$$ language plpgsql;

drop trigger if exists trg_audit_no_update on audit_log;
create trigger trg_audit_no_update
  before update or delete on audit_log
  for each row execute function prevent_audit_update_delete();

comment on table audit_log is
'Append-only audit log. entry_hash = sha256(prev_hash || "|" || canonical(details) || "|" || created_at_iso). prev_hash="GENESIS" for first entry.';
