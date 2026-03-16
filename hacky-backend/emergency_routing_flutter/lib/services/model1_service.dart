import 'package:dio/dio.dart';
import '../config/api_config.dart';
import '../config/cities_config.dart';
import '../models/health_response.dart';
import '../models/prediction_response.dart';
import '../models/model_info_response.dart';

class Model1Service {
  final Dio _dio = Dio(BaseOptions(
    baseUrl: kApiBaseUrl,
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 30),
  ));

  // ── Health & info ──────────────────────────────────────────────────────────

  Future<HealthResponse> checkHealth() async {
    try {
      final response = await _dio.get('/health');
      return HealthResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Health Check Failed: ${e.message}');
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

  // ── City-level prediction (trained cities only) ────────────────────────────

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
      final response =
          await _dio.post('/predict/batch', data: {'city_names': cityNames});
      final List<dynamic> data = response.data;
      return data
          .where((item) => item['congestion_t5'] != null)
          .map((item) => PredictionResponse.fromJson(item))
          .toList();
    } on DioException catch (e) {
      throw Exception('Batch Prediction Failed: ${e.message}');
    }
  }

  // ── Area prediction (pan-India, any city via bbox) ─────────────────────────

  Future<PredictionResponse> predictArea({
    required Map<String, double> bbox,
    required String areaId,
    String? referenceCity,
  }) async {
    try {
      final response = await _dio.post('/predict/area', data: {
        'bbox': bbox,
        'area_id': areaId,
        if (referenceCity != null) 'reference_city': referenceCity,
        'weather_context_city': referenceCity,
      });
      // /predict/area returns a slightly different shape — normalize it
      final Map<String, dynamic> raw = Map<String, dynamic>.from(response.data);
      return PredictionResponse.fromJson({
        'city': raw['area'] ?? areaId,
        'timestamp': raw['timestamp'],
        'congestion_t5': raw['congestion_t5'] ?? 0.0,
        'congestion_t10': raw['congestion_t10'] ?? 0.0,
        'congestion_t20': raw['congestion_t20'] ?? 0.0,
        'congestion_t30': raw['congestion_t30'] ?? 0.0,
        'uncertainty_t5': raw['uncertainty_t5'] ?? 0.1,
        'uncertainty_t10': raw['uncertainty_t10'] ?? 0.1,
        'uncertainty_t20': raw['uncertainty_t20'] ?? 0.1,
        'uncertainty_t30': raw['uncertainty_t30'] ?? 0.1,
        'latency_ms': raw['latency_ms'] ?? 0.0,
      });
    } on DioException catch (e) {
      throw Exception('Area Prediction Failed: ${e.message}');
    }
  }

  // ── Smart predict: auto-routes to city or area endpoint ───────────────────

  Future<PredictionResponse> predictForCity(CityConfig city) async {
    if (city.hasCityModel) {
      return predictCity(city.name);
    }
    // Find the nearest trained city as reference
    final reference = kTrainedCities.isNotEmpty ? kTrainedCities.first.name : null;
    return predictArea(
      bbox: city.bbox,
      areaId: city.name.toLowerCase().replaceAll(' ', '_'),
      referenceCity: reference,
    );
  }
}
