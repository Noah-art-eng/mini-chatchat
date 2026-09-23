# Mini ChatChat Phase 10.2 User Data Isolation

## Goal

Phase 10.2 adds the multi-tenant data ownership foundation without adding login, registration, OAuth, or login UI. The current runtime still behaves as a single demo workspace, but persistent data is now scoped through a Demo User so future authenticated users can be isolated without changing the public API contract.

## Database Migration

`backend/db.py` now creates and maintains a default Demo User:

- email: `demo@local`
- display name: `Demo User`
- provider: `demo`

The following tables receive `user_id` through compatible `ALTER TABLE` migrations:

- `conversation`
- `message`
- `knowledge_base`
- `knowledge_file`
- `file_doc`

Existing rows with `NULL user_id` are migrated to the Demo User. This preserves old local data and keeps current unauthenticated usage compatible.

The legacy global unique constraints were also migrated:

- `knowledge_base`: from global `kb_name` uniqueness to `UNIQUE(user_id, kb_name)`
- `knowledge_file`: from global `(kb_name, file_name)` uniqueness to `UNIQUE(user_id, kb_name, file_name)`

This allows future users to own knowledge bases and files with the same names without collisions.

## User-Scoped Database Access

Database helpers now resolve `user_id=None` to the Demo User. Existing API calls do not need a user argument yet, but repository methods are ready for authenticated user scope later.

Scoped helpers include:

- `create_default_kb`
- `list_kbs`
- `get_kb_record`
- `user_owns_kb`
- `create_kb`
- `create_conversation`
- `list_conversations`
- `get_conversation`
- `update_conversation_title`
- `delete_conversation`
- `save_message`
- `get_conversation_messages`
- `update_message_feedback`
- `upsert_file_record`
- `update_file_status`
- `delete_file_record`
- `list_file_records`
- `add_file_doc`
- `delete_file_docs`
- `list_file_docs`
- `delete_file_docs_by_kb`
- `delete_files_by_kb`
- `delete_kb_record`

## File Directory Migration

Knowledge-base and temp-file runtime data now use a user-scoped root:

```text
backend/data/
  users/
    demo/
      knowledge_bases/
        default/
          content/
          uploads/
          vector_store/
      temp/
```

`backend/user_scope.py` owns these path helpers:

- `get_user_root`
- `get_user_kb_root`
- `get_user_temp_root`
- `ensure_user_directories`
- `migrate_legacy_demo_files`

Legacy runtime folders such as `backend/data/default` and `backend/data/temp` are copied into the Demo User scope when the backend starts or a KB service is created. The migration copies data instead of deleting or moving it, so local runtime data is preserved.

## FAISS / Upload / KB Scope

`MiniKBService` now defaults to:

```text
data/users/demo/knowledge_bases/{kb_name}
```

The service stores uploads, parsed content, chunks metadata, and FAISS files under the user-scoped KB path. Temp KBs use:

```text
data/users/demo/temp/{temp_kb_id}
```

KB import/export keeps the same public zip shape, but reads from and restores into the user-scoped KB root.

## Ownership Check

The first ownership checks are now centralized around `user_owns_kb` and user-scoped DB filtering:

- conversations are listed, loaded, renamed, deleted, and written only within the current user scope
- messages and feedback are updated only within the current user scope
- knowledge bases are listed and deleted only within the current user scope
- document metadata and file chunk mappings are read/written only within the current user scope
- `kb_search` refuses unknown or unowned KB names instead of implicitly creating a directory
- `/switch_kb` refuses unknown or unowned KB names

Current Guest mode resolves to the Demo User, so existing API requests remain compatible.

## Frontend Compatibility

The React auth foundation still defaults to a guest session. `GuestSession` now carries `apiUserScope: "demo"` as a future-facing hint for API clients. No login UI or route gating behavior changed in this phase.

## Backward Compatibility

Public API request and response shapes are unchanged. Existing local data is assigned to the Demo User and legacy runtime directories are copied into the new scoped layout.

## Remaining Work

- Phase 10.3: add email login and registration.
- Pass authenticated user identity from JWT dependencies into DB and service calls.
- Add request-level ownership checks once real users exist.
- Add explicit tests for cross-user access denial after authenticated users are available.
- Decide whether to eventually remove old legacy runtime folders after user confirmation.
