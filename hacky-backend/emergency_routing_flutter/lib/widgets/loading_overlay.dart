import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../providers/prediction_provider.dart';
import '../config/theme.dart';

class LoadingOverlay extends ConsumerWidget {
  const LoadingOverlay({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isLoading = ref.watch(isLoadingProvider);
    if (!isLoading) return const SizedBox.shrink();

    return Stack(
      children: [
        const ModalBarrier(color: Colors.black54, dismissible: false),
        Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(color: kAccent, strokeWidth: 3),
              const SizedBox(height: 16),
              const Text('Running LSTM+GCN inference...', style: TextStyle(color: kTextSecondary, fontSize: 13)),
              const SizedBox(height: 4),
              const Text('Model 1 — Spatiotemporal Prediction', style: TextStyle(color: kTextSecondary, fontSize: 11)),
            ],
          ),
        ),
      ],
    ).animate().fadeIn(duration: 150.ms);
  }
}
