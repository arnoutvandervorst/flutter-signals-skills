---
name: cloud-functions-v2
description: Backend conventions for Firebase Cloud Functions v2 in TypeScript alongside a Flutter app — v2 handlers only, index.ts as the single export surface, an internal.ts barrel for shared classes, procOn* handler functions, TS models mirroring the Dart models (toData/fromData/fromDoc/static firestoreService), idempotent handlers (ProcessedEvent claim or deterministic ids), retry with a stale-event guard, scheduled-job retry by cadence, deterministic retried handlers (no Math.random), deadlines and reuse for external calls, backend copy in functions/i18n, one time zone for day boundaries, batched deploys, pure decision functions tested with vitest, structured activity logging without identifiers. Use when writing or changing a Firestore trigger, HTTPS endpoint, scheduled job, Cloud Task handler, external API call, backend push/e-mail copy, or backend model, or when deploying functions.
---

# Cloud Functions v2

## Non-negotiable rules

1. **v2 only.** Never add a v1 function. Region and memory/timeout tiers come from shared
   constants.
2. **`functions/src/index.ts` is the single export surface**; shared building blocks
   (constants, enums, models, `BaseModel`, `FirestoreService`, notification helpers) are
   re-exported from `classes/internal.ts` — import from the barrel.
3. **Handlers are thin wrappers around `procOn*` functions** (`procOnCreateSnap`, …) that
   take plain inputs, so they can be called from tests and from other handlers.
4. **Backend models mirror Dart:** extend the TS `BaseModel`, implement `toData`, populate
   via `fromData` / `fromDoc`, expose a static `firestoreService`, and keep `add()` /
   `update()` / `delete()` on the model instead of raw collection writes in handlers.
5. **Every trigger is idempotent.** Firestore triggers are delivered at least once and run
   with `retry: true`: claim the event (`ProcessedEvent.claim(event.id, handler)`) before a
   non-idempotent effect (counter increment, push, coin), or write with a deterministic id
   (`create()` on `snap_<id>`). Guard against stale redeliveries (drop events older than a
   few hours).
6. **Await every side effect** (pushes, alerts, writes). An un-awaited promise can be frozen
   with the instance. A push failure is logged, not retried.
7. **Decisions are pure functions, tested with vitest** next to the source
   (`*.test.ts`); the handler only gathers inputs and performs writes. Firestore is stubbed
   with `vi.spyOn`, never a live emulator in unit tests.
8. **Cost per event is a design input** (see `firebase-security-and-cost`): no per-event
   writes to shared docs; one batched `getAll` over N single reads.
9. **Scheduled jobs page with a cursor and a page size**, are capped to one instance, and
   have retry configured; they never `.get()` a whole collection.
10. **Usage telemetry:** one structured log line per meaningful event
    (`logActivity(kind, fields)`) with categories and counts only — an allow-list keeps
    uids, names and document ids out.
11. **Scheduled-job retry follows the cadence.** The scheduler defaults to zero retries, so a
    cold-start abort loses the run. Sub-daily jobs: a short retry (3 from 30 s) — the next
    run is their real retry. Daily / weekly / monthly jobs: 5 retries from minutes up to an
    hour (~2–3 h in total) to bridge a regional outage. Every such job converges on a
    re-run (deterministic ids, `addIfMissing` on a day key). A job that is idempotent by
    construction takes no up-front claim — a claim would silence a run that crashed.
12. **A retried handler decides the same way twice:** a seeded shuffle, never
    `Math.random()` (check `math-random-in-handlers`).
13. **External calls have a deadline and are reused.** A failed screening is "unscreened"
    (re-queued through a task queue), never a detection. An endpoint that opens something
    outside Firestore (a payment) reuses the one still open instead of starting another.
    Redirect hosts come from an allow-list.
14. **Backend copy (push, inbox, e-mail) is slang JSON under `functions/i18n`**, generated
    with `npm run i18n`; never inline nl/en strings in TypeScript.
15. **Day boundaries come from one zone constant** (`timeZone`) through shared
    `localDateOf` / `startOfLocalDay` helpers; a product cutoff (a journal day that runs
    until 04:00) is one helper mirrored in Dart and TS, tested on both sides.
16. **Kill switches per trigger family** (`kDisableOn*Triggers`) in the shared constants.
17. **Deploy in batches.** A shared-code change re-deploys every function and hits the
    60 writes/min/region quota; deploy 30 at a time with a pause. A new trigger with retries
    needs `--force` in a non-interactive deploy.

## Definition of done

- [ ] `npm run lint && npm run build && npm test` green.
- [ ] Idempotency claim / deterministic id on every non-idempotent effect.
- [ ] Pure decision function + vitest cases for the new branch.
- [ ] Dart/TS mirrors updated together; contract test still green.

Reference: `functions/src/index.ts`, `functions/src/classes/internal.ts`,
`functions/src/classes/processed_event.ts`, `functions/src/util/triggers.ts`
(`scheduleRetryFor`), `functions/src/services/activity.ts`, `docs/BACKEND_FUNCTIONS.md`,
`docs/ARCHITECTURE.md` "Idempotency", `docs/BACKEND_I18N.md`. A variant: handlers live per
feature (`functions/src/<feature>/handlers.ts`), use deterministic ids + `isStale`
(`functions/src/economy/events.ts`) instead of `ProcessedEvent`, `kDailyRetry` in
`functions/src/classes/constants.ts`, and `scripts/deploy_functions.sh` (batched deploy).
