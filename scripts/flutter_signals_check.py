#!/usr/bin/env python3
"""Mechanical checks for signals-stack Flutter apps (flutter-signals plugin).

Modes:
  flutter_signals_check.py --repo DIR      check every in-scope file of a repo (CI / local)
  flutter_signals_check.py --file PATH     check one file (finds the repo via pubspec.yaml)
  flutter_signals_check.py --write-baseline RULE[,RULE] DIR
                                           baseline every current offender of new rules, so
                                           they block only new code (adopting a rule)
  flutter_signals_check.py --hook          PostToolUse hook: reads the tool JSON on stdin,
                                           prints {"decision":"block","reason":...} on violations

Per-repo config: <repo>/.claude/flutter-signals.json
  {
    "disabled": ["legacy-material-import"],          # rules this repo opts out of
    "baseline": {"lib/a.dart": ["build-method"]}      # known offenders, with a reason in git history
  }

Each rule is a promise kept forever: textually decidable, anchored to a structure,
silent when broken. Taste does not belong here — false positives get a gate deleted.
Exit code 1 when a violation is found (repo / file mode).
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

GENERATED = ("*.g.dart", "*.mapper.dart", "*.freezed.dart", "*.gr.dart")
SKIP_DIRS = {".dart_tool", "build", "node_modules", ".git", "graphify-out", "ios", "android",
             "macos", "windows", "linux", "web", "site", ".docs-build", "coverage"}


@dataclass(frozen=True)
class Rule:
    id: str
    why: str
    scope: tuple[str, ...]            # glob patterns relative to the repo root
    pattern: str | None = None        # line regex, matched on comment-stripped lines
    file_check: Callable[[str, "Context"], list[int]] | None = None  # whole-file check -> lines
    strip_comments: bool = True
    exclude: tuple[str, ...] = ()     # glob patterns carved out of scope


@dataclass
class Context:
    package: str


def dart_code(line: str) -> str:
    """The line without a // comment (keeps it dependency-free; URLs in strings also lose
    their tail, so never anchor a rule inside a URL-shaped string)."""
    index = line.find("//")
    return line if index < 0 else line[:index]


def signals_in_services(text: str, ctx: Context) -> list[int]:
    needle = re.compile(
        rf"^\s*import\s+['\"]package:(signals(_flutter|_hooks)?|{re.escape(ctx.package)}/signals)/"
    )
    return [i for i, line in enumerate(text.splitlines(), 1) if needle.search(dart_code(line))]


CREATES_REACTIVE = re.compile(r"(?<![\w.])(signal|computed|effect|streamSignal|futureSignal)\s*(<[^>]*>)?\s*\(")


def state_without_dispose(text: str, ctx: Context) -> list[int]:
    code = "\n".join(dart_code(line) for line in text.splitlines())
    if not CREATES_REACTIVE.search(code) or re.search(r"\bdispose\s*\(", code):
        return []
    first = next(i for i, line in enumerate(text.splitlines(), 1) if CREATES_REACTIVE.search(dart_code(line)))
    return [first]


BUILD_METHOD = re.compile(r"\bWidget\s+build\s*\(\s*BuildContext\b")


def more_than_one_build(text: str, ctx: Context) -> list[int]:
    hits = [i for i, line in enumerate(text.splitlines(), 1) if BUILD_METHOD.search(dart_code(line))]
    return hits[1:]


# A top-level function that returns something other than a Future / void: a helper that
# derives a text, colour or widget above the widget instead of in an extension or widget file.
TOP_LEVEL_HELPER = (
    r"^(?!(?:class|abstract|sealed|final|base|interface|mixin|enum|extension|typedef|import|export"
    r"|part|library|const|var|late|external|static|Future|FutureOr|void|return|if|for|while|switch)\b)"
    r"(?:[A-Za-z_][\w<>?,. ]*|\([^)]*\)\??)\s+[a-z_]\w*\s*(?:<[^>]*>)?\s*\("
)

SDK_UI_IMPORT = r"^\s*import\s+['\"]package:(material_ui/|cupertino_ui/|flutter/(material|cupertino)\.dart)"

TEXT_STYLE = r"\bTextStyle\s*\(|\btextTheme\b|\bAppText\.|\bfontSize\s*:|\bfontWeight\s*:"
SPACING_LITERAL = (
    r"\bEdgeInsets\.\w+\([^)]*?(?<![\w.])[1-9]\d*(\.\d+)?\b"
    r"|\bSizedBox\(\s*(height|width)\s*:\s*[1-9]\d*(\.\d+)?\s*\)"
    r"|\bspacing\s*:\s*[1-9]\d*(\.\d+)?\b"
)

RULES: tuple[Rule, ...] = (
    Rule(
        "presentation-text-style",
        "feature text takes the common text widget's roles and tones (e.g. CustomText(role:, tone:)), "
        "not a TextStyle, textTheme, size or weight of its own — style within common's bounds. A role "
        "that's missing? Ask the owner to extend the common text widget",
        ("lib/presentation/**/*.dart",),
        TEXT_STYLE,
        exclude=("lib/presentation/common/**",),
    ),
    Rule(
        "presentation-spacing-literal",
        "spacing comes from the app's spacing tokens (e.g. AppSize.space16), not a bare number, so "
        "every gap sits on one scale",
        ("lib/presentation/**/*.dart",),
        SPACING_LITERAL,
        exclude=("lib/presentation/common/**",),
    ),
    Rule(
        "sdk-ui-in-feature",
        "feature widgets build on Custom* widgets from lib/presentation/common; only those talk to "
        "Material/Cupertino, so an SDK change touches common alone. Import package:flutter/widgets.dart "
        "and common.dart (Icons is re-exported there). A Custom* widget does it or nearly does? Ask the "
        "owner to extend it; none fits? Ask before adding one",
        ("lib/presentation/**/*.dart",),
        SDK_UI_IMPORT,
        exclude=("lib/presentation/common/**",),
    ),
    Rule(
        "one-widget-per-file",
        "one build method per file — move this widget to its own file (public, named after the "
        "file) so it can be imported, reused and tested on its own",
        ("lib/presentation/**/*.dart",),
        file_check=more_than_one_build,
    ),
    Rule(
        "presentation-top-level-helper",
        "no helper functions above a widget: check lib/extensions/ first, then put text, colour or "
        "state derived from a model in an extension method there, and a piece of UI in its own widget "
        "file. Only navigation entry points (Future / void showX, openX) stay top-level",
        ("lib/presentation/**/*.dart",),
        TOP_LEVEL_HELPER,
    ),
    Rule(
        "legacy-material-import",
        "import material_ui / cupertino_ui, not flutter/material.dart or flutter/cupertino.dart "
        "— they define different types (ThemeData, TabController…) and mixing them breaks at the boundary",
        ("lib/**/*.dart", "test/**/*.dart", "integration_test/**/*.dart"),
        r"^\s*import\s+['\"]package:flutter/(material|cupertino)\.dart['\"]",
    ),
    Rule(
        "flutter-localizations-import",
        "localization delegates come from material_ui (GlobalMaterialLocalizations.delegates), "
        "not flutter_localizations",
        ("lib/**/*.dart",),
        r"^\s*import\s+['\"]package:flutter_localizations/",
    ),
    Rule(
        "slang-placeholder",
        "slang placeholders are ${name}, not {name} — {name} generates a no-argument getter and "
        "the call site fails to compile",
        ("lib/i18n/**/*.i18n.json",),
        r"(?<![$\\])\{[A-Za-z_][A-Za-z0-9_]*(:\s*[A-Za-z<>?]+)?\}",
        strip_comments=False,
    ),
    Rule(
        "flutter-pub-run",
        "use `dart run`, not `flutter pub run` — the flutter wrapper strips "
        "--delete-conflicting-outputs and the build aborts on output conflicts",
        ("**/*.md", "**/*.sh", "Makefile", ".github/workflows/*.yml", "**/Fastfile", "**/*.rb"),
        r"\bflutter\s+pub\s+run\s+[a-z_]",  # a command, not the rule's own explanation
        strip_comments=False,
    ),
    Rule(
        "raw-route-string",
        "navigate by RouteData constant (goNamed(kXRoute.name)), never a raw path string",
        ("lib/**/*.dart",),
        r"\.(go|push|replace|pushReplacement)\(\s*['\"]/",
    ),
    Rule(
        "build-method",
        "extract a widget class instead of a _buildX() method — classes get const, their own "
        "rebuild scope and a name in the inspector",
        ("lib/presentation/**/*.dart",),
        r"\bWidget\s+_build[A-Z]\w*\s*\(",
    ),
    Rule(
        "firestore-in-presentation",
        "presentation renders only — Firestore goes through a state class and FirestoreService<T>",
        ("lib/presentation/**/*.dart",),
        r"\bFirebaseFirestore\.instance\b",
    ),
    Rule(
        "signal-in-presentation",
        "widgets don't create signals/computeds/effects (never disposed); use hooks "
        "(useComputed, useSignal) or a state class",
        ("lib/presentation/**/*.dart",),
        r"(?<![\w.])(signal|computed|effect)\s*(<[^>]*>)?\s*\(",
    ),
    Rule(
        "signals-in-services",
        "the services layer does not depend on signals — state lives in lib/signals/",
        ("lib/services/**/*.dart",),
        file_check=signals_in_services,
    ),
    Rule(
        "state-without-dispose",
        "a state class that creates signals/computeds/effects must dispose them in dispose()",
        ("lib/signals/**/*.dart",),
        file_check=state_without_dispose,
    ),
    Rule(
        "plain-future-signal",
        "create FutureSignals with guardedFutureSignal — signals_core 7 writes a load that lands "
        "after dispose into the disposed signal (SignalsWriteAfterDisposeError, signals.dart#507)",
        ("lib/**/*.dart",),
        r"(?<![\w.])futureSignal\s*[<(]",
        exclude=("lib/signals/common/guarded_future_signal.dart",),
    ),
    Rule(
        "deprecated-signals-api",
        "signals_flutter 7 deprecates Watch / Watch.builder, .watch(context) and SignalsMixin — use "
        "SignalBuilder(builder:) for a local rebuild or extend SignalWidget "
        "(https://dartsignals.dev/packages/signals_flutter/)",
        ("lib/**/*.dart", "test/**/*.dart"),
        r"(?<![\w.])Watch(\.builder)?(<[^>]*>)?\(|\.watch\(\s*context\b|\bSignalsMixin\b",
    ),
    Rule(
        "math-random-in-handlers",
        "triggers are delivered at least once and retried — a retry must decide the same, so use "
        "a seeded shuffle / deterministic choice, never Math.random()",
        ("functions/src/events/**/*.ts", "functions/src/**/handlers.ts"),
        r"(?<![\w.])Math\.random\s*\(",
        exclude=("**/*.test.ts",),
    ),
)


def find_repo(path: Path) -> Path | None:
    for parent in [path, *path.parents]:
        if (parent / "pubspec.yaml").is_file():
            return parent
    return None


def load_config(repo: Path) -> dict:
    config = repo / ".claude" / "flutter-signals.json"
    if not config.is_file():
        return {}
    try:
        return json.loads(config.read_text())
    except (OSError, ValueError):
        return {}


def package_name(repo: Path) -> str:
    match = re.search(r"^name:\s*(\S+)", (repo / "pubspec.yaml").read_text(), re.MULTILINE)
    return match.group(1) if match else ""


def matches(rel: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(rel, pattern):
            return True
        # "lib/**/*.dart" should also match "lib/a.dart" (zero directories).
        if "/**/" in pattern and fnmatch.fnmatch(rel, pattern.replace("/**/", "/")):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(rel, pattern[3:]):
            return True
    return False


def check_file(repo: Path, file: Path, config: dict, ctx: Context) -> list[str]:
    rel = file.relative_to(repo).as_posix()
    if any(fnmatch.fnmatch(file.name, g) for g in GENERATED):
        return []
    disabled = set(config.get("disabled", []))
    baseline = set(config.get("baseline", {}).get(rel, []))
    rules = [r for r in RULES if r.id not in disabled and r.id not in baseline and matches(rel, r.scope)
             and not matches(rel, r.exclude)]
    if not rules:
        return []
    try:
        text = file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    findings: list[str] = []
    lines = text.splitlines()
    for rule in rules:
        if rule.file_check is not None:
            hits = rule.file_check(text, ctx)
        else:
            regex = re.compile(rule.pattern or "")
            hits = [
                i for i, line in enumerate(lines, 1)
                if regex.search(dart_code(line) if rule.strip_comments else line)
            ]
        findings += [f"{rel}:{i}: [{rule.id}] {rule.why}" for i in hits]
    return findings


def iter_files(repo: Path):
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(repo).parts
        if any(part in SKIP_DIRS for part in rel_parts[:-1]):
            continue
        yield path


def run_repo(repo: Path) -> int:
    config, ctx = load_config(repo), Context(package_name(repo))
    findings = [f for file in iter_files(repo) for f in check_file(repo, file, config, ctx)]
    for finding in sorted(findings):
        print(finding)
    print(f"flutter-signals: {len(findings)} violation(s) in {repo}", file=sys.stderr)
    return 1 if findings else 0


def run_file(path: Path) -> list[str]:
    path = path.resolve()
    repo = find_repo(path.parent)
    if repo is None or not path.is_file():
        return []
    return check_file(repo, path, load_config(repo), Context(package_name(repo)))


def run_hook() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not file_path:
        return 0
    findings = run_file(Path(file_path))
    if findings:
        reason = (
            "flutter-signals checks found a convention violation in the file you just wrote. "
            "Fix it (or, if it is a deliberate exception, add it to .claude/flutter-signals.json "
            "`baseline` with the owner's agreement):\n" + "\n".join(findings)
        )
        print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def write_baseline(repo: Path, rule_ids: list[str]) -> int:
    """Baselines every current offender of [rule_ids], so a new rule blocks only new code."""
    path = repo / ".claude" / "flutter-signals.json"
    config = load_config(repo)
    baseline: dict[str, list[str]] = config.setdefault("baseline", {})
    probe = {**config, "baseline": {}, "disabled": [r.id for r in RULES if r.id not in rule_ids]}
    ctx, added = Context(package_name(repo)), 0
    for file in iter_files(repo):
        for finding in check_file(repo, file, probe, ctx):
            rel = finding.split(":", 1)[0]
            rule = finding.split(": [", 1)[1].split("]", 1)[0]
            if rule not in baseline.setdefault(rel, []):
                baseline[rel].append(rule)
                added += 1
    reasons = config.setdefault("baselineReasons", {})
    for rule in rule_ids:
        reasons.setdefault(rule, "predates the rule; convert the file when you next touch it, then drop it here")
    config["baseline"] = dict(sorted(baseline.items()))
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    print(f"flutter-signals: baselined {added} offender(s) of {', '.join(rule_ids)} in {path}", file=sys.stderr)
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["--hook"]:
        return run_hook()
    if len(argv) == 3 and argv[0] == "--write-baseline":
        return write_baseline(Path(argv[2]).resolve(), argv[1].split(","))
    if len(argv) == 2 and argv[0] == "--repo":
        return run_repo(Path(argv[1]).resolve())
    if len(argv) >= 2 and argv[0] == "--strict":
        # Ignores the baseline: is this file really converted? (adopting a rule file by file)
        findings = []
        for arg in argv[1:]:
            path = Path(arg).resolve()
            repo = find_repo(path.parent)
            if repo is not None and path.is_file():
                config = {**load_config(repo), "baseline": {}}
                findings += check_file(repo, path, config, Context(package_name(repo)))
        print("\n".join(findings)) if findings else None
        return 1 if findings else 0
    if len(argv) == 2 and argv[0] == "--file":
        findings = run_file(Path(argv[1]))
        print("\n".join(findings)) if findings else None
        return 1 if findings else 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
