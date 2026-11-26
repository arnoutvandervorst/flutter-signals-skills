---
name: firebase-security-and-cost
description: Security and cost rules for a Flutter + Firebase app — firestore.rules is the security boundary (never only the UI), every visibility tier and backend-owned field gets a rules test both ways, private user data lives on an owner-only private doc, other users are looked up only through backend endpoints, analytics carry pseudonymous ids only; and Firebase cost + contention are design inputs (reads/writes per event at 10k users, ~1 write/s per doc, job-computed aggregates over per-event increments, per-event cost stated in the commit); rules tests on the app's real write payload; the compiled ruleset size limit. Use when writing or changing firestore.rules or storage.rules, adding a field that others can read, adding a query/listener/trigger write, designing a counter or aggregate, exposing user data, or adding analytics events.
---

# Firebase security and cost

## Security — non-negotiable

1. **`firestore.rules` is the boundary.** A UI gate is not security: any signed-in session
   (guests included) can call the SDK directly. Every tier the product promises (self /
   friend / public / staff) is enforced in rules.
2. **Every tier gets a rules test both ways** — the allowed reader succeeds *and* the
   disallowed one fails. Every new backend-owned field gets a test proving a client cannot
   write it (rules pin list + the model's `backendOwnedKeys`).
3. **Private data (contact details, push tokens, block list, codes) lives on an owner-only
   private doc** (e.g. `/userPrivate/{uid}`), never on the public profile doc. The backend
   loads it explicitly before reading it.
4. **Never query another user by phone / e-mail / code from the client.** Use a backend
   endpoint that returns only a public identity and hides blocks.
5. **Adding someone to a shared space goes through the backend** (consent / block checks),
   not an owner-writable rules path.
6. **Storage rules:** no `list` on user folders; `get` only by the uploader where the app
   renders token URLs.
7. **Analytics and logs carry pseudonymous ids or categories only** — never e-mail, phone,
   names.
8. **Impersonation / support sessions are read-only**, in rules and in HTTP endpoints.
9. **Rules tests write the payload the app really sends** — `Model.toMap()` with its blank
   sub-maps and `null` keys — not a hand-made minimal doc, and read the viewer's own
   *missing* deterministic-id doc. Three production `PERMISSION_DENIED` bugs passed
   hand-made tests (for example `test/contract/signup_zero_payload_test.dart`).
10. **The compiled ruleset has a size limit the emulator does not check** (250 KB compiled;
    a release fails with `400 INVALID_ARGUMENT`, then a misleading `409`). Track a proxy
    (`grep -vE '^\s*//' firestore.rules | tr -d ' \n' | wc -c`) with headroom below the
    last measured failure. Keep it small: rules only for writes the app makes, no
    `allow …: if false` (unmatched is already denied), bounded-field helpers
    (`str(v, max)`, `optStr(d, k, max)`) over spelled-out checks. When a release fails on
    size, make room — never deploy a ruleset other than the repo's.

## Cost — a design input, always

Before adding a read or write to a trigger, a listener, or a query, answer:
- How many times a day at **10k users**? (Per-impression and per-fanout work multiplies.)
- Does it land on **one hot document**? Firestore sustains ~**1 write/s per doc** — a
  per-event increment on a shared daily doc is a contention bug, not just a cost.
- Does a **scheduled job already page this data**? Derive from it instead.
- Can a per-fanout read be **cached in-process**?
- Is the query window **sized to what the UI shows**? No unbounded listeners.

Prefer **job-computed aggregates** (a daily/weekly job with `count()` / `sum()`) over
per-event increments for population-wide numbers; keep per-user writes on the user's own
doc. **State the per-event cost in the commit message** when a change adds one. If a
requested feature would multiply cost (per-event writes to a shared doc, per-impression
work, N+1 reads), flag it with numbers **before** implementing and propose the cheaper shape.

## Definition of done

- [ ] Rules updated; rules tests for every new tier / field, both ways.
- [ ] New queries have their composite index committed.
- [ ] Cost per event estimated at 10k users; stated in the commit if non-zero.

Reference: `firestore.rules`, `storage.rules`, `rules_test/firestore.spec.js`,
`docs/VISIBILITY.md`, `lib/services/user_directory.dart`. Ruleset size: the app's
`OPERATIONS.md`.
