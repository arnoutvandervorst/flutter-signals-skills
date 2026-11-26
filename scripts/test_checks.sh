#!/usr/bin/env bash
# Self-test: every rule fires on the fixture app exactly where expected, nothing else
# fires, and the PostToolUse hook blocks an offending file and stays silent otherwise.
set -euo pipefail
cd "$(dirname "$0")/.."
CHECK="python3 scripts/flutter_signals_check.py"
fail=0
expect() { # expect "<rule> <rel-path>:<line>"
  if ! grep -qF "$2: [$1]" <<<"$OUT"; then echo "MISSING: $1 at $2"; fail=1; fi
}
OUT="$($CHECK --repo fixtures/app 2>/dev/null || true)"
expect legacy-material-import      lib/presentation/bad_widget.dart:1
expect build-method                lib/presentation/bad_widget.dart:7
expect signal-in-presentation      lib/presentation/bad_widget.dart:11
expect firestore-in-presentation   lib/presentation/bad_widget.dart:12
expect raw-route-string            lib/presentation/bad_widget.dart:13
expect signals-in-services         lib/services/bad_service.dart:1
expect signals-in-services         lib/services/bad_service.dart:2
expect state-without-dispose       lib/signals/leaky_state.dart:2
expect slang-placeholder           lib/i18n/strings_en.i18n.json:3
expect flutter-pub-run             README.md:3
expect plain-future-signal         lib/signals/loader_state.dart:2
expect math-random-in-handlers     functions/src/events/on_create.ts:2
expect sdk-ui-in-feature           lib/presentation/bad_widget.dart:1
expect one-widget-per-file         lib/presentation/two_widgets.dart:16
expect presentation-top-level-helper lib/presentation/two_widgets.dart:3
expect presentation-spacing-literal lib/presentation/styled_widget.dart:8
expect presentation-text-style lib/presentation/styled_widget.dart:9
expect deprecated-signals-api     lib/signals/old_watch.dart:4
count=$(grep -c ": \[" <<<"$OUT" || true)
if [ "$count" -ne 18 ]; then echo "EXPECTED 18 findings, got $count:"; echo "$OUT"; fail=1; fi

# Hook: offending file -> block JSON; clean file -> nothing; non-Flutter path -> nothing.
hook() { printf '{"tool_input":{"file_path":"%s"}}' "$1" | $CHECK --hook; }
grep -q '"decision": "block"' <<<"$(hook "$PWD/fixtures/app/lib/presentation/bad_widget.dart")" || { echo "HOOK did not block"; fail=1; }
[ -z "$(hook "$PWD/fixtures/app/lib/presentation/good_widget.dart")" ] || { echo "HOOK blocked a clean file"; fail=1; }
[ -z "$(hook "$PWD/fixtures/app/lib/presentation/common/custom_label.dart")" ] || { echo "HOOK blocked Material in common"; fail=1; }
[ -z "$(hook "/tmp/not-a-flutter-project/x.dart")" ] || { echo "HOOK fired outside Flutter"; fail=1; }

[ "$fail" -eq 0 ] && echo "flutter-signals self-test: OK" || { echo "flutter-signals self-test: FAILED"; exit 1; }
