import 'package:flutter/widgets.dart';
import 'package:flutter_hooks/flutter_hooks.dart';

// import 'package:flutter/material.dart';  (commented out: must not count)
class GoodWidget extends HookWidget {
  const GoodWidget({super.key});

  @override
  Widget build(BuildContext context) {
    final label = useComputed(() => 'ok');
    return Text(label.value);
  }
}

/// A navigation entry point may stay top-level.
Future<void> showGood(BuildContext context) async {}
