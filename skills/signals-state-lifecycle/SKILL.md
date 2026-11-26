---
name: signals-state-lifecycle
description: How state is owned in a signals_flutter + flutter_hooks app — a state class per feature under lib/signals/ that creates every Signal, Computed, StreamSignal and effect, exposes computeds and page slots, and disposes all of it; FutureSignals only through guardedFutureSignal; no signal write after dispose; the widget creates it with useMemoized, disposes it with useEffect, reads it with useComputed + SignalBuilder. Covers read-vs-workflow state splits, globals, StreamRecoveryController, LoadPhase exposure, and the fromStream test seam. Use when writing or reviewing a state class, a StreamSignal / Firestore stream, a computed, an effect, a HookWidget that owns state, a dispose() method, or when a screen leaks listeners or shows stale data.
---

# Signals state lifecycle

State lives in classes under `lib/signals/<feature>/`, never in widgets. A state class
**owns** every reactive object it creates and **disposes all of them**. Widgets create the
state, dispose it, and render derived values.

## Non-negotiable rules

1. **The state class creates every `signal`, `computed`, `StreamSignal` and `effect` it uses**
   and releases each one in `dispose()`. `EffectCleanup` handles are called, signals and
   computeds `.dispose()`d, stream signals disposed last. WHY: long-lived reactive objects
   keep Firestore listeners alive — a leak is a stream that keeps billing reads.
2. **No `signal(` / `computed(` / `effect(` in `lib/presentation/`.** Widgets use hooks
   (`useComputed`, `useSignal` only for purely local UI state) and `SignalBuilder`.
3. **Widget ownership shape:** `useMemoized(() => XState(id), [id])` to create,
   `useEffect(() => state.dispose, [state])` to dispose, `useComputed` to derive a view
   model, `SignalBuilder` to render. Rebuild keys are the constructor inputs.
4. **One page owns one feature state.** The state exposes slots (`body`, `actions`,
   `bottomNavigationBar`) and sub-widgets consume that state instead of branching inline.
5. **Split read state from workflow state** on complex features: `XState` (read, streams)
   alongside `XCreateState` / `XEditState` / `XManageState` (drafts, submit, validation).
6. **Document-backed state exposes `phase`** (`Computed<LoadPhase>`, see
   `load-phase-ui-states`). Computeds that read the model fall back to neutral values
   (`''`, `0`, `false`, `[]`) while not ready — never a real-looking value.
7. **Long-lived streams go through `StreamRecoveryController`** (heartbeat, backoff,
   re-subscribe) and are gated on auth (`authIsAuthenticated`) so a signed-out session
   subscribes to nothing.
8. **Give the state a test seam:** a `@visibleForTesting XState.fromStream(id, stream)`
   constructor (preview mode: no viewer, never touches auth or Firestore). Test all four
   phases.
9. **Don't stack a second query layer.** If the data already lives in a feature or auth
   signal (current user, followers, chats), derive it with `useComputed` + `SignalBuilder`.
10. **Globals** (app-lifetime signals) live in `lib/signals/global/global.dart` and are
    re-exported by the barrel `lib/signals/signals.dart`. They are the only signals without
    a dispose.
11. **FutureSignals only through `guardedFutureSignal`**, never plain `futureSignal`.
    signals_core 7 keeps the pending future through `dispose()`, so a page closed while it
    loads writes the late value into a disposed signal (`SignalsWriteAfterDisposeError`,
    signals.dart#507). The check `plain-future-signal` enforces it.
12. **No signal write after dispose.** A state method that writes signals after an `await`
    (or a timer/ticker that reads computeds) checks a `_disposed` flag first — the page may
    have closed during the gap. This was a fatal Crashlytics crash, not a log line.
13. **A ref-counted state cache releases by instance, not by id** — releasing by id disposed
    the entry a new viewer had just taken for the same id.
14. **"Once per session" effects are keyed by uid** (a `lastUid` compare), not a boolean
    someone must remember to reset; a reconcile effect (badge, device metadata) runs from the
    authoritative stream every time, with no "only on change" gate that can stick.

## Shape of a state class

```dart
class GroupAuthState {
  final String groupId;
  final StreamRecoveryController _streamRecovery = StreamRecoveryController(name: 'GroupAuthState');

  late final StreamSignal<Group?> _groupStream;
  late final EffectCleanup _groupStreamEffect;
  late final Computed<LoadPhase> phase;
  late final Computed<String> title;

  final Stream<Group?>? _previewStream; //* test seam

  GroupAuthState(String groupId) : this._(groupId, null);

  @visibleForTesting
  GroupAuthState.fromStream(String groupId, Stream<Group?> stream) : this._(groupId, stream);

  GroupAuthState._(this.groupId, this._previewStream) {
    _groupStream = _streamRecovery.watch(() {
      final preview = _previewStream;
      if (preview != null) return preview;
      if (!authIsAuthenticated.value) return const Stream<Group?>.empty();
      return Group.firestoreService.streamFromId(groupId);
    }, streamName: 'GroupAuthState._groupStream');
    _groupStreamEffect = _groupStream.subscribe(_streamRecovery.observe);

    phase = computed(() {
      final state = _groupStream.value;
      // members-only doc: a refusal is "not for you" = missing, never the error column
      if (state is AsyncError<Group?> && isPermissionDenied(state.error)) return LoadPhase.missing;
      return loadPhaseOf<Group>(state);
    });
    title = computed(() => _groupStream.value.value?.name ?? ''); // neutral fallback
  }

  void dispose() {
    _groupStreamEffect();
    _streamRecovery.dispose();
    phase.dispose();
    title.dispose();
    _groupStream.dispose();
  }
}
```

## Shape of the owning widget

```dart
class GroupTile extends HookWidget {
  const GroupTile({super.key, required this.groupId});
  final String groupId;

  @override
  Widget build(BuildContext context) {
    final state = useMemoized(() => GroupAuthState(groupId), [groupId]);
    useEffect(() => state.dispose, [state]);
    final vm = useComputed(() => (title: state.title.value, phase: state.phase.value));
    return SignalBuilder(builder: (context) => LoadPhaseSkeleton(phase: vm.value.phase, child: Text(vm.value.title)));
  }
}
```

## Anti-patterns

- A `computed` or `effect` created inside `build()` — recreated every rebuild, never disposed.
- A state class with signals but no `dispose()`, or a `dispose()` that forgets the stream.
- Branching on raw Firebase auth in a widget — branch on the app's auth gate variants.
- A second Firestore query for data another signal already holds.
- Computed fallbacks like `'Expired'` / `'Unknown'` for a not-yet-loaded model.
- `futureSignal(...)` directly, or `_x.value = …` after an `await` without a disposed check.

## Definition of done

- [ ] Every reactive object created in the class appears in `dispose()`.
- [ ] The widget disposes the state it created.
- [ ] `phase` exposed and rendered; neutral fallbacks.
- [ ] `fromStream` seam + tests for loading / error / missing / ready.

Reference implementations: `lib/signals/group/group_auth_state.dart`,
`lib/signals/user/user_auth_state.dart`, `lib/presentation/user_auth/user_auth_tile.dart`,
`lib/presentation/user_auth/**` (page slots), `test/signals/load_phase_states_test.dart`,
`lib/signals/common/guarded_future_signal.dart` (+ `test/contract/guarded_future_signal_contract_test.dart`,
both apps), `lib/signals/snap/snap_state_cache.dart` (release by instance),
`lib/signals/common/device_metadata_sync.dart`, `app_badge_sync.dart`.
