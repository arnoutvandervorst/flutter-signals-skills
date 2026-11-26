class LoaderState {
  final profile = futureSignal(() async => 1);
  void dispose() => profile.dispose();
}
