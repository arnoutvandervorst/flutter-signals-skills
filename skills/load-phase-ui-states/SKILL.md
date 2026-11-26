---
name: load-phase-ui-states
description: Rendering the non-happy paths in a signals Flutter app — every document-backed state exposes a LoadPhase (loading / error / missing / ready) and pages render it with LoadPhaseBuilder, tiles with LoadPhaseSkeleton; neutral null fallbacks; empty vs filtered-empty; the feedback ladder (inline → snackbar → banner → dialog); Undo over confirm; permission-denied as "missing". Use when building a page or tile that loads data, showing a spinner/skeleton/error/empty state, adding a snackbar or dialog, handling a failed or refused read, or when a screen shows "Unknown"/"Expired"/"empty" or nothing at all while it is really still loading (visible waiting), an offline banner, or the boot screen.
---

# Load phases and UI states

Three different answers — *don't know yet*, *failed*, *gone* — must never render the same.
A slow network, a permission error and a deleted document used to look identical because
every computed painted its null fallback ("Expired", "Unknown", "") for all of them.

## Non-negotiable rules

1. **Every document-backed state exposes `phase`** — `Computed<LoadPhase>` built with
   `loadPhaseOf<T>(asyncState)`: `AsyncLoading` → loading, `AsyncError` → error,
   `AsyncData(null)` → missing, `AsyncData(value)` → ready.
2. **A page renders by phase with `LoadPhaseBuilder`**: skeleton bones while loading, the
   error column (with retry) on error, the "gone" empty state when missing, content when
   ready. **A tile uses `LoadPhaseSkeleton`** (bones only — a tile never shows an error column).
3. **Null-model fallbacks are neutral** (`''`, `0`, `0.0`, `false`, `[]`) — never a
   real-looking value. The phase, not the fallback, tells the user what is going on.
4. **A rules refusal of a members-only document is `missing`, not `error`** — "not for you"
   and "gone" are the same answer to the viewer; the generic error column suggests a bug.
5. **Empty vs filtered-empty are different states.** "You have no snaps yet" + a create
   action ≠ "Nothing matches this filter" + a clear-filter action.
6. **The feedback ladder, least intrusive first:** inline text next to the control →
   snackbar (transient, one action max) → banner (persistent condition, e.g. offline) →
   dialog (only when the user must decide before continuing).
7. **Undo over confirm** for reversible actions (archive, remove from list): act, then offer
   Undo in the snackbar. Reserve confirmation dialogs for irreversible actions.
8. **Error copy names what failed and what to do**, from slang — never an exception string.
9. **Waiting is always visible, at once.** On a slow network a silent wait reads as broken
   (a blank or black screen, then content or an error seconds later). Every wait on
   Firestore or a function shows a skeleton, a spinner or a short label immediately.
10. **Nothing to skeletonize is not "loaded".** `LoadPhaseBuilder` with an empty child
    (`SizedBox.shrink()`, the usual `x == null ? const SizedBox.shrink() : …`) must show a
    loader during `loading` — a skeleton of nothing is a white page. Build that into
    `LoadPhaseBuilder` once (`loading when child is SizedBox && child.child == null` →
    `CustomLoadingColumn`) instead of fixing every call site.
11. **The phase covers every stream the page needs.** A page that also waits on a second
    stream (a saved draft, a check-in to prefill) stays `loading` until that one is in;
    otherwise it is `ready` with an empty child — blank.
12. **A list or section never says "empty" while it is loading.** `?? []` on an
    `AsyncLoading` value paints "No buddies yet" on a cold start. Sections that hide when
    empty hide only when *ready* and empty; while loading they show a small skeleton.
13. **A media box shows a placeholder while its poster/video loads** — never a bare
    black/coloured box with nothing in it.
14. **An empty first snapshot from the cache is not "empty".** On a cold start the cache
    answers first with nothing; hold that snapshot until the server answers or a timeout
    passes (`holdEmptyFirstFromCache`), or the page flashes its empty state.
15. **"Offline" comes from our own acks, never a connectivity plugin.** The banner shows when
    our writes stop getting server acks (with a decay timer), because "has Wi-Fi" says
    nothing about whether Firestore is reachable.
16. **The boot shell has three steps and no dependencies**: a spinner, then a "slow
    connection" line after a threshold, then an error with retry — never an endless spinner.

## Definition of done

- [ ] `phase` exposed; the page/tile renders all four phases differently.
- [ ] Tests cover loading, error, missing, ready via the state's `fromStream` seam.
- [ ] Empty and filtered-empty distinguished where filters exist.
- [ ] No raw exception text reaches the UI.
- [ ] On a throttled network (or with the emulator paused) nothing renders blank, black
      or "empty" while it loads.

Reference implementations: `lib/signals/common/load_phase.dart`,
`lib/presentation/common/load_phase_builder.dart` (`isEmptyChild`),
`test/signals/load_phase_states_test.dart`, `lib/signals/group/group_auth_state.dart`
(permission-denied → missing), `docs/ARCHITECTURE.md` "Waiting is always visible" (or
`docs/DESIGN.md`), `lib/signals/home/home_stack_state.dart`
(`holdEmptyFirstFromCache`), `lib/signals/common/network_health.dart`,
`lib/presentation/common/boot_shell.dart`. The action twin — `ActionPhase` +
`PendingActions<K>` + `ActionPhaseBuilder` for a control that waits on the backend — is in
`async-safety` (rule 11).
