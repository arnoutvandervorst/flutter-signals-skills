---
name: widget-composition-and-layout
description: UI composition rules for a signals + flutter_hooks app — layers (feature widget → Custom* common widget → Material/Cupertino; only common imports material_ui), reuse first (extend a near-fit Custom* widget or ask before adding one), one widget per file, rendering helpers as extension methods, HookWidget that only renders, material_ui / cupertino_ui imports instead of flutter/material.dart (useTabControllerUi, no compatibility bridge) in apps that migrated, reusable Custom* widgets with no default outer margin (the parent owns vertical rhythm), the page gutter applied exactly once through PageBody / GutterScope, vertical rhythm through CustomSpacedColumn, extracted widget classes instead of _buildX() methods, model-driven tile blueprint, every new shared widget in the gallery test. Use when building or refactoring a screen, tile or shared widget, touching padding/margins/gutters, importing Material/Cupertino, or adding to lib/presentation/common.
---

# Widget composition and layout

## Layers and reuse (read first)

```
feature widget (lib/presentation/<feature>/)  →  Custom<Widget> (lib/presentation/common/)  →  Material / Cupertino / SDK
```

**Only `Custom*` widgets talk to Material/Cupertino.** A feature widget imports
`package:flutter/widgets.dart` and `common.dart` (which re-exports `Icons` / `IconData`), and its
build method is an implementation of one or more `Custom*` widgets. When the SDK changes, only
the common layer moves; and every piece of UI the app shows is a common widget with a gallery
test, so the UI stays testable instead of growing wild.

Before you build any UI, in this order:

1. **Look in `lib/presentation/common/` (and its gallery test) for a widget that does it.** Use it.
2. **One does it nearly?** Ask the owner whether to extend that widget (a parameter, a slot).
   Do not copy its styling into a feature widget.
3. **Nothing fits?** Ask the owner whether to add a new `Custom*` widget. Only after a yes: build
   it in common (named `Custom<What>`, never after a look or brand), add it to the gallery test,
   then build the feature widget on top of it by importing it.
4. **Need a function to render something** (a due text, a colour, a label)? Look in
   `lib/extensions/` first; add an extension method on the model there if none exists. No helper
   functions above a widget; only navigation entry points (`Future`/`void` `showX`, `openX`) may
   be top-level.
5. **Style within common's bounds.** Text is the common text widget with a role and a tone
   (e.g. `CustomText('…', role: title, tone: muted)`), never a `TextStyle`, `textTheme`, size or
   weight of its own; condensed capitals and figures are the common heading / figure widgets.
   **Few font sizes, used everywhere.** The common text roles are the app's whole type scale (a
   handful of fixed sizes); pick the nearest role, never a size of its own, and don't add a role
   or a "large" variant of a widget to make one card stand out. Cards of the same kind (a quest,
   a challenge, a task tile) share sizes; emphasis comes from colour, weight or placement. A
   growing set of sizes makes the app read like a tabloid (owner).
   Spacing is a token from the app's scale (e.g. `AppSize.space16`), never a bare number. A button
   is the common button with a variant, a size and at most a palette accent — never a colour,
   shape, padding or text style of its own; a screen with its own palette sets it once in a scope. A role,
   tone or step that's missing: ask the owner to extend common.
6. **One widget (one build method) per file**, public, named after the file — no private
   `_Row` / `_Dots` next to the main widget: those are their own files, importable and testable.

Existing code that predates these rules sits in the repo's baseline; convert a file when you
touch it, then drop it from the baseline.

## Non-negotiable rules

1. **Widgets render; state lives elsewhere.** `HookWidget` + `useMemoized` / `useEffect` /
   `useComputed` / `SignalBuilder`. No Firestore, no business logic, no inline copy (slang).
