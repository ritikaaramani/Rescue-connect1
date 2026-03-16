import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Unified Backend Service - HTTP Polling Based (No WebSocket)
class BackendService {
  // Try multiple URLs to find working backend
  static const List<String> possibleUrls = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://192.168.1.1:8000',  // Common router IP
  ];
  
  late String baseUrl;
  
  // Polling timers
  Timer? _vehiclePoller;
  Timer? _blockagePoller;
  
  // Stream controllers for events
  final _incidentUpdates = StreamController<Map<String, dynamic>>.broadcast();
  final _vehicleUpdates = StreamController<Map<String, dynamic>>.broadcast();
  final _blockageAlerts = StreamController<Map<String, dynamic>>.broadcast();
  final _rerouteAlerts = StreamController<Map<String, dynamic>>.broadcast();
  final _dispatchMessages = StreamController<Map<String, dynamic>>.broadcast();
  
  // Track last blockages for diff detection
  Set<String> _lastBlockageIds = {};
  
  /// Find working backend URL
  Future<bool> findWorkingBackend() async {
    print('🔍 Searching for backend...');
    for (final url in possibleUrls) {
      try {
        final response = await http.get(
          Uri.parse('$url/health'),
          headers: {'Content-Type': 'application/json'},
        ).timeout(Duration(seconds: 2));
        
        if (response.statusCode == 200) {
          baseUrl = url;
          print('✅ Backend found at: $baseUrl');
          return true;
        }
      } catch (e) {
        print('  ❌ $url unreachable');
      }
    }
    
    // Fallback to localhost
    baseUrl = possibleUrls[0];
    print('⚠️  Using fallback: $baseUrl');
    return false;
  }
  Stream<Map<String, dynamic>> get incidentUpdates => _incidentUpdates.stream;
  Stream<Map<String, dynamic>> get vehicleUpdates => _vehicleUpdates.stream;
  Stream<Map<String, dynamic>> get blockageAlerts => _blockageAlerts.stream;
  Stream<Map<String, dynamic>> get rerouteAlerts => _rerouteAlerts.stream;
  Stream<Map<String, dynamic>> get dispatchMessages => _dispatchMessages.stream;
  
  /// Start polling for vehicle position updates (every 500ms)
  Future<void> startVehiclePolling(String vehicleId) async {
    print('✅ Started polling vehicle position');
    _vehiclePoller = Timer.periodic(Duration(milliseconds: 500), (timer) {
      getVehiclePosition(vehicleId).then((data) {
        if (data.isNotEmpty) {
          _vehicleUpdates.add(data);
        }
      }).catchError((e) {
        print('Poll error: $e');
        return null;
      });
    });
  }
  
  /// Start polling for blockage updates (every 500ms to match vehicle updates)
  Future<void> startBlockagePolling() async {
    print('✅ Started polling blockages every 500ms');
    _blockagePoller = Timer.periodic(Duration(milliseconds: 500), (timer) {
      getActiveBlockages().then((blockages) {
        final currentIds = blockages.map((b) => b['id'] ?? '').toSet();
        
        // Detect new blockages
        for (final blockage in blockages) {
          final bid = blockage['id'] ?? '';
          if (!_lastBlockageIds.contains(bid)) {
            _blockageAlerts.add(blockage);
          }
        }
        
        _lastBlockageIds = currentIds.cast<String>();
      }).catchError((e) {
        print('Blockage poll error: $e');
        return null;
      });
    });
  }
  
  /// Stop all polling
  void stopPolling() {
    _vehiclePoller?.cancel();
    _blockagePoller?.cancel();
    print('🔌 Stopped all polling');
  }
  
  // ────────────────────────────────────────────────────────────────────────
  // HTTP API Calls
  // ────────────────────────────────────────────────────────────────────────
  
  /// Report a new emergency incident
  Future<Map<String, dynamic>> reportIncident({
    required String incidentId,
    required String reporterId,
    required List<double> location, // [lat, lon]
    required String type, // accident, medical, fire, etc
    required int severity, // 1-10
    required String description,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/incident/report'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'id': incidentId,
          'reporter_id': reporterId,
          'location': location,
          'type': type,
          'severity': severity,
          'description': description,
          'timestamp': DateTime.now().toIso8601String(),
        }),
      );
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to report incident: ${response.body}');
      }
    } catch (e) {
      print('❌ Error reporting incident: $e');
      rethrow;
    }
  }
  
  /// Find nearest hospitals
  Future<List<Map<String, dynamic>>> findNearestHospitals(
    double lat,
    double lon, {
    int limit = 3,
  }) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/hospitals/nearest?lat=$lat&lon=$lon&limit=$limit'),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return List<Map<String, dynamic>>.from(data['hospitals'] ?? []);
      } else {
        throw Exception('Failed to fetch hospitals: ${response.body}');
      }
    } catch (e) {
      print('❌ Error fetching hospitals: $e');
      rethrow;
    }
  }
  
  /// Main dispatch workflow - calls backend to start complete workflow
  Future<Map<String, dynamic>> dispatchIncident({
    required String incidentId,
    required String vehicleId,
    required double vehicleStartLat,
    required double vehicleStartLon,
    required double incidentLat,
    required double incidentLon,
    required String hospitalId,
    required double hospitalLat,
    required double hospitalLon,
    String cityName = "Indore",
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/dispatch/comprehensive').replace(
        queryParameters: {
          'incident_id': incidentId,
          'vehicle_id': vehicleId,
          'vehicle_start_lat': vehicleStartLat.toString(),
          'vehicle_start_lon': vehicleStartLon.toString(),
          'incident_lat': incidentLat.toString(),
          'incident_lon': incidentLon.toString(),
          'hospital_id': hospitalId,
          'hospital_lat': hospitalLat.toString(),
          'hospital_lon': hospitalLon.toString(),
          'city_name': cityName,
        },
      );
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        print('✅ Dispatch successful: $incidentId');
        return data;
      } else {
        throw Exception('Dispatch failed: ${response.body}');
      }
    } catch (e) {
      print('❌ Error dispatching incident: $e');
      rethrow;
    }
  }
  
  /// Get current vehicle position
  Future<Map<String, dynamic>> getVehiclePosition(String vehicleId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/vehicle/$vehicleId/position'),
      );
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to fetch vehicle position');
      }
    } catch (e) {
      print('❌ Error fetching vehicle position: $e');
      rethrow;
    }
  }
  
  /// Get all active blockages
  Future<List<Map<String, dynamic>>> getActiveBlockages() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/blockages'));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return List<Map<String, dynamic>>.from(data['blockages'] ?? []);
      }
      return [];
    } catch (e) {
      print('❌ Error fetching blockages: $e');
      return [];
    }
  }

  /// Get all vehicles
  Future<List<Map<String, dynamic>>> getAllVehicles() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/vehicles'));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return List<Map<String, dynamic>>.from(data['vehicles'] ?? []);
      }
      return [];
    } catch (e) {
      print('❌ Error fetching vehicles: $e');
      return [];
    }
  }

  /// Get all hospitals
  Future<List<Map<String, dynamic>>> getAllHospitals() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/hospitals/all'));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return List<Map<String, dynamic>>.from(data['hospitals'] ?? []);
      }
      return [];
    } catch (e) {
      print('❌ Error fetching hospitals: $e');
      return [];
    }
  }

  /// Get incident logs
  Future<List<Map<String, dynamic>>> getIncidentLogs(String incidentId) async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/incident/$incidentId/logs'));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return List<Map<String, dynamic>>.from(data['logs'] ?? []);
      }
      return [];
    } catch (e) {
      print('❌ Error fetching mission logs: $e');
      return [];
    }
  }
  
  /// Get blockage impact on a route
  Future<Map<String, dynamic>> getRouteBlockageImpact(
    List<List<double>> route,
  ) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/blockages/route-impact?route=${Uri.encodeComponent(jsonEncode(route))}'),
      );
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        return {'eta_increase_min': 0.0, 'reliability_decrease': 0.0};
      }
    } catch (e) {
      print('❌ Error calculating blockage impact: $e');
      return {'eta_increase_min': 0.0, 'reliability_decrease': 0.0};
    }
  }
  
  /// Infer location from photo
  Future<Map<String, dynamic>> inferLocationFromPhoto({
    String? imageUrl,
    double? fallbackLat,
    double? fallbackLon,
  }) async {
    try {
      final params = <String, String>{
        if (imageUrl != null) 'image_url': imageUrl,
        if (fallbackLat != null) 'fallback_lat': fallbackLat.toString(),
        if (fallbackLon != null) 'fallback_lon': fallbackLon.toString(),
      };
      
      final response = await http.post(
        Uri.parse('$baseUrl/location/infer-from-photo').replace(queryParameters: params),
      );
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        return {'inferred_location': [fallbackLat, fallbackLon], 'method': 'fallback'};
      }
    } catch (e) {
      print('❌ Error inferring location: $e');
      return {'inferred_location': [fallbackLat, fallbackLon], 'method': 'fallback'};
    }
  }
  
  /// Clean up resources
  void dispose() {
    stopPolling();
    _incidentUpdates.close();
    _vehicleUpdates.close();
    _blockageAlerts.close();
    _rerouteAlerts.close();
    _dispatchMessages.close();
    print('✅ Backend service disposed');
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Riverpod Providers
// ────────────────────────────────────────────────────────────────────────────

final backendServiceProvider = Provider<BackendService>((ref) {
  final service = BackendService();
  ref.onDispose(() {
    service.dispose();
  });
  return service;
});