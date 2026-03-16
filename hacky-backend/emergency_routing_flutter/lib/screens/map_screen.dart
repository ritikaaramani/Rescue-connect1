import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/health_provider.dart';
import '../providers/prediction_provider.dart';
import '../config/theme.dart';
import '../widgets/alert_banner.dart';
import '../widgets/city_selector.dart';
import '../widgets/map_widget.dart';
import '../widgets/congestion_card.dart';
import '../widgets/congestion_chart.dart';
import '../widgets/loading_overlay.dart';

class MapScreen extends ConsumerStatefulWidget {
  const MapScreen({super.key});

  @override
  ConsumerState<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends ConsumerState<MapScreen> {
  Timer? _refreshTimer;
  int _countdown = 30;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(healthStateProvider.notifier).fetch();
      ref.read(modelInfoStateProvider.notifier).fetch();
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _handlePredict(String cityName) async {
    ref.read(isLoadingProvider.notifier).setLoading(true);
    try {
      final result = await ref.read(model1ServiceProvider).predictCity(cityName);
      ref.read(predictionsProvider.notifier).setPrediction(cityName, result);
      ref.read(lastUpdatedProvider.notifier).update();
    } catch (e) {
      ref.read(appErrorProvider.notifier).setError(e.toString());
      Future.delayed(const Duration(seconds: 4), () {
        if (mounted) ref.read(appErrorProvider.notifier).setError(null);
      });
    } finally {
      ref.read(isLoadingProvider.notifier).setLoading(false);
    }
  }

  void _manageAutoRefresh(bool autoRefresh) {
    if (autoRefresh) {
      if (_refreshTimer == null || !_refreshTimer!.isActive) {
        _countdown = 30;
        _refreshTimer = Timer.periodic(const Duration(seconds: 1), (t) {
          if (!mounted) return;
          setState(() {
            _countdown--;
            if (_countdown <= 0) {
              _countdown = 30;
              final city = ref.read(selectedCityProvider);
              if (city != null) _handlePredict(city.name);
            }
          });
        });
      }
    } else {
      _refreshTimer?.cancel();
    }
  }

  @override
  Widget build(BuildContext context) {
    final autoRefresh = ref.watch(autoRefreshProvider);
    _manageAutoRefresh(autoRefresh);

    final health = ref.watch(healthStateProvider);
    final appError = ref.watch(appErrorProvider);
    final selectedCity = ref.watch(selectedCityProvider);
    final predictions = ref.watch(predictionsProvider);
    final isLoading = ref.watch(isLoadingProvider);
    final lastUpdated = ref.watch(lastUpdatedProvider);

    final prediction = selectedCity != null ? predictions[selectedCity.name] : null;

    return Scaffold(
      backgroundColor: kBackground,
      body: Stack(
        children: [
          SafeArea(
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      const Text('🚨 Emergency Routing', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 20, color: Colors.white)),
                      const Spacer(),
                      Row(
                        children: [
                          Container(
                            width: 8, height: 8,
                            decoration: BoxDecoration(shape: BoxShape.circle, color: health?.status == 'ok' ? kSuccess : kDanger),
                          ),
                          const SizedBox(width: 6),
                          Text(health?.status == 'ok' ? 'AI Active' : 'Offline', style: const TextStyle(fontSize: 12)),
                        ],
                      )
                    ],
                  ),
                ),
                if (appError != null)
                  Container(
                    color: kDanger,
                    padding: const EdgeInsets.all(8),
                    width: double.infinity,
                    child: Text(appError, style: const TextStyle(color: Colors.white)),
                  ),
                AlertBanner(score: prediction?.congestionT5),
                CitySelector(onCitySelect: (city) {
                  ref.read(selectedCityProvider.notifier).select(city);
                  _handlePredict(city.name);
                }),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: MapWidget(
                    cityLat: selectedCity?.lat ?? 28.6139,
                    cityLng: selectedCity?.lng ?? 77.2090,
                    congestionScore: prediction?.congestionT5 ?? 0,
                    cityName: selectedCity?.name ?? 'Delhi',
                    isPulsing: autoRefresh && isLoading,
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Row(
                    children: [
                      Switch(
                        value: autoRefresh,
                        onChanged: (_) => ref.read(autoRefreshProvider.notifier).toggle(),
                        activeColor: kAccent,
                      ),
                      const Text('Auto 30s', style: TextStyle(color: kTextSecondary, fontSize: 12)),
                      if (autoRefresh) ...[
                        const SizedBox(width: 8),
                        Text('Next: ${_countdown}s', style: const TextStyle(color: kAccent, fontSize: 12)),
                      ],
                      const Spacer(),
                      OutlinedButton.icon(
                        icon: const Icon(Icons.refresh),
                        label: const Text('Refresh Now'),
                        onPressed: isLoading ? null : () => _handlePredict(selectedCity?.name ?? 'Delhi'),
                        style: OutlinedButton.styleFrom(foregroundColor: kAccent),
                      )
                    ],
                  ),
                ),
                Expanded(
                  child: SingleChildScrollView(
                    child: prediction != null
                        ? Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              children: [
                                CongestionCard(prediction, isSelected: true),
                                const SizedBox(height: 12),
                                CongestionChart(prediction),
                              ],
                            ),
                          )
                        : Center(
                            child: Container(
                              margin: const EdgeInsets.all(32),
                              padding: const EdgeInsets.all(32),
                              decoration: BoxDecoration(
                                border: Border.all(color: kTextSecondary, style: BorderStyle.none),
                              ),
                              child: const Column(
                                children: [
                                  Icon(Icons.analytics_outlined, size: 48, color: kTextSecondary),
                                  SizedBox(height: 16),
                                  Text('Select a city to run AI prediction'),
                                  Text('LSTM+GCN Model 1', style: TextStyle(color: kTextSecondary, fontSize: 12)),
                                ],
                              ),
                            ),
                          ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(8.0),
                  child: Text('Last updated: ${lastUpdated ?? '—'}', style: const TextStyle(color: kTextSecondary, fontSize: 11), textAlign: TextAlign.center),
                )
              ],
            ),
          ),
          const LoadingOverlay(),
        ],
      ),
    );
  }
}