2. **Material/Cupertino via the decoupled packages** (apps that migrated):
   `package:material_ui/material_ui.dart` and `package:cupertino_ui/cupertino_ui.dart`,
   never `package:flutter/material.dart` / `cupertino.dart` — they define *different types*
   and mixing them is a compile error at the boundary. `flutter_hooks`' `useTabController`
   returns the legacy type: use `useTabControllerUi`. Localization delegates come from
   `material_ui`. Do **not** wrap the app in `MaterialUiCompatibilityBridge` (it changes the
   ambient `IconTheme` and `IconButton.filled` goes black). Non-widget code imports
   `package:flutter/widgets.dart`.
3. **Reusable widgets carry no default outer margin** — the parent owns vertical rhythm
   (`Column(spacing:)`, gap widgets, or an explicit `margin:` at the call site). Hidden
   default margins make every gap an invisible sum that breaks on the next UI change.
4. **The page gutter is applied exactly once, structurally.** `PageBody` applies it and
   wraps its child in `GutterScope.applied`; a widget that wants a gutter asks
   `GutterScope.horizontalOf(context)` / `paddingOf(context)`, which returns 0 inside an
   already-inset subtree. Never hardcode the gutter; code that must, calls
   `GutterScope.debugAssertNotApplied(context, 'Widget')`. (A doubled gutter looks plausible
   until two screens are compared.)
5. **Extract widget classes, not `_buildX()` methods** — classes get `const`, their own
   rebuild scope and a name in the inspector.
6. **Model-driven tiles follow the tile blueprint:** `useMemoized` create →
   `useEffect` dispose → `useComputed` view model → `SignalBuilder` render; a tile that only formats
   an already-loaded model stays a plain widget.
7. **Shared widgets are named `Custom*`** and live in `lib/presentation/common/`; a new one
   is added to the gallery test in the same change (a coverage test fails otherwise).
8. **UI enums render through `EnumItem`** (`title`, `iconData`, `color`), never a
   widget-local switch.
9. **Vertical rhythm through `CustomSpacedColumn` / `spacedListChildren`**, on a fixed
   scale (16 between sections, 8 / 12 inside). They skip the gap around a child that
   renders nothing, so a hidden section never leaves a double gap. Pinned by a
   vertical-spacing test.
10. **Several choices that make the screen scroll → a wizard, as the first proposal.** A
    form, check-in, journal, intake or completion where the person makes more than one
    choice and the whole does not fit on one phone screen is presented as a wizard: one
    section per screen, the progress on top (one segment per step plus "step 2 of 4 ·
    name", never labelled pills, they run out of room), an overview before when it can be
    left halfway, a summary with Edit per section after. Each step saves a draft where the
    data allows it, the wizard says so ("draft saved · 10:21") and the action that opens it
    shows the task as in progress, not done, until Done. Presets before free text. The
    behaviour comes from the shared wizard state (`step_kit` `WizardState`: required steps
    checked live, skip, save per step, resume, jumps); the app only draws it, with the
    header on its tab's floor. A long single page is the exception, argued in the change,
    for screens that are read rather than filled in.

## Definition of done

- [ ] Feature widgets import `flutter/widgets.dart` + `common.dart` only; Material/Cupertino stays in common.
- [ ] Existing `Custom*` widgets reused; a near-fit extended or a new one added only after the owner said yes.
- [ ] One build method per file; rendering helpers are extension methods (existing ones reused).
- [ ] Text through the common text widget (role + tone); spacing from the token scale.
- [ ] No legacy Material import; no `_buildX()`; no hardcoded gutter.
- [ ] New shared widget in the gallery test (light and dark).
- [ ] A screen with several choices that scrolls is a wizard (rule 10), or the change says why not.
- [ ] `flutter analyze` clean.

Reference: `lib/presentation/common/gutter_scope.dart`, `page_body.dart`,
`lib/presentation/user_auth/user_auth_tile.dart`, `lib/presentation/coin/coin_tile.dart`,
`lib/presentation/common/hooks/use_tab_controller.dart`, `lib/presentation/common/custom_spaced_column.dart`,
`test/widget/common_gallery_test.dart`, `test/widget/vertical_spacing_test.dart`.
