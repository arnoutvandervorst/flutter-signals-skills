import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class BadWidget extends StatelessWidget {
  const BadWidget({super.key});

  Widget _buildTitle() => const Text('x');

  @override
  Widget build(BuildContext context) {
    final count = computed(() => 1);
    FirebaseFirestore.instance.collection('x');
    context.go('/home');
    return _buildTitle();
  }
}
