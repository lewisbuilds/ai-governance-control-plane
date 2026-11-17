-- Document the payload actually included by audit_app.py when it hashes an event.
comment on table audit_log is
'Append-only audit log. entry_hash = sha256(prev_hash || "|" || canonical_json(event_type, subject, decision, details)). prev_hash="GENESIS" for the first entry. Writers serialize with a transaction-scoped advisory lock.';
