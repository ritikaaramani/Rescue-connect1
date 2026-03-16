import 'package:dio/dio.dart';
import 'package:latlong2/latlong.dart';
import '../models/route_model.dart';
import '../config/api_config.dart';

class Hospital {
  final String id;
  final String name;
  final LatLng location;
  final int icuBeds;
  final bool traumaSpecialty;
  final double distanceKm;

  Hospital({required this.id, required this.name, required this.location, required this.icuBeds, required this.traumaSpecialty, required this.distanceKm});

  factory Hospital.fromJson(Map<String, dynamic> json) {
    return Hospital(
      id: json['id'],
      name: json['name'],
      location: LatLng(json['location'][0], json['location'][1]),
      icuBeds: json['icu_beds_available'],
      traumaSpecialty: json['trauma_specialty'],
      distanceKm: json['distance_km'].toDouble(),
    );
  }
}

class UnifiedRoutingResponse {
  final String status;
  final String city;
  final double standardEtaMin;
  final double aiEtaMin;
  final double reliabilityScore;
  final List<double> confidenceInterval;
  final String recommendedRouteId;
  final List<IndiaFactor> activeFactors;
  final String recommendedLane;
  final String reasoning;

  UnifiedRoutingResponse({
    required this.status,
    required this.city,
    required this.standardEtaMin,
    required this.aiEtaMin,
    required this.reliabilityScore,
    required this.confidenceInterval,
    required this.recommendedRouteId,
    required this.activeFactors,
    required this.recommendedLane,
    required this.reasoning,
  });

  factory UnifiedRoutingResponse.fromJson(Map<String, dynamic> json) {
    return UnifiedRoutingResponse(
      status: json['status'],
      city: json['city'],
      standardEtaMin: json['standard_eta_min'].toDouble(),
      aiEtaMin: json['ai_eta_min'].toDouble(),
      reliabilityScore: json['reliability_score'].toDouble(),
      confidenceInterval: List<double>.from(json['confidence_interval'].map((x) => x.toDouble())),
      recommendedRouteId: json['recommended_route_id'],
      activeFactors: List<IndiaFactor>.from(json['active_factors'].map((x) => IndiaFactor.fromJson(x))),
      recommendedLane: json['recommended_lane'] ?? "Default",
      reasoning: json['reasoning'] ?? "AI optimized route calculated.",
    );
  }
}

class UnifiedService {
  final Dio _dio = Dio();

  Future<UnifiedRoutingResponse> getRoute(LatLng origin, LatLng destination, String city, {String criticality = "High"}) async {
    try {
      final response = await _dio.post(
        '$kApiBaseUrl/route/comprehensive',
        data: {
          'origin': [origin.latitude, origin.longitude],
          'destination': [destination.latitude, destination.longitude],
          'city_name': city,
          'criticality': criticality,
          'weather': 'Clear',
        },
      );
      return UnifiedRoutingResponse.fromJson(response.data);
    } catch (e) {
      throw Exception('Failed to load comprehensive route: $e');
    }
  }

  Future<List<Hospital>> getNearestHospitals(LatLng currentPos) async {
    try {
      final response = await _dio.get(
        '$kApiBaseUrl/hospitals/nearest',
        queryParameters: {
          'lat': currentPos.latitude,
          'lon': currentPos.longitude,
        },
      );
      return (response.data as List).map((x) => Hospital.fromJson(x)).toList();
    } catch (e) {
      throw Exception('Failed to load hospitals: $e');
    }
  }

  Future<bool> reportIncident(LatLng location, String type, int severity) async {
    try {
      await _dio.post(
        '$kApiBaseUrl/incident/report',
        data: {
          'reporter_id': 'Driver_001',
          'location': [location.latitude, location.longitude],
          'type': type,
          'severity': severity,
          'timestamp': DateTime.now().toIso8601String(),
        },
      );
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<List<Map<String, dynamic>>> getMessages() async {
    try {
      final response = await _dio.get('$kApiBaseUrl/dispatch/messages');
      return List<Map<String, dynamic>>.from(response.data);
    } catch (e) {
      return [];
    }
  }
}
