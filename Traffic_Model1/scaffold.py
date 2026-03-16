import os

BASE_DIR = r"C:\Users\VAIBHAVI\Traffic_Model1\emergency_routing_flutter"

FILES = {
    "android/app/src/main/AndroidManifest.xml": """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
    <application
        android:label="emergency_routing_flutter"
        android:name="${applicationName}"
        android:usesCleartextTraffic="true"
        android:icon="@mipmap/ic_launcher">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:theme="@style/LaunchTheme"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize">
            <meta-data
              android:name="io.flutter.embedding.android.NormalTheme"
              android:resource="@style/NormalTheme"
              />
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
        <meta-data
            android:name="flutterEmbedding"
            android:value="2" />
    </application>
    <queries>
        <intent>
            <action android:name="android.intent.action.PROCESS_TEXT"/>
            <data android:mimeType="text/plain"/>
        </intent>
    </queries>
</manifest>""",

    "lib/config/api_config.dart": """const String kApiBaseUrl = 'http://192.168.29.74:8001';
""",

    "lib/config/cities_config.dart": """class CityConfig {
  final String name;
  final double lat;
  final double lng;

  const CityConfig({required this.name, required this.lat, required this.lng});
}

const List<CityConfig> kCities = [
  CityConfig(name: 'Delhi', lat: 28.6139, lng: 77.2090),
  CityConfig(name: 'Mumbai', lat: 19.0760, lng: 72.8777),
  CityConfig(name: 'Bengaluru', lat: 12.9716, lng: 77.5946),
  CityConfig(name: 'Chennai', lat: 13.0827, lng: 80.2707),
  CityConfig(name: 'Patna', lat: 25.5941, lng: 85.1376),
];
""",

    "lib/config/theme.dart": """import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

const Color kBackground = Color(0xFF0A0A0F);
const Color kCardBg = Color(0xFF0F0F1A);
const Color kCardBorder = Color(0xFF1A1A2E);
const Color kTextPrimary = Color(0xFFFFFFFF);
const Color kTextSecondary = Color(0xFF8888AA);
const Color kAccent = Color(0xFF4A9EFF);
const Color kAccentDim = Color(0xFF1A3A5C);
const Color kSuccess = Color(0xFF00C851);
const Color kWarning = Color(0xFFFF8800);
const Color kDanger = Color(0xFFFF4444);

Color getCongestionColor(double score) {
  if (score < 0.3) return kSuccess;
  if (score < 0.6) return kWarning;
  return kDanger;
}

String getCongestionLabel(double score) {
  if (score < 0.3) return 'Clear';
  if (score < 0.6) return 'Moderate Traffic';
  return 'Heavy Congestion';
}

String getCongestionMessage(double score) {
  if (score < 0.3) return 'Route is clear. Safe to proceed.';
  if (score < 0.6) return 'Moderate traffic ahead. Caution advised.';
  return 'Heavy congestion detected. Consider alternate route.';
}

String formatLatency(double ms) {
  if (ms < 1000) return '${ms.toStringAsFixed(0)}ms';
  return '${(ms / 1000).toStringAsFixed(1)}s';
}

String formatUptime(double seconds) {
  final h = (seconds / 3600).floor();
  final m = ((seconds % 3600) / 60).floor();
  final s = (seconds % 60).floor();
  return '${h}h ${m}m ${s}s';
}

ThemeData buildAppTheme() {
  return ThemeData(
    scaffoldBackgroundColor: kBackground,
    colorScheme: const ColorScheme.dark(
      primary: kAccent,
      surface: kCardBg,
    ),
    fontFamily: GoogleFonts.rajdhani().fontFamily,
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.transparent,
      elevation: 0,
      foregroundColor: kTextPrimary,
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: kCardBg,
      indicatorColor: kAccentDim,
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) return const TextStyle(color: kAccent, fontSize: 12, fontWeight: FontWeight.bold);
        return const TextStyle(color: kTextSecondary, fontSize: 12);
      }),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) return const IconThemeData(color: kAccent);
        return const IconThemeData(color: kTextSecondary);
      }),
    ),
    cardTheme: const CardTheme(
      color: kCardBg,
      elevation: 0,
      shape: RoundedRectangleBorder(
        side: BorderSide(color: kCardBorder),
        borderRadius: BorderRadius.all(Radius.circular(16)),
      ),
    ),
    textTheme: const TextTheme(
      bodyLarge: TextStyle(color: kTextPrimary),
      bodyMedium: TextStyle(color: kTextPrimary),
    ),
  );
}
""",

    "lib/models/prediction_response.dart": """import 'package:freezed_annotation/freezed_annotation.dart';

part 'prediction_response.freezed.dart';
part 'prediction_response.g.dart';

@freezed
class PredictionResponse with _$PredictionResponse {
  factory PredictionResponse({
    required String city,
    required String timestamp,
    @JsonKey(name: 'congestion_t5') required double congestionT5,
    @JsonKey(name: 'congestion_t10') required double congestionT10,
    @JsonKey(name: 'congestion_t20') required double congestionT20,
    @JsonKey(name: 'congestion_t30') required double congestionT30,
    @JsonKey(name: 'uncertainty_t5') required double uncertaintyT5,
    @JsonKey(name: 'uncertainty_t10') required double uncertaintyT10,
    @JsonKey(name: 'uncertainty_t20') required double uncertaintyT20,
    @JsonKey(name: 'uncertainty_t30') required double uncertaintyT30,
    @JsonKey(name: 'latency_ms') required double latencyMs,
  }) = _PredictionResponse;

  factory PredictionResponse.fromJson(Map<String, dynamic> json) =>
      _$PredictionResponseFromJson(json);
}
""",

    "lib/models/health_response.dart": """import 'package:freezed_annotation/freezed_annotation.dart';

part 'health_response.freezed.dart';
part 'health_response.g.dart';

@freezed
class HealthResponse with _$HealthResponse {
  factory HealthResponse({
    required String status,
    @JsonKey(name: 'model_loaded') required bool modelLoaded,
    @JsonKey(name: 'cities_available') required List<String> citiesAvailable,
    @JsonKey(name: 'uptime_seconds') required double uptimeSeconds,
  }) = _HealthResponse;

  factory HealthResponse.fromJson(Map<String, dynamic> json) =>
      _$HealthResponseFromJson(json);
}
""",

    "lib/models/model_info_response.dart": """import 'package:freezed_annotation/freezed_annotation.dart';

part 'model_info_response.freezed.dart';
part 'model_info_response.g.dart';

@freezed
class ModelInfoResponse with _$ModelInfoResponse {
  factory ModelInfoResponse({
    @JsonKey(name: 'model_name') required String modelName,
    @JsonKey(name: 'lstm_hidden_size') required int lstmHiddenSize,
    @JsonKey(name: 'gcn_hidden_dim') required int gcnHiddenDim,
    @JsonKey(name: 'num_prediction_horizons') required int numPredictionHorizons,
    @JsonKey(name: 'checkpoint_path') required String checkpointPath,
    @JsonKey(name: 'parameter_count') required int parameterCount,
  }) = _ModelInfoResponse;

  factory ModelInfoResponse.fromJson(Map<String, dynamic> json) =>
      _$ModelInfoResponseFromJson(json);
}
""",

    "lib/models/dispatch_log_entry.dart": """import 'package:freezed_annotation/freezed_annotation.dart';

part 'dispatch_log_entry.freezed.dart';

@freezed
class DispatchLogEntry with _$DispatchLogEntry {
  factory DispatchLogEntry({
    required String id,
    required String timestamp,
    required String city,
    required double score,
    required String message,
    required String level,
  }) = _DispatchLogEntry;
}
""",

    "lib/services/model1_service.dart": """import 'package:dio/dio.dart';
import '../config/api_config.dart';
import '../models/health_response.dart';
import '../models/prediction_response.dart';
import '../models/model_info_response.dart';

class Model1Service {
  final Dio _dio = Dio(BaseOptions(
    baseUrl: kApiBaseUrl,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
  ));

  Future<HealthResponse> checkHealth() async {
    try {
      final response = await _dio.get('/health');
      return HealthResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Health Check Failed: ${e.message}');
    }
  }

  Future<PredictionResponse> predictCity(String cityName) async {
    try {
      final response = await _dio.post('/predict', data: {'city_name': cityName});
      return PredictionResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Prediction Failed: ${e.message}');
    }
  }

  Future<List<PredictionResponse>> predictBatch(List<String> cityNames) async {
    try {
      final response = await _dio.post('/predict/batch', data: {'city_names': cityNames});
      final List<dynamic> data = response.data;
      return data
          .where((item) => item['congestion_t5'] != null)
          .map((item) => PredictionResponse.fromJson(item))
          .toList();
    } on DioException catch (e) {
      throw Exception('Batch Prediction Failed: ${e.message}');
    }
  }

  Future<ModelInfoResponse> getModelInfo() async {
    try {
      final response = await _dio.get('/model/info');
      return ModelInfoResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Model Info Failed: ${e.message}');
    }
  }
}
""",

    "lib/services/model2_service.dart": """class Model2Service {
  Future<Never> scoreRoute() async {
    throw UnimplementedError('Model 2 not yet integrated');
  }
}
""",

    "lib/services/model3_service.dart": """class Model3Service {
  Future<Never> rerouteAgent() async {
    throw UnimplementedError('Model 3 not yet integrated');
  }
}
""",
    
    "lib/providers/prediction_provider.dart": """import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:intl/intl.dart';
import '../config/cities_config.dart';
import '../models/prediction_response.dart';
import 'dispatch_provider.dart';

part 'prediction_provider.g.dart';

@riverpod
class SelectedCity extends _$SelectedCity {
  @override
  CityConfig? build() => null;

  void select(CityConfig city) {
    state = city;
  }
}

@riverpod
class Predictions extends _$Predictions {
  @override
  Map<String, PredictionResponse> build() => {};

  void setPrediction(String city, PredictionResponse p) {
    state = {...state, city: p};
    ref.read(dispatchLogProvider.notifier).addEntry(p);
  }

  void setBatch(List<PredictionResponse> list) {
    for (var p in list) {
      setPrediction(p.city, p);
    }
  }

  void clear() {
    state = {};
  }
}

@riverpod
class IsLoading extends _$IsLoading {
  @override
  bool build() => false;

  void setLoading(bool val) {
    state = val;
  }
}

@riverpod
class AppError extends _$AppError {
  @override
  String? build() => null;

  void setError(String? msg) {
    state = msg;
  }
}

@riverpod
class AutoRefresh extends _$AutoRefresh {
  @override
  bool build() => false;

  void toggle() {
    state = !state;
  }
}

@riverpod
class LastUpdated extends _$LastUpdated {
  @override
  String? build() => null;

  void update() {
    state = DateFormat('HH:mm:ss').format(DateTime.now());
  }
}
""",

    "lib/providers/dispatch_provider.dart": """import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../models/dispatch_log_entry.dart';
import '../models/prediction_response.dart';
import '../config/theme.dart';

part 'dispatch_provider.g.dart';

@riverpod
class DispatchLog extends _$DispatchLog {
  @override
  List<DispatchLogEntry> build() => [];

  void addEntry(PredictionResponse prediction) {
    final score = prediction.congestionT5;
    final String level = score < 0.3 ? 'low' : score < 0.6 ? 'moderate' : 'high';
    
    final entry = DispatchLogEntry(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      timestamp: DateTime.now().toIso8601String(),
      city: prediction.city,
      score: score,
      message: getCongestionMessage(score),
      level: level,
    );
    
    final newList = [entry, ...state];
    if (newList.length > 100) {
      state = newList.sublist(0, 100);
    } else {
      state = newList;
    }
  }

  void clear() {
    state = [];
  }
}
""",

    "lib/providers/health_provider.dart": """import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../models/health_response.dart';
import '../models/model_info_response.dart';
import '../services/model1_service.dart';

part 'health_provider.g.dart';

@riverpod
Model1Service model1Service(Model1ServiceRef ref) {
  return Model1Service();
}

@riverpod
class HealthState extends _$HealthState {
  @override
  HealthResponse? build() => null;

  Future<void> fetch() async {
    try {
      state = await ref.read(model1ServiceProvider).checkHealth();
    } catch (e) {
      state = null;
    }
  }
}

@riverpod
class ModelInfoState extends _$ModelInfoState {
  @override
  ModelInfoResponse? build() => null;

  Future<void> fetch() async {
    try {
      state = await ref.read(model1ServiceProvider).getModelInfo();
    } catch (e) {
      state = null;
    }
  }
}
""",

    "lib/widgets/status_badge.dart": """import 'package:flutter/material.dart';
import '../config/theme.dart';

class StatusBadge extends StatelessWidget {
  final double score;
  const StatusBadge({super.key, required this.score});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 3, horizontal: 10),
      decoration: BoxDecoration(
        color: getCongestionColor(score),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        getCongestionLabel(score).toUpperCase(),
        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11),
      ),
    );
  }
}
""",

    "lib/widgets/alert_banner.dart": """import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../config/theme.dart';

class AlertBanner extends StatelessWidget {
  final double? score;
  const AlertBanner({super.key, this.score});

  @override
  Widget build(BuildContext context) {
    if (score == null) return const SizedBox.shrink();

    final color = getCongestionColor(score!);
    final msg = getCongestionMessage(score!);
    
    IconData iconData = Icons.check_circle_outline;
    if (score! >= 0.3) iconData = Icons.warning_amber_rounded;
    if (score! >= 0.6) iconData = Icons.error_outline;

    Widget banner = Container(
      color: color.withOpacity(0.15),
      padding: const EdgeInsets.all(12),
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        border: Border(left: BorderSide(color: color, width: 3)),
      ),
      child: Row(
        children: [
          Icon(iconData, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Text(msg, style: const TextStyle(color: kTextSecondary, fontSize: 13)),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(20)),
            child: Text(
              '${(score! * 100).toStringAsFixed(0)}%',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
            ),
          )
        ],
      ),
    ).animate().slideY(begin: -1, end: 0, duration: 300.ms, curve: Curves.easeOut);

    if (score! >= 0.6) {
      banner = banner.animate(onPlay: (c) => c.repeat()).shimmer(duration: 2000.ms, color: kDanger.withOpacity(0.3));
    }

    return banner;
  }
}
""",

    "lib/widgets/dispatch_log_entry_tile.dart": """import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/dispatch_log_entry.dart';
import '../config/theme.dart';

class DispatchLogEntryTile extends StatelessWidget {
  final DispatchLogEntry entry;
  const DispatchLogEntryTile({super.key, required this.entry});

  @override
  Widget build(BuildContext context) {
    final timeStr = DateFormat('HH:mm:ss').format(DateTime.parse(entry.timestamp));
    final color = getCongestionColor(entry.score);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border(left: BorderSide(color: color, width: 3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(entry.city, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
              const Spacer(),
              Text(timeStr, style: const TextStyle(color: kTextSecondary, fontSize: 11)),
            ],
          ),
          const SizedBox(height: 4),
          Text(entry.message, style: const TextStyle(color: kTextSecondary, fontSize: 13)),
          const SizedBox(height: 8),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(4)),
                child: Text('${(entry.score * 100).toStringAsFixed(1)}%', 
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11)),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: kCardBorder, borderRadius: BorderRadius.circular(4)),
                child: Text(entry.level.toUpperCase(), 
                  style: const TextStyle(color: kTextSecondary, fontSize: 11)),
              )
            ],
          )
        ],
      ),
    );
  }
}
""",

    "lib/widgets/loading_overlay.dart": """import 'package:flutter/material.dart';
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
""",
    
    "lib/widgets/city_selector.dart": """import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../config/cities_config.dart';
import '../config/theme.dart';
import '../providers/prediction_provider.dart';

class CitySelector extends ConsumerWidget {
  final void Function(CityConfig) onCitySelect;

  const CitySelector({super.key, required this.onCitySelect});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedCity = ref.watch(selectedCityProvider);
    final predictions = ref.watch(predictionsProvider);

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: Row(
        children: kCities.map((city) {
          final isSelected = selectedCity?.name == city.name;
          final hasPrediction = predictions.containsKey(city.name);
          final predScore = predictions[city.name]?.congestionT5;

          Color bgColor = Colors.transparent;
          if (isSelected) bgColor = hasPrediction ? getCongestionColor(predScore!) : kAccent;

          return GestureDetector(
            onTap: () => onCitySelect(city),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              height: 40,
              margin: const EdgeInsets.only(right: 8),
              padding: const EdgeInsets.symmetric(horizontal: 16),
              decoration: BoxDecoration(
                color: bgColor,
                borderRadius: BorderRadius.circular(999),
                border: !isSelected ? Border.all(color: const Color(0xFF333333)) : null,
              ),
              child: Row(
                children: [
                  if (hasPrediction && !isSelected) ...[
                    Container(width: 6, height: 6, decoration: BoxDecoration(shape: BoxShape.circle, color: getCongestionColor(predScore!))),
                    const SizedBox(width: 6),
                  ],
                  Text(
                    city.name,
                    style: TextStyle(
                      color: isSelected ? Colors.white : kTextSecondary,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
""",

    "lib/widgets/map_widget.dart": """import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../config/theme.dart';

class MapWidget extends StatelessWidget {
  final double cityLat;
  final double cityLng;
  final double congestionScore;
  final String cityName;
  final bool isPulsing;

  const MapWidget({
    super.key,
    required this.cityLat,
    required this.cityLng,
    required this.congestionScore,
    required this.cityName,
    required this.isPulsing,
  });

  @override
  Widget build(BuildContext context) {
    final color = getCongestionColor(congestionScore);
    
    // Matrix to invert OpenStreetMap layers for dark mode
    final List<double> darkModeMatrix = [
      -1,  0,  0, 0, 255,
       0, -1,  0, 0, 255,
       0,  0, -1, 0, 255,
       0,  0,  0, 1,   0,
    ];

    Widget markerChild = Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.emergency, color: color, size: 32),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(4)),
          child: Text(cityName, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 10)),
        )
      ],
    );

    if (isPulsing) {
      markerChild = markerChild.animate(onPlay: (c) => c.repeat())
        .scale(begin: const Offset(1, 1), end: const Offset(1.3, 1.3), duration: 1000.ms)
        .then()
        .scale(begin: const Offset(1.3, 1.3), end: const Offset(1, 1), duration: 1000.ms);
    }

    return Container(
      height: 280,
      clipBehavior: Clip.hardEdge,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kCardBorder),
      ),
      child: FlutterMap(
        options: MapOptions(
          initialCenter: LatLng(cityLat, cityLng),
          initialZoom: 12,
          interactionOptions: const InteractionOptions(flags: InteractiveFlag.all),
        ),
        children: [
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'com.emergencyrouting.app',
            tileBuilder: (BuildContext context, Widget tileWidget, TileImage tile) {
              return ColorFiltered(
                colorFilter: ColorFilter.matrix(darkModeMatrix),
                child: tileWidget,
              );
            },
          ),
          CircleLayer(
            circles: [
              CircleMarker(
                point: LatLng(cityLat, cityLng),
                radius: 3000,
                useRadiusInMeter: true,
                color: color.withOpacity(0.35),
                borderColor: color.withOpacity(0.8),
                borderStrokeWidth: 2,
              )
            ],
          ),
          MarkerLayer(
            markers: [
              Marker(
                point: LatLng(cityLat, cityLng),
                width: 80,
                height: 80,
                child: markerChild,
              )
            ],
          )
        ],
      ),
    );
  }
}
""",

    "lib/widgets/congestion_card.dart": """import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/prediction_response.dart';
import '../config/theme.dart';
import 'status_badge.dart';

class CongestionCard extends StatelessWidget {
  final PredictionResponse prediction;
  final bool isSelected;

  const CongestionCard(this.prediction, {super.key, this.isSelected = false});

  @override
  Widget build(BuildContext context) {
    final t5 = prediction.congestionT5;
    
    List<Color> gradientColors;
    if (t5 < 0.3) {
      gradientColors = [const Color(0xFF0A2E1A), const Color(0xFF0D3D22)];
    } else if (t5 < 0.6) {
      gradientColors = [const Color(0xFF2E1A00), const Color(0xFF3D2A00)];
    } else {
      gradientColors = [const Color(0xFF2E0A0A), const Color(0xFF3D1010)];
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: gradientColors),
        border: Border.all(color: getCongestionColor(t5).withOpacity(0.5), width: 1.5),
        borderRadius: BorderRadius.circular(16),
        boxShadow: isSelected 
          ? [BoxShadow(color: kAccent.withOpacity(0.3), blurRadius: 8)] 
          : null,
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(prediction.city, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
              StatusBadge(score: t5),
            ],
          ),
          const SizedBox(height: 16),
          Text('${(t5 * 100).toStringAsFixed(1)}%', style: TextStyle(fontSize: 44, fontWeight: FontWeight.bold, color: getCongestionColor(t5))),
          const Text('T+5 Congestion', style: TextStyle(color: kTextSecondary, fontSize: 12)),
          const SizedBox(height: 16),
          const Divider(color: kCardBorder),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildHorizonCol('T+10', prediction.congestionT10),
              _buildHorizonCol('T+20', prediction.congestionT20),
              _buildHorizonCol('T+30', prediction.congestionT30),
            ],
          ),
          const Divider(color: kCardBorder),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              Chip(
                label: Text('⚡ ${formatLatency(prediction.latencyMs)}'),
                backgroundColor: kAccentDim,
                side: BorderSide.none,
              ),
              Chip(
                label: Text('± ${prediction.uncertaintyT5.toStringAsFixed(2)}'),
                backgroundColor: kCardBorder,
                side: BorderSide.none,
              ),
            ],
          )
        ],
      ),
    ).animate().fadeIn().slideY(begin: 0.2, end: 0);
  }

  Widget _buildHorizonCol(String label, double val) {
    return Column(
      children: [
        Text(label, style: const TextStyle(color: Colors.grey, fontSize: 11)),
        Text('${(val * 100).toStringAsFixed(1)}%', style: TextStyle(color: getCongestionColor(val), fontSize: 16, fontWeight: FontWeight.bold)),
      ],
    );
  }
}
""",

    "lib/widgets/congestion_chart.dart": """import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../models/prediction_response.dart';
import '../config/theme.dart';

class CongestionChart extends StatelessWidget {
  final PredictionResponse prediction;
  const CongestionChart(this.prediction, {super.key});

  @override
  Widget build(BuildContext context) {
    final color = getCongestionColor(prediction.congestionT5);
    
    return Container(
      height: 180,
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          const Text('Congestion Forecast', style: TextStyle(color: kTextSecondary, fontSize: 12)),
          const SizedBox(height: 16),
          Expanded(
            child: LineChart(
              LineChartData(
                minY: 0,
                maxY: 1.0,
                gridData: const FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: 0.25,
                ),
                borderData: FlBorderData(show: false),
                titlesData: FlTitlesData(
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 22,
                      getTitlesWidget: (val, meta) {
                        const labels = ['T+5', 'T+10', 'T+20', 'T+30'];
                        if (val.toInt() >= 0 && val.toInt() < labels.length) {
                          return Text(labels[val.toInt()], style: const TextStyle(color: kTextSecondary, fontSize: 10));
                        }
                        return const SizedBox.shrink();
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 30,
                      interval: 0.25,
                      getTitlesWidget: (val, meta) => Text(val.toStringAsFixed(2), style: const TextStyle(color: kTextSecondary, fontSize: 10)),
                    )
                  )
                ),
                lineBarsData: [
                  LineChartBarData(
                    spots: [
                      FlSpot(0, prediction.congestionT5),
                      FlSpot(1, prediction.congestionT10),
                      FlSpot(2, prediction.congestionT20),
                      FlSpot(3, prediction.congestionT30),
                    ],
                    color: color,
                    barWidth: 2.5,
                    isCurved: true,
                    dotData: const FlDotData(show: true),
                    belowBarData: BarAreaData(
                      show: true,
                      color: color.withOpacity(0.15),
                    ),
                  ),
                  LineChartBarData(
                    spots: [
                      FlSpot(0, (prediction.congestionT5 + prediction.uncertaintyT5).clamp(0.0, 1.0)),
                      FlSpot(1, (prediction.congestionT10 + prediction.uncertaintyT10).clamp(0.0, 1.0)),
                      FlSpot(2, (prediction.congestionT20 + prediction.uncertaintyT20).clamp(0.0, 1.0)),
                      FlSpot(3, (prediction.congestionT30 + prediction.uncertaintyT30).clamp(0.0, 1.0)),
                    ],
                    color: color.withOpacity(0.4),
                    barWidth: 1,
                    isCurved: true,
                    dashArray: [4, 4],
                    dotData: const FlDotData(show: false),
                  )
                ]
              )
            ),
          ),
        ],
      ),
    );
  }
}
""",

    "lib/screens/main_shell.dart": """import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'map_screen.dart';
import 'dashboard_screen.dart';
import 'dispatch_screen.dart';
import 'settings_screen.dart';
import '../providers/dispatch_provider.dart';
import '../config/theme.dart';

class MainShell extends ConsumerStatefulWidget {
  const MainShell({super.key});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    MapScreen(),
    DashboardScreen(),
    DispatchScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final dispatchLog = ref.watch(dispatchLogProvider);

    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: NavigationBar(
        backgroundColor: kCardBg,
        indicatorColor: kAccentDim,
        selectedIndex: _currentIndex,
        onDestinationSelected: (idx) => setState(() => _currentIndex = idx),
        destinations: [
          const NavigationDestination(icon: Icon(Icons.map_outlined), selectedIcon: Icon(Icons.map), label: 'Map'),
          const NavigationDestination(icon: Icon(Icons.bar_chart_outlined), selectedIcon: Icon(Icons.bar_chart), label: 'Dashboard'),
          NavigationDestination(
            icon: Badge(
              isLabelVisible: dispatchLog.isNotEmpty,
              label: Text(dispatchLog.length.toString()),
              child: const Icon(Icons.cell_tower_outlined),
            ),
            selectedIcon: Badge(
              isLabelVisible: dispatchLog.isNotEmpty,
              label: Text(dispatchLog.length.toString()),
              child: const Icon(Icons.cell_tower),
            ),
            label: 'Dispatch',
          ),
          const NavigationDestination(icon: Icon(Icons.settings_outlined), selectedIcon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
    );
  }
}
""",

    "lib/screens/map_screen.dart": """import 'dart:async';
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
""",

    "lib/screens/dashboard_screen.dart": """import 'package:flutter/material.dart';
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
                      gradient: const LinearGradient(colors: [Color(0xFF1A3AFF), Color(0xFF0000CC)]),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.transparent,
                        shadowColor: Colors.transparent,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      onPressed: () => _handleBatchPredict(ref),
                      child: isLoading
                          ? const Row(mainAxisAlignment: MainAxisAlignment.center, children: [SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)), SizedBox(width: 8), Text('Predicting...', style: TextStyle(color: Colors.white))])
                          : const Text('⚡ Predict All Cities', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
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
""",

    "lib/screens/dispatch_screen.dart": """import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/dispatch_provider.dart';
import '../config/theme.dart';
import '../widgets/dispatch_log_entry_tile.dart';

class DispatchScreen extends ConsumerWidget {
  const DispatchScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dispatchLog = ref.watch(dispatchLogProvider);

    return Scaffold(
      backgroundColor: kBackground,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  const Text('📡 Dispatch Log', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 20, color: Colors.white)),
                  const Spacer(),
                  if (dispatchLog.isNotEmpty)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      decoration: BoxDecoration(
                        color: dispatchLog.any((e) => e.level == 'high') ? kDanger : kAccent,
                        borderRadius: BorderRadius.circular(28),
                      ),
                      child: Text(dispatchLog.length.toString(), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
                    )
                ],
              ),
            ),
            if (dispatchLog.isEmpty)
              const Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.cell_tower, color: kTextSecondary, size: 64),
                      SizedBox(height: 16),
                      Text('No dispatch events yet', style: TextStyle(color: Colors.white, fontSize: 16)),
                      Text('Predictions appear here automatically', style: TextStyle(color: kTextSecondary, fontSize: 13)),
                    ],
                  ),
                ),
              )
            else ...[
              Expanded(
                child: ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: dispatchLog.length,
                  itemBuilder: (ctx, idx) => DispatchLogEntryTile(entry: dispatchLog[idx]),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Text('${dispatchLog.length} total events', style: const TextStyle(color: kTextSecondary, fontSize: 11), textAlign: TextAlign.center),
              ),
            ],
            Padding(
              padding: const EdgeInsets.all(16),
              child: OutlinedButton(
                style: OutlinedButton.styleFrom(
                  foregroundColor: kDanger,
                  side: const BorderSide(color: kDanger),
                  minimumSize: const Size.fromHeight(50),
                ),
                onPressed: () {
                  showDialog(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: const Text('Clear Log?'),
                      content: const Text('This will delete all dispatch alerts.'),
                      actions: [
                        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
                        TextButton(onPressed: () {
                          ref.read(dispatchLogProvider.notifier).clear();
                          Navigator.pop(ctx);
                        }, child: const Text('Clear', style: TextStyle(color: kDanger))),
                      ],
                    ),
                  );
                },
                child: const Text('Clear Log'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
""",

    "lib/screens/settings_screen.dart": """import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../config/api_config.dart';
import '../config/theme.dart';
import '../providers/health_provider.dart';
import '../providers/prediction_provider.dart';
import '../providers/dispatch_provider.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final health = ref.watch(healthStateProvider);
    final modelInfo = ref.watch(modelInfoStateProvider);

    return Scaffold(
      backgroundColor: kBackground,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text('Settings', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 20, color: Colors.white)),
              const SizedBox(height: 16),
              
              _header('🔌 API Configuration'),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: kCardBg, border: Border.all(color: kCardBorder), borderRadius: BorderRadius.circular(12)),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Backend URL', style: TextStyle(color: kTextSecondary, fontSize: 12)),
                    SizedBox(height: 4),
                    SelectableText(kApiBaseUrl, style: TextStyle(color: kAccent, fontFamily: 'monospace', fontSize: 13)),
                    SizedBox(height: 8),
                    Text('Edit lib/config/api_config.dart to change', style: TextStyle(color: kTextSecondary, fontSize: 11)),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              
              _header('🟢 Model Status'),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: kCardBg, border: Border.all(color: kCardBorder), borderRadius: BorderRadius.circular(12)),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _statusRow('Status', health?.status ?? '—', health?.status == 'ok' ? kSuccess : kDanger),
                    _statusRow('Model Loaded', health?.modelLoaded == true ? '✓ Loaded' : '✗ Not loaded', health?.modelLoaded == true ? kSuccess : kDanger),
                    _statusRow('Cities', health?.citiesAvailable.join(', ') ?? '—', Colors.white),
                    _statusRow('Uptime', formatUptime(health?.uptimeSeconds ?? 0), Colors.white),
                    const SizedBox(height: 8),
                    OutlinedButton(
                      style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(40)),
                      onPressed: () => ref.read(healthStateProvider.notifier).fetch(),
                      child: const Text('Refresh Status'),
                    )
                  ],
                ),
              ),
              const SizedBox(height: 16),
              
              _header('🧠 Model Architecture'),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: kCardBg, border: Border.all(color: kCardBorder), borderRadius: BorderRadius.circular(12)),
                child: Column(
                  children: [
                    _infoRow('Model', modelInfo?.modelName ?? '—'),
                    _infoRow('Parameters', modelInfo?.parameterCount.toString() ?? '—'),
                    _infoRow('LSTM Hidden', modelInfo?.lstmHiddenSize.toString() ?? '—'),
                    _infoRow('GCN Hidden', modelInfo?.gcnHiddenDim.toString() ?? '—'),
                    _infoRow('Horizons', modelInfo?.numPredictionHorizons.toString() ?? '—'),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              _header('🔒 Coming Soon'),
              Opacity(
                opacity: 0.4,
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: kCardBg, border: Border.all(color: kCardBorder), borderRadius: BorderRadius.circular(12)),
                  child: const Column(
                    children: [
                      Row(children: [Icon(Icons.lock, size: 16), SizedBox(width: 8), Text('Model 2 — Route Reliability Scorer')]),
                      Divider(color: kCardBorder, height: 24),
                      Row(children: [Icon(Icons.lock, size: 16), SizedBox(width: 8), Text('Model 3 — RL Rerouting Agent (DQN)')]),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              _header('⚠️ Actions'),
              OutlinedButton(
                style: OutlinedButton.styleFrom(foregroundColor: kDanger, side: const BorderSide(color: kDanger), minimumSize: const Size.fromHeight(48)),
                onPressed: () => ref.read(predictionsProvider.notifier).clear(),
                child: const Text('Clear All Predictions'),
              ),
              const SizedBox(height: 8),
              OutlinedButton(
                style: OutlinedButton.styleFrom(foregroundColor: kDanger, side: const BorderSide(color: kDanger), minimumSize: const Size.fromHeight(48)),
                onPressed: () => ref.read(dispatchLogProvider.notifier).clear(),
                child: const Text('Clear Dispatch Log'),
              ),
              const SizedBox(height: 24),
              const Text('v1.0.0-demo  |  Model 1 Active', style: TextStyle(color: kTextSecondary, fontSize: 12), textAlign: TextAlign.center),
            ],
          ),
        ),
      ),
    );
  }

  Widget _header(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(text, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
    );
  }

  Widget _statusRow(String label, String value, Color valueColor) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: kTextSecondary)),
          Text(value, style: TextStyle(color: valueColor, fontWeight: FontWeight.bold)),
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
""",

    "lib/main.dart": """import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'config/theme.dart';
import 'screens/main_shell.dart';

void main() {
  runApp(const ProviderScope(child: EmergencyRoutingApp()));
}

class EmergencyRoutingApp extends ConsumerWidget {
  const EmergencyRoutingApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'Emergency Routing',
      theme: buildAppTheme(),
      home: const MainShell(),
      debugShowCheckedModeBanner: false,
    );
  }
}
"""
}

for path, content in FILES.items():
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Created {len(FILES)} files successfully!")
