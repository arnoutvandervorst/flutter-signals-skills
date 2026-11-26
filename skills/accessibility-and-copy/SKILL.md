---
name: accessibility-and-copy
description: User-facing copy and accessibility in a slang Flutter app — every visible string, tooltip and semantics label from slang (both locales, ${name} placeholders), no inline strings, localized EnumItem titles, semantics labels on icon-only controls, 48x48 tap targets, never clamping the text scaler, colour never the only signal, reduce motion respected, auth e-mails and backend push copy in the user's language, pseudonymous analytics. Adapted from zakariaf/Flutter-Skills accessibility-as-code. Use when adding or changing visible text, buttons, icons, tooltips, error messages, snackbars, or reviewing a screen for accessibility.
---

# Accessibility and copy

## Non-negotiable rules

1. **All user-facing copy lives in slang** (`lib/i18n/**`), in every supported locale, in
   the same change. Never an inline string in a widget — tooltips and semantics labels
   included. Placeholders are `${name}`.
2. **Copy that belongs together stays one key** (don't split a sentence across keys; word
   order differs per language).
3. **Icon-only controls carry a localized tooltip / semantics label.**
4. **Tap targets are at least 48×48** logical pixels.
5. **Never clamp the text scaler** (`withClampedTextScaling`, fixed `textScaleFactor`);
   layouts must survive large text.
6. **Colour is never the only signal** — pair status colour with an icon or text
   (`EnumItem` gives `title` + `iconData` + `color`).
7. **Error copy says what failed and what to do next** — never an exception string.
8. **Analytics parameters carry no personal data** (no e-mail, phone, names).
9. **Copy the app doesn't render follows the same rules.** Push and inbox text comes from
   the backend's slang (`functions/i18n`, see `cloud-functions-v2`). Firebase Auth e-mails
   (verify, reset) go out in the app's language: call
   `FirebaseAuth.setLanguageCode(LocaleSettings.currentLocale.languageCode)` before each one.
10. **Respect reduce motion** (`MediaQuery.disableAnimations`): crossfades and auto-advances
    become instant.
11. **An empty avatar shows initials on a colour seeded per user**, never a blank circle and
    never the brand mark for someone else.

## Definition of done

- [ ] No new inline strings; both locales updated; `dart run slang` run.
- [ ] Icon-only controls labelled; large-text check done on the new screen.

Reference: `lib/services/auth/firebase.dart` (`_useAppLanguage`);
`lib/presentation/home/home_vote_recap.dart` (reduce motion).
