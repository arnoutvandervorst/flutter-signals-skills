# Changelog

Notable changes per release, newest first. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/) (`.claude-plugin/plugin.json`). Each version has a
GitHub release with the same notes.

## [1.12.0] - 2026-11-26

### Added
- `widget-composition-and-layout` rule 10: a screen where the person makes several choices
  and that would scroll is a wizard as the first proposal (one section per screen, segmented
  progress with "step x of n · name", overview and summary, a draft per step shown in the
  wizard and on the action that opens it, presets before free text), built on `step_kit`'s
  `WizardState`. A checklist line in the definition of done.
- `signals-flutter-conventions`: the multi-step primitive is `step_kit` `WizardState`.

## [1.11.1] - 2026-11-26

### Security
- `deps_update.py`: a git dependency's url and the remote's tag names can no longer reach git
  as options. Only https, ssh and git urls are queried (with `--` before the url), only plain
  version tags are kept, and `rev-list` gets `--end-of-options` and a `refs/tags/` range.

## [1.11.0] - 2026-11-26

First public release.

### Added
- `update-deps`: own git packages come first. `deps_update.py` lists each app's git
  dependencies (pinned ref, newest remote tag, untagged local commits, uncommitted changes),
  marks a blocked package whose solver chain names one as "held by own package", and with
  `--all` runs packages before apps. The skill gets step 2b and a checklist line.
- `update-deps`: CI must run the same Flutter SDK as the machine; report a difference and move
  the pin with an SDK upgrade.
- README: links to the shared packages for this stack (`auth_engine`, `signals_kit`,
  `invite_kit`, `step_kit`).

### Changed
- App-specific references replaced by generic wording and examples; runbooks point to the
  app's own `OPERATIONS.md` / release docs for its scripts and paths.

## [1.10.0] - 2026-11-25

### Added
- Buttons within common's bounds: variant, size and palette accent instead of local styles.
- Few font sizes, used everywhere: a fixed small type scale, no per-card variants.

### Changed
- Follow the signals_flutter docs: `SignalBuilder`, not the deprecated `Watch` /
  `.watch(context)`.

## [1.9.0] - 2026-11-24

### Added
- Text and spacing within common's bounds: feature code takes text roles and spacing from the
  common layer.

## [1.8.0] - 2026-11-24

### Added
- Layering rule and checks: feature widget → `Custom*` widget → Material/Cupertino; only the
  common layer imports `material_ui` / `cupertino_ui`; one build method per file.

## [1.7.0] - 2026-11-10

### Added
- Manual runbooks `store-media` (screenshots, demo videos, media site) and `nuc-ci-runner`
  (a self-hosted GitHub Actions runner for CI and Android releases).

## [1.6.1] - 2026-11-05

### Fixed
- `update-deps`: allow the `protobufjs` and `re2` install scripts when updating the global
  Firebase CLI.

## [1.6.0] - 2026-11-05

### Added
- `update-deps`: update the global Firebase CLI too.

## [1.5.0] - 2026-10-31

### Added
- `update-deps`: Flutter SDK channel check, newer release and the change list since the
  installed revision.

## [1.4.0] - 2026-10-25

### Added
- Lessons from two production apps on this stack; checks for a plain `futureSignal` and for
  `Math.random` in backend handlers.

## [1.3.0] - 2026-10-24

### Added
- `update-deps` runbook and `deps_update.py`; iOS through Swift Package Manager only.

## [1.2.0] - 2026-10-22

### Added
- `ActionPhase`: once-per-key backend actions with a visible phase.

## [1.1.0] - 2026-10-08

### Added
- Visible waiting: load-phase and async-safety rules.

## [1.0.0] - 2026-09-24

### Added
- The plugin: skills and convention checks for signals Flutter apps, installable from the
  GitHub marketplace.
