---
name: run-codegen
description: Manual runbook to regenerate slang translations and dart_mappable mappers in the right order and verify nothing unexpected changed.
disable-model-invocation: true
---

# Run codegen

1. After i18n edits: `dart run slang`.
2. After model edits: `dart run build_runner build --delete-conflicting-outputs`
   (never `flutter pub run`).
3. `git status --short lib/` — only the expected `*.g.dart` / `*.mapper.dart` changed.
   An unexpected mapper diff means a subclass is missing `super.<field>`.
4. `flutter analyze` clean.
5. Commit the generated files with the source change.
