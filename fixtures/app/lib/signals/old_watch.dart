import 'package:signals_flutter/signals_flutter.dart';

// Deprecated in signals_flutter 7: a rebuild belongs in SignalBuilder.
final old = Watch((context) => const SizedBox());
