import 'package:flutter/widgets.dart';

String dueText(DateTime day) => '$day';

class First extends StatelessWidget {
  const First({super.key});

  @override
  Widget build(BuildContext context) => Text(dueText(DateTime(2026)));
}

class _Second extends StatelessWidget {
  const _Second();

  @override
  Widget build(BuildContext context) => const Text('second');
}
