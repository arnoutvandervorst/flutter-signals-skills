---
name: firestore-model-layer
description: The model and data layer of a signals + Firebase Flutter app — persisted models extend BaseModel, use dart_mappable, expose a static FirestoreService<T>, and change via copyWith + update()/delete(); FirestoreService is the only typed Firestore layer (ids, paths, timestamps, backendOwnedKeys stripping, private-key split, ackOrQueued); collection and field names come from firestore_paths / field_names; logical deletes; primary constructors; super.<field> in subclasses; UPPER_SNAKE enum wire values; UI enums with EnumItem; Source.server for backend-created docs, targeted updates for partial fields, orderBy fields present on create, PageState liveness. Use when adding or changing a model, a Firestore read/write/query, an enum, a field name, a backend-owned field, or a delete.
---

# Firestore model layer

## Non-negotiable rules

1. **Persisted models extend `BaseModel`** (`id`, `path`, `createdAt`, `updatedAt`,
   `expiresAt`, `archiveAt`), are `@MappableClass`, expose a static
   `FirestoreService<T> get firestoreService`, and change through `copyWith(...)` then
   `update()` / `delete()`. Drafts for create flows come from a `Model.initial(...)` factory.
2. **`FirestoreService<T>` is the only typed Firestore layer.** It injects `id`/`path`,
   stamps timestamps, strips `backendOwnedKeys`, routes private keys to the private doc,
   and provides `ackOrQueued`. No raw `FirebaseFirestore.instance.collection(...)` writes
   scattered through the app — and never in `lib/presentation/`.
3. **Interactive writes go through `ackOrQueued`**: a missing server ack means "queued
   offline", not "lost". Never `await` a raw write on a UI path — offline, it never resolves.
4. **Names by constant:** collection paths from `lib/data/firestore_paths.dart`, field
   names in `where` / `orderBy` / `update` from `lib/data/field_names.dart`. (A contract
   test can pin that every query uses them.)
5. **Backend-owned fields** (counters, stamps, moderation, roles) are listed in the model's
   `backendOwnedKeys` so a stale in-memory model can never write them back — and are pinned
   in `firestore.rules` (see `firebase-security-and-cost`). The client never recomputes a
   denormalised counter; it reads the field.
6. **Some deletes are logical** (e.g. a user is marked `EXPIRED` so backend cleanup runs).
   Never replace a logical delete with a hard delete.
7. **New classes use primary constructors** (Dart ≥ 3.13):
   `class const Kudo({super.id, …, final String refId = ''}) extends BaseModel with KudoMappable`.
   `super.*` first, `final` on **every** own parameter (a bare parameter creates no field
   and the mapper silently loses it), factories stay in the body. Existing classes are
   converted only when touched.
8. **Adding a field to a base `@MappableClass`** requires `super.<field>` in **every**
   subclass constructor, or the subclass `copyWith` silently drops it.
9. **Enum wire values are UPPER_SNAKE** (`build.yaml`: `enumCaseStyle`); UI-facing enums
   live in `lib/model/enum.dart` as `enum X with EnumItem` (localized `title`, `iconData`,
   `color`) — never a widget-local switch.
10. **Keep Dart and TypeScript models in lockstep** for anything the backend reads or
    writes; a contract test pins shared enums and constants.
11. **A doc the backend creates is read with `Source.server`** (e.g. right after sign-up):
    the cache can never hold it yet, so a default read answers "missing" from the cache.
12. **Partial fields (heartbeat, `lastActiveAt`, a single flag) get one targeted update**,
    never a full-model `update()` from a snapshot that may be stale — that writes old values
    back over fields another writer just set.
13. **Every field a query orders or filters by is written on create.** A doc without the
    `orderBy` field silently drops out of the query; nothing errors.
14. **Paging liveness is a cost choice.** `PageState` `window` keeps the whole loaded window
    in one listener (live edits everywhere, a growing window re-reads it); `firstPageOnly`
    keeps only page one live. Pick per list and say why.

## After editing a model

Run `dart run build_runner build --delete-conflicting-outputs` (see
`codegen-slang-mappable`) and commit the regenerated `*.mapper.dart`.

## Definition of done

- [ ] Model extends `BaseModel`, has `firestoreService`, mapper regenerated.
- [ ] New backend-owned fields in `backendOwnedKeys` **and** pinned in rules (+ rules test).
- [ ] Queries use `field_names` / `firestore_paths`; any new compound query has its index in
      `firestore.indexes.json` (pinned by an index contract test).

Reference implementations: `lib/model/base.dart`,
`lib/services/database/firestore.dart`, `lib/data/field_names.dart`,
`lib/model/enum_item.dart`, `lib/services/auth/sign_up_persistence.dart` (`Source.server`),
`lib/signals/common/page_state.dart`, `test/contract/field_names_test.dart`,
`test/contract/backend_owned_keys_test.dart`, `test/contract/firestore_indexes_test.dart`.
