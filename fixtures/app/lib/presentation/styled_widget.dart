import 'package:flutter/widgets.dart';

class StyledWidget extends StatelessWidget {
  const StyledWidget({super.key});

  @override
  Widget build(BuildContext context) => const Padding(
    padding: EdgeInsets.all(16),
    child: Text('x', style: TextStyle(fontSize: 13)),
  );
}
