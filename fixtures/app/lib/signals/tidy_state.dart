class TidyState {
  final count = signal(0);
  void dispose() => count.dispose();
}
