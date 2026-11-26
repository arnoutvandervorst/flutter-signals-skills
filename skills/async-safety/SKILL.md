---
name: async-safety
description: No-silent-failure async in a signals + flutter_hooks Flutter app — the arrow-callback Future-drop hole no lint catches (onTap: () => state.save(x)), void-returning handler methods on state classes, a mounted/context.mounted guard after every await before touching BuildContext, capturing Navigator/ScaffoldMessenger before the gap, unawaited() only with catchError, bounded awaits for Firestore writes that may never ack offline, no empty or bare catch, rethrow over throw e, disposing timers/subscriptions/stream signals, a visible busy state on every action that waits on the backend, ActionPhase + PendingActions for an action that runs once per key or waits for a trigger's answer. Use when writing async/await, wiring onTap/onPressed/onChanged callbacks, touching context after an await, adding a Timer/Future.delayed/stream listener, or writing try/catch.
---

# Async safety: no failure may be silent

Adapted from zakariaf/Flutter-Skills `async-safety` for the signals stack.

## Non-negotiable rules

1. **A callback never holds a `Future`.** `onTap: () => state.save(x)` where `save` is
   async is caught by **no** lint (`discarded_futures`, `unawaited_futures` and
   `unused_result` all miss it: the arrow returns the Future, the `VoidCallback` discards
   it). Fix the shape: the state class exposes a `void` method that runs
   `unawaited(_save(x).catchError(...))` and reports the failure into a signal/snackbar.
2. **Guard after every `await`, immediately before the next `BuildContext` use**
   (`if (!context.mounted) return;`). With several awaits, the guard goes after the last.
   Or capture `Navigator.of(context)` / `ScaffoldMessenger.of(context)` before the gap.
3. **`unawaited(x)` only if `x` cannot fail silently** — it ends in `.catchError(...)` that
   logs with the stack and surfaces the failure.
4. **Firestore writes on a UI path are bounded** (`ackOrQueued`): offline, a write future
   never resolves; an unbounded await freezes the UI. A missing ack means "queued".
5. **Every `Timer`, `StreamSubscription`, `StreamController` and stream signal is released**
   in the state's `dispose()` (or the hook's cleanup). Timer callbacks that touch UI check
   the owner is still alive.
6. **No empty catch, no bare catch.** Catch the specific type (`on FirebaseException`),
   log with the stack (Crashlytics), surface the failure; `rethrow`, never `throw e`
   (resets the stack).
7. **Never `assert` a platform/plugin result** — asserts are stripped in release.
8. **Nothing unbounded before `runApp`.** Every boot step has a timeout; only
   `Firebase.initializeApp` may fail boot.
9. **An action that waits on the backend shows it at once.** The control turns busy on tap
   (a spinner in place of the label — one shared `CustomBusyLabel(busy:, child:)` — or a
   dimmed row/overlay for list items), is disabled while busy so it cannot fire twice, and
   says so when it fails (a snackbar from slang). Greying out alone is not feedback.
   Navigate away only after success; a destructive call (delete, leave, dissolve, remove)
   is awaited, never fired and forgotten.
10. **"Busy" is not "failed".** A state method that refuses while a save runs (returns
    `false`) must not reach a "Couldn't save" snackbar: gate the controls on the state's
    `isSaving`/`busy` signal so the second tap never happens.
11. **An action keyed per item, or answered by a trigger, runs through `PendingActions<K>`**
    — `ActionPhase` (`idle` / `sending` / `waiting`), the action twin of `LoadPhase`. A
    widget-local `useState(false)` only covers the await: it is lost when a list tile is
    rebuilt mid-write (scrolled away and back), and it comes back between a client write
    and the trigger that answers it, so a second tap writes again. The state class (or the
    list that owns the items) holds one `PendingActions<K>` keyed by what the action is
    about (task id, message id) and disposes it; `run(key, write:, confirmed:)` runs once
    per key, stays `waiting` until `confirmed()` — read from the state's own signals —
    turns true or a timeout passes, and goes back to `idle` (logged) when the write fails.
    Render with `ActionPhaseBuilder` (control off and `CustomBusyLabel` while
    `phase.isBusy`, optionally a "being processed" line while `waiting`). A caller that
    must tell "refused, already busy" from "failed" checks `phaseOf(key).isBusy` first —
    busy is not failed (rule 10). Two limits: a **last-answer-wins toggle** (yes / no /
    clear) frees at the write, not at the confirm — holding it makes the user's correction
    wait on the trigger. And a **doc the client writes for an action gets an id derived from
    what it is about** (`<taskId>_<day>`), never `collection.doc()` — a retried or double
    tap then lands on the same doc instead of a second one.
12. **Writes still unacked at sign-out are bounded too.** After sign-out they never complete;
    a sign-out that awaits them hangs.

## Definition of done

- [ ] No `() => asyncCall()` handed to a `VoidCallback`.
- [ ] Every post-await `context` use is guarded.
- [ ] Every `unawaited` ends in `catchError`; every catch is typed and logged.
- [ ] Every backend action shows busy on tap, cannot double-fire, and surfaces failure.
- [ ] Per-item or trigger-answered actions go through `PendingActions<K>`, with tests for
      sending → waiting → idle, a refused second run, a failed write and the timeout.

Reference implementations: deterministic action ids — `test/model/idempotent_ids_test.dart`;
`PendingActions` / `ActionPhase` from `signals_kit` +
`lib/presentation/common/action_phase_builder.dart` (home tasks, check-in, pay, chat-bubble
actions, inbox archive / mark read), `test/signals/pending_actions_test.dart`.
