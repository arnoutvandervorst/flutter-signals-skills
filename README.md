# flutter-signals — skills and checks for signals-based Flutter apps

A Claude Code plugin with **engineering skills** (playbooks the agent loads only when a task
matches) and **convention checks** (a hook that blocks obvious violations right after an
edit, plus the same checks for CI) for Flutter + Firebase apps on:

`signals_flutter` + `signals_hooks` · `flutter_hooks` · `go_router` · `slang` ·
`dart_mappable` · Firebase (Auth, Firestore, Storage, Messaging, Functions v2 in TypeScript)

Shared building blocks for this stack live in their own packages:
[auth_engine](https://github.com/arnoutvandervorst/auth_engine) (auth state machine),
[signals_kit](https://github.com/arnoutvandervorst/signals_kit) (state building blocks),
[invite_kit](https://github.com/arnoutvandervorst/invite_kit) (invites, contacts, QR) and
[step_kit](https://github.com/arnoutvandervorst/step_kit) (wizard state machine). Inspired by
[zakariaf/Flutter-Skills](https://github.com/zakariaf/Flutter-Skills) (Riverpod stack);
the stack-agnostic ideas (async safety, UI states, accessibility, release discipline) are
adapted here — their skills are not installed, because their Riverpod / freezed / gen_l10n
rules contradict this stack.

## Skills

| Skill | Governs |
|---|---|
| `signals-flutter-conventions` | Front door: house rules + which skill to open |
| `signals-state-lifecycle` | State classes own and dispose every signal; `guardedFutureSignal`; no write after dispose; hooks; page slots; test seams |
| `load-phase-ui-states` | `LoadPhase`, loading / error / missing / ready, visible waiting, cache-empty-first, offline banner, boot shell, feedback ladder, Undo |
| `firestore-model-layer` | `BaseModel`, `FirestoreService<T>`, `ackOrQueued`, backend-owned keys, enums |
| `firebase-security-and-cost` | Rules as the boundary, rules tests on the real payload, ruleset size, private data, cost and contention checklist |
| `cloud-functions-v2` | v2 handlers, barrels, idempotency, retry by cadence, deterministic retries, backend i18n, batched deploys, pure decisions + vitest, activity logs |
| `codegen-slang-mappable` | The two codegen commands and their pitfalls |
| `widget-composition-and-layout` | `material_ui`, no default margins, `GutterScope`, `Custom*` widgets |
| `routing-go-router` | Route constants, pure redirects, parked deep links, push for the current viewer only, tab shells |
| `async-safety` | The arrow-callback Future hole, mounted guards, no silent catch, busy state on every backend action, `ActionPhase` / `PendingActions` |
| `testing-strategy` | Lowest layer, seams, contract tests, rules both ways, emulator gate |
| `release-versioning` | `year.month.seq+build`, beta = build bump only, promote never rebuild |
| `accessibility-and-copy` | Copy in slang, semantics, tap targets, text scale |
| `run-codegen`, `run-integration-gate`, `release-beta`, `update-deps`, `store-media`, `nuc-ci-runner` | Manual runbooks (`/…` only) |

## Package updates

`/flutter-signals:update-deps [project…|all]` runs `scripts/deps_update.py`. The script
also works on its own:

```bash
python3 scripts/deps_update.py --all ~/Projects            # report: in range / major / blocked + why
python3 scripts/deps_update.py --apply --verify ~/Projects/app  # take in-range updates, analyze/test
python3 scripts/deps_update.py --apply --majors --native app    # try majors + iOS SPM + Android build
```

For each pub and npm root it lists:
- the in-range updates it takes (lockfile only);
- the majors that resolve but need a constraint edit;
- the blocked updates, each with the solver's own explanation (the `pub add --dry-run`
  chain, or the `npm install --dry-run` peer conflict).

The runbook also updates the global Firebase CLI (`npm install -g --allow-scripts=protobufjs,re2 firebase-tools@latest`),
which no lockfile covers.

Before the projects it reports the installed Flutter SDK: its channel, a newer release on
that channel, and on beta/master whether the latest stable meets each project's
`environment:` floor. For a newer release it lists the commits since the installed revision
(GitHub compare; past 50 commits only the count and the link). It reads Flutter's public
release feed and never upgrades the SDK.

`--native` exists because the pub solver never sees Swift Package Manager or Gradle pins.
iOS is SPM only, and a project that still has an `ios/Podfile` is flagged.

## Checks

`scripts/flutter_signals_check.py` — one rule table, used by the hook and CI:

| Rule | Catches |
|---|---|
| `legacy-material-import` | `package:flutter/material.dart` / `cupertino.dart` |
| `flutter-localizations-import` | `package:flutter_localizations/` |
| `slang-placeholder` | `{name}` instead of `${name}` in `*.i18n.json` |
| `flutter-pub-run` | `flutter pub run <pkg>` in docs, scripts, CI, Fastfiles |
| `raw-route-string` | `context.go('/…')` and friends |
| `build-method` | `Widget _buildX(` in presentation |
| `sdk-ui-in-feature` | a `material_ui` / `cupertino_ui` / `flutter/material` import in presentation outside `common/` |
| `one-widget-per-file` | a second `Widget build(BuildContext` in a presentation file |
| `presentation-text-style` | `TextStyle(`, `textTheme`, `AppText.`, `fontSize:` / `fontWeight:` in presentation outside `common/` |
| `presentation-spacing-literal` | a bare number in `EdgeInsets.*(`, `SizedBox(height:/width: n)` or `spacing: n` outside `common/` |
| `presentation-top-level-helper` | a top-level function in presentation that returns something other than a `Future` / `void` |
| `firestore-in-presentation` | `FirebaseFirestore.instance` in presentation |
| `signal-in-presentation` | `signal(` / `computed(` / `effect(` in presentation |
| `signals-in-services` | signals imports in `lib/services/` |
| `state-without-dispose` | a `lib/signals/` file creating reactive objects with no `dispose(` |
| `deprecated-signals-api` | `Watch(` / `Watch.builder(`, `.watch(context)`, `SignalsMixin` (deprecated in signals_flutter 7; use `SignalBuilder` / `SignalWidget`) |
| `plain-future-signal` | `futureSignal(` in `lib/` outside `guarded_future_signal.dart` |
| `math-random-in-handlers` | `Math.random(` in `functions/src/events/` and `functions/src/**/handlers.ts` (tests excluded) |

Per-repo opt-outs and known offenders: `<repo>/.claude/flutter-signals.json`

```json
{
  "disabled": ["legacy-material-import", "flutter-localizations-import"],
  "baseline": { "lib/presentation/old_page.dart": ["build-method"] },
  "baselineReasons": { "build-method": "predates the rule; convert when touched" }
}
```

Run: `python3 scripts/flutter_signals_check.py --repo <app>` (exit 1 on a violation) or
`--file <path>`. Adopting a new rule in an existing app:
`--write-baseline <rule>[,<rule>] <app>` baselines today's offenders, so the hook blocks only new code. Self-test: `scripts/test_checks.sh`.

## Install in an app

```bash
# From the app's directory: declare the marketplace for the project and enable the plugin
claude plugin marketplace add arnoutvandervorst/flutter-signals-skills --scope project
claude plugin install flutter-signals@flutter-signals --scope project
```

This writes `extraKnownMarketplaces` + `enabledPlugins` into the app's committed
`.claude/settings.json`, so everyone with access to this (private) repo gets the plugin.
Pull updates with `claude plugin marketplace update flutter-signals`. While developing the
plugin itself, `claude --plugin-dir ~/Projects/flutter-signals-skills` loads the working
tree directly.

Validate after changes: `claude plugin validate --strict .claude-plugin/plugin.json`,
`claude plugin validate --strict skills`, `scripts/test_checks.sh`.
