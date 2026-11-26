---
name: signals-flutter-conventions
description: The front door for a Flutter + Firebase app built on signals_flutter + flutter_hooks + go_router + slang + dart_mappable. States the house rules every change obeys (one concern per lib/ layer, state classes own and dispose every signal, widgets only render, Firestore only through FirestoreService, rules are the security boundary, cost is a design input) and routes each task to the focused skill. Use at the start of any Flutter/Dart/Cloud Functions work in such an app, before designing a feature, when unsure which layer code belongs in, or when onboarding to the conventions.
---

# Signals Flutter conventions — index

House rules for Flutter apps on the signals stack. Apply these on every task, then open the
focused skill.

The stack: `signals_flutter` + `signals_hooks` (state), `flutter_hooks` (widget
lifecycle), `go_router` (routing), `slang` (i18n), `dart_mappable` (models), Firebase
(Auth, Firestore, Storage, Messaging, Functions v2 in TypeScript).

The app's own `CLAUDE.md` wins on conflict; these skills are the shared baseline.

## Non-negotiable rules

1. **One concern per `lib/` directory; never cross layers inline from a widget.**
   `presentation/` renders, `signals/` owns state and async, `model/` holds entities,
   `services/` wraps IO, `routes/` holds the router, `i18n/` holds copy. *(signals-state-lifecycle)*
2. **Every owned `Signal`, `Computed`, `StreamSignal`, effect and subscription is disposed
   by the state class that created it.** Long-lived reactive objects are the norm; a leak
   is a stream listener that never stops billing reads. *(signals-state-lifecycle)*
3. **Widgets render.** `HookWidget` + `useMemoized` / `useEffect` / `useComputed` / `SignalBuilder`.
   Follow the signals_flutter docs (https://dartsignals.dev/packages/signals_flutter/): `Watch`,
   `Watch.builder`, `.watch(context)` and `SignalsMixin` are deprecated in v7 — a local rebuild is
   `SignalBuilder(builder: (context) => …)`, a widget whose whole build reacts extends `SignalWidget`.
   Never silence `deprecated_member_use` in `analysis_options.yaml`: it is how the next deprecation
   reaches you (rule `deprecated-signals-api`).
   No Firestore, no business logic, no inline copy. *(widget-composition-and-layout)*
4. **Document-backed state exposes a `LoadPhase`** (loading / error / missing / ready), and
   the UI renders by it. "Don't know yet", "failed" and "gone" never look the same, and
   waiting is always visible: no blank screen, no "empty" while loading, a busy state on
   every action that waits. *(load-phase-ui-states, async-safety)*
5. **Firestore only through the typed `FirestoreService<T>`**; models extend `BaseModel`,
   use `dart_mappable`, change via `copyWith` + `update()`. *(firestore-model-layer)*
6. **Security lives in `firestore.rules`, never only in the UI**; every tier is a rules test
   both ways. **Cost and contention are design inputs.** *(firebase-security-and-cost)*
7. **Backend: Cloud Functions v2 only, idempotent handlers, one export surface.**
   *(cloud-functions-v2)*
8. **All user-facing copy in slang; codegen with the right command.** *(codegen-slang-mappable,
   accessibility-and-copy)*
9. **Routes by constant, redirects as pure tested functions.** *(routing-go-router)*
10. **Async is never silent.** *(async-safety)*
11. **Test at the lowest layer that can catch the bug; contract-test anything mirrored.**
    *(testing-strategy)*
12. **Betas bump the build number only; production promotes, never rebuilds.**
    *(release-versioning)*
13. **Strict analyzer** (`strict-casts`, `strict-inference`, `strict-raw-types`); prefer
    explicit types; `flutter analyze` clean before done.
14. **iOS native dependencies through Swift Package Manager only, never CocoaPods**
    (`flutter config --enable-swift-package-manager`). No Podfile, no `pod install`, no pod
    as a workaround. A plugin without SPM support is a blocker to report, not a reason to
    bring pods back. Native pins live in the plugin's `Package.swift` and the app's
    `Package.resolved`. *(update-deps)*
15. **Docs change with the code.** A change that alters behaviour described in the app's
    docs (architecture, operations, testing, user guide) updates them in the same commit.

## Route to the right skill

| When you are… | Open |
|---|---|
| Writing a state class, streams, disposal, page slots | `signals-state-lifecycle` |
| Rendering loading / error / empty / missing, feedback, undo | `load-phase-ui-states` |
| Adding a model, a Firestore read/write, enum, field name | `firestore-model-layer` |
| Rules, visibility tiers, private data, counters, cost | `firebase-security-and-cost` |
| Writing a trigger, endpoint or scheduled job | `cloud-functions-v2` |
| Editing i18n JSON or a `@MappableClass` | `codegen-slang-mappable` |
| Building or refactoring UI, layout, gutter, shared widgets | `widget-composition-and-layout` |
| Routes, redirects, deep links | `routing-go-router` |
| `async`/`await`, callbacks, timers, try/catch | `async-safety` |
| Writing tests, contract tests, emulator suites | `testing-strategy` |
| Versioning, changelog, store release | `release-versioning` |
| Copy, semantics, a11y | `accessibility-and-copy` |
| Regenerating code / running the release gate / shipping a beta / updating packages (manual) | `run-codegen`, `run-integration-gate`, `release-beta`, `update-deps` |
| Store screenshots, demo videos, media site / the CI runner on the NUC (manual) | `store-media`, `nuc-ci-runner` |

## Reuse before building

Before writing a new primitive, check the app for these:

| Need | Reuse |
|---|---|
| Paginated list / grid | `PageState<T>` — `lib/signals/common/page_state.dart` |
| Load states | `LoadPhase` + `LoadPhaseBuilder` / `LoadPhaseSkeleton` |
| An action that runs once per key or waits for a trigger | `ActionPhase` + `PendingActions<K>` + `ActionPhaseBuilder` — `lib/signals/common/action_phase.dart` |
| A button that waits on the backend | `CustomBusyLabel` — `lib/presentation/common/custom_busy_label.dart` |
| A one-shot async load | `guardedFutureSignal` — `lib/signals/common/guarded_future_signal.dart` |
| Offline banner | `NetworkHealthState` — `lib/signals/common/network_health.dart` |
| Boot screen | `BootShell` — `lib/presentation/common/boot_shell.dart` |
| Feature flags | `lib/signals/common/feature_flags.dart` |
| Tab switch | `TabShellScope.open` — `lib/presentation/common/tab_shell_scope.dart` |
| Long-lived stream with recovery | `StreamRecoveryController` — `lib/signals/common/stream_recovery.dart` |
| Image create / edit | `SingleImageUploadState` / `MultiImageUploadState` — `lib/signals/common/image_upload.dart` |
| Multi-step flow (the default for any screen with several choices that scrolls) | `CustomStep` + `step_kit` `WizardState` |
| UI enum with title / icon / colour | `enum X with EnumItem` in `lib/model/enum.dart` |
| Page gutter | `PageBody` / `GutterScope` |
| Vertical rhythm | `CustomSpacedColumn` / `spacedListChildren` |

If the data already lives in a feature or auth signal, derive it with `useComputed` +
`SignalBuilder` — never stack a second query layer on top.

## Checks

`python3 scripts/flutter_signals_check.py --repo <repo>` in this plugin runs the mechanical checks; the plugin's
PostToolUse hook runs the relevant ones on every edited file. Per-repo opt-outs and
baselines live in `<repo>/.claude/flutter-signals.json`.
