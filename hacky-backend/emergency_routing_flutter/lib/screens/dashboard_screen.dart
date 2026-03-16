import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/prediction_provider.dart';
import '../providers/health_provider.dart';
import '../config/theme.dart';
import '../widgets/congestion_card.dart';
import '../widgets/loading_overlay.dart';
import '../config/cities_config.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  Future<void> _handleBatchPredict(WidgetRef ref) async {
    ref.read(isLoadingProvider.notifier).setLoading(true);
    try {
      final results = await ref.read(model1ServiceProvider).predictBatch(['Delhi', 'Mumbai', 'Bengaluru', 'Chennai', 'Patna']);
      ref.read(predictionsProvider.notifier).setBatch(results);
      ref.read(lastUpdatedProvider.notifier).update();
    } catch (e) {
      ref.read(appErrorProvider.notifier).setError(e.toString());
    } finally {
      ref.read(isLoadingProvider.notifier).setLoading(false);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final predictions = ref.watch(predictionsProvider);
    final isLoading = ref.watch(isLoadingProvider);
    final modelInfo = ref.watch(modelInfoStateProvider);

    return Scaffold(
      backgroundColor: kBackground,
      body: Stack(
        children: [
          SafeArea(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('City Dashboard', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 20, color: Colors.white)),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(colors: [kEmergencyOrange, Color(0xFFFF3D00)]),
                      borderRadius: BorderRadius.circular(12),
                      boxShadow: [BoxShadow(color: kEmergencyOrange.withOpacity(0.3), blurRadius: 12, offset: const Offset(0, 4))],
                    ),
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.transparent,
                        shadowColor: Colors.transparent,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      onPressed: () => _handleBatchPredict(ref),
                      child: isLoading
                          ? const Row(mainAxisAlignment: MainAxisAlignment.center, children: [SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)), SizedBox(width: 8), Text('Running AI models...', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold))])
                          : const Row(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(Icons.bolt, color: Colors.white, size: 18), SizedBox(width: 8), Text('PREDICT ALL CITIES', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15, letterSpacing: 1))]),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                if (predictions.isNotEmpty)
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Row(
                      children: kCities.map((c) {
                        final pred = predictions[c.name];
                        if (pred == null) return const SizedBox.shrink();
                        final color = getCongestionColor(pred.congestionT5);
                        return GestureDetector(
                          onTap: () {
                            ref.read(selectedCityProvider.notifier).select(c);
                            // Navigate to tab 0 (Map) handled natively by users normally
                          },
                          child: Container(
                            width: 60, height: 60, margin: const EdgeInsets.only(right: 8),
                            decoration: BoxDecoration(
                              color: color.withOpacity(0.2),
                              border: Border.all(color: color),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(c.name[0], style: TextStyle(fontWeight: FontWeight.bold, fontSize: 20, color: color)),
                                Container(width: 8, height: 8, decoration: BoxDecoration(shape: BoxShape.circle, color: color)),
                              ],
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                const SizedBox(height: 12),
                if (predictions.isEmpty && !isLoading)
                  const Expanded(
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.bolt, color: kTextSecondary, size: 64),
                          Text('Tap Predict All Cities', style: TextStyle(color: kTextSecondary)),
                        ],
                      ),
                    ),
                  )
                else
                  Expanded(
                    child: ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        ...predictions.values.map((p) => Padding(padding: const EdgeInsets.only(bottom: 12), child: CongestionCard(p))),
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(color: kCardBg, border: Border.all(color: kCardBorder), borderRadius: BorderRadius.circular(16)),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(children: [Text('🧠 Model Architecture', style: TextStyle(color: kAccent, fontSize: 14, fontWeight: FontWeight.bold))]),
                              const Divider(color: kCardBorder),
                              _infoRow('Model', modelInfo?.modelName ?? '—'),
                              _infoRow('Parameters', modelInfo?.parameterCount.toString() ?? '—'),
                              _infoRow('LSTM Hidden', modelInfo?.lstmHiddenSize.toString() ?? '—'),
                              _infoRow('GCN Hidden', modelInfo?.gcnHiddenDim.toString() ?? '—'),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                        Opacity(
                          opacity: 0.4,
                          child: Container(
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(color: kCardBg, border: Border.all(color: kCardBorder), borderRadius: BorderRadius.circular(16)),
                            child: const Row(
                              children: [
                                Icon(Icons.lock, color: kTextSecondary),
                                SizedBox(width: 8),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text('Route Reliability Scaling', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                                    Text('Model 2 — Coming Soon', style: TextStyle(color: kTextSecondary, fontSize: 12)),
                                  ],
                                )
                              ],
                            ),
                          ),
                        )
                      ],
                    ),
                  )
              ],
            ),
          ),
          const LoadingOverlay(),
        ],
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: kTextSecondary)),
          Text(value, style: const TextStyle(color: kAccent, fontFamily: 'monospace')),
        ],
      ),
    );
  }
}
