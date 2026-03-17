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
          'limit': 8,
        },
      );
      final list = (response.data as List).map((x) => Hospital.fromJson(x)).toList();

      // Defensive: ensure we never pick a hospital from a different far-away city.
      // Some backends sort by ICU beds; we always sort by true distance.
      const dist = Distance();
      final withDist = list
          .map((h) => MapEntry(h, dist.as(LengthUnit.Kilometer, currentPos, h.location)))
          .toList();
      withDist.sort((a, b) => a.value.compareTo(b.value));

      // Filter to "local" hospitals if possible (within 120km of currentPos).
      final local = withDist.where((e) => e.value <= 120).map((e) => e.key).toList();
      if (local.isNotEmpty) return local.take(5).toList();

      // Fallback: return sorted by distance even if all are far.
      return withDist.map((e) => e.key).take(5).toList();
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

  Future<List<Map<String, dynamic>>> getActiveIncidents() async {
    try {
      final supabaseUrl = 'https://uhlnwyrikuiprkuubloh.supabase.co';
      final supabaseKey = 'sb_publishable_3AB7L_OofX-B7hlO7mWUrA_vrSq5cBO';
      
      final url = '$supabaseUrl/rest/v1/posts?dispatch_status=in.(pending,assigned,in-progress)&order=created_at.desc';
      final response = await _dio.get(url, options: Options(
        headers: {
          'apikey': supabaseKey,
          'Authorization': 'Bearer $supabaseKey',
          'Content-Type': 'application/json',
        },
      ));
      
      if (response.statusCode == 200) {
        final List<dynamic> posts = response.data;
        
        return posts.map((post) {
           final location = post['location'];
           double lat = 22.7196; // Default Indore
           double lon = 75.8577;
           
           if (post['inferred_latitude'] != null && post['inferred_longitude'] != null) {
              lat = double.tryParse(post['inferred_latitude'].toString()) ?? lat;
              lon = double.tryParse(post['inferred_longitude'].toString()) ?? lon;
           } else if (location is Map && location['lat'] != null) {
              lat = double.tryParse(location['lat'].toString()) ?? lat;
              lon = double.tryParse(location['lon'].toString()) ?? lon;
           } else if (location is Map && location['latitude'] != null) {
              lat = double.tryParse(location['latitude'].toString()) ?? lat;
              lon = double.tryParse(location['longitude'].toString()) ?? lon;
           }
           
           int severity = int.tryParse(post['severity']?.toString() ?? '5') ?? 5;
           String priority = severity >= 7 ? 'High' : 'Medium';
           
           String incidentType = post['disaster_type']?.toString() ?? 'Emergency';
           if (post['ai_analysis'] is Map && post['ai_analysis']['disaster_type'] != null) {
               incidentType = post['ai_analysis']['disaster_type'];
           }
           
           String locLabel = 'Disaster Location';
           if (post['extracted_locations'] is List && (post['extracted_locations'] as List).isNotEmpty) {
               locLabel = post['extracted_locations'][0].toString();
           }
           
           return {
             "id": post['id'].toString(),
             "type": incidentType,
             "priority": priority,
             "originCoord": {"latitude": lat, "longitude": lon},
             "destCoord": {"latitude": 22.7533, "longitude": 75.8937},
             "originLabel": locLabel,
             "destLabel": "Nearest Hospital",
             "timestamp": post['created_at'] ?? DateTime.now().toIso8601String(),
             "callerInfo": "Citizen Report",
             "witnessReports": [],
             "state": post['dispatch_status'] ?? "pending",
             "videoFeedUrl": post['image_url'],
             "ambulanceEtaMin": 10,
             "patientCondition": "Unknown",
             "assignedHospital": post['assigned_team'],
           };
        }).toList();
      }
      return [];
    } catch (e) {
      print('❌ Error fetching direct supabase incidents in unified_service: $e');
      return [];
    }
  }
}
