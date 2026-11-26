---
name: codegen-slang-mappable
description: Code generation in a slang + dart_mappable Flutter app — which command after which edit (dart run slang after i18n JSON, dart run build_runner build --delete-conflicting-outputs after a @MappableClass), dart run not flutter pub run, the slang builder disabled so the slang CLI owns translations*.g.dart, ${name} placeholders (never {name}), never git checkout generated translations mid-edit, super.<field> in every subclass, committed generated files with a CI diff gate. Use after editing lib/i18n/**/*.i18n.json, a @MappableClass model, build.yaml, or when build_runner throws InvalidOutputException / a translation getter has no arguments.
---

# Codegen: slang + dart_mappable

The two commands are **not interchangeable**:

```bash
dart run slang                                            # after editing lib/i18n/**/*.i18n.json
dart run build_runner build --delete-conflicting-outputs  # after editing a @MappableClass
```

## Non-negotiable rules

1. **`dart run`, never `flutter pub run`** — the flutter wrapper strips
   `--delete-conflicting-outputs` ("options removed and ignored") and the build aborts on
   output conflicts.
2. **The slang CLI owns `translations*.g.dart`.** Disable the `slang_build_runner` builder in
   `build.yaml`; otherwise build_runner throws `InvalidOutputException: Asset already exists`
   and aborts mid-run, leaving subclass mappers half-regenerated.
3. **slang placeholders are `${name}`, not `{name}`.** `{name}` generates a no-argument
   getter and the call site fails to compile — silently until build.
4. **Never `git checkout -- lib/i18n/translations*.g.dart`** to tidy up while i18n source
   edits are uncommitted — it reverts generated keys. Regenerate instead.
5. **Adding a field to a base `@MappableClass`** requires `super.<field>` in every subclass
   constructor (analyzer: `invalid_override`), or `copyWith` drops it.
6. **Generated files are committed**, and CI regenerates and fails on a diff (ignore the
   `/// Built on` timestamp line).
7. **Edit both locales** (e.g. `*_en.i18n.json` and `*_nl.i18n.json`) in the same change;
   keep the JSON two-space formatted.

## Definition of done

- [ ] The right command was run; generated files committed; `flutter analyze` clean.

See the manual runbook `run-codegen` for the full regenerate sequence.
