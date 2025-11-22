-- 0001_add_request_id_column.sql
-- Purpose: add optional correlation/request ID to audit_log and index it for faster lookups

alter table if exists audit_log
  add column if not exists request_id text;

comment on column audit_log.request_id is 'Optional correlation/request ID to link audit entries to requests/logs.';

create index if not exists idx_audit_request_id on audit_log (request_id);
