class LeakyState {
  final count = signal(0);
  late final doubled = computed(() => count.value * 2);
}
