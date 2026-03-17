import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Unified Backend Service - HTTP Polling Based (No WebSocket)
class BackendService {
  // Try multiple URLs to find working backend
  static const List<String> possibleUrls = [
    'http://localhost:9000',
    'http://127.0.0.1:9000',
    'http://192.168.1.1:9000',  // Common router IP
  ];
  
  String baseUrl = 'http://localhost:9000';
  
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
  
  /// Run the full ML pipeline (M1 → M2 → M3) for a routing request
  Future<Map<String, dynamic>> runMLPipeline({
    required String vehicleId,
    String start = 'hospital',
    String destination = 'accident_location',
    String city = 'Indore',
    double currentSpeed = 25.0,
    double remainingDistance = 5200.0,
    double weatherCoeff = 1.0,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/route/ml-pipeline'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'start': start,
          'destination': destination,
          'city': city,
          'vehicle_id': vehicleId,
          'current_speed': currentSpeed,
          'remaining_distance': remainingDistance,
          'weather_coeff': weatherCoeff,
        }),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else {
        throw Exception('ML pipeline failed: ${response.body}');
      }
    } catch (e) {
      print('ML pipeline error: $e');
      // Return mock fallback so the UI never crashes
      return {
        'status': 'client_fallback',
        'best_route': {
          'route_id': 'bypass_route',
          'reliability': 0.88,
          'eta_minutes': 13.0,
        },
        'model3_decision': {'action': 'stay'},
      };
    }
  }

  /// Fetch citizen disaster posts (high severity, pending dispatch)
  Future<List<Map<String, dynamic>>> getCitizenPosts({
    int severityMin = 6,
    int limit = 20,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/citizen/posts').replace(
        queryParameters: {
          'severity_min': severityMin.toString(),
          'limit': limit.toString(),
        },
      );
      final response = await http.get(uri);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return List<Map<String, dynamic>>.from(data['posts'] ?? []);
      }
      return [];
    } catch (e) {
      print('Error fetching citizen posts: $e');
      return [];
    }
  }

  /// Mark a citizen post as dispatched
  Future<bool> markPostDispatched(String postId) async {
    try {
      final supabaseUrl = 'https://uhlnwyrikuiprkuubloh.supabase.co';
      final supabaseKey = 'sb_publishable_3AB7L_OofX-B7hlO7mWUrA_vrSq5cBO';
      final response = await http.patch(
        Uri.parse('$supabaseUrl/rest/v1/posts?id=eq.$postId'),
        headers: {
          'apikey': supabaseKey,
          'Authorization': 'Bearer $supabaseKey',
          'Content-Type': 'application/json',
          'Prefer': 'return=minimal',
        },
        body: jsonEncode({'dispatch_status': 'assigned'})
      );
      return response.statusCode >= 200 && response.statusCode < 300;
    } catch (e) {
      print('Error marking post dispatched to Supabase: $e');
      return false;
    }
  }

  /// Get active incidents directly from Supabase REST API
  Future<List<Map<String, dynamic>>> getActiveIncidents() async {
    try {
      final supabaseUrl = 'https://uhlnwyrikuiprkuubloh.supabase.co';
      final supabaseKey = 'sb_publishable_3AB7L_OofX-B7hlO7mWUrA_vrSq5cBO';
      
      final url = Uri.parse('$supabaseUrl/rest/v1/posts?dispatch_status=in.(pending,assigned,in-progress)&order=created_at.desc');
      final response = await http.get(
        url,
        headers: {
          'apikey': supabaseKey,
          'Authorization': 'Bearer $supabaseKey',
          'Content-Type': 'application/json',
        },
      );
      
      if (response.statusCode == 200) {
        final List<dynamic> posts = jsonDecode(response.body);
        
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
      print('❌ Error fetching direct supabase incidents: $e');
      return [];
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

/// Provider that exposes a function to run the ML pipeline
final mlPipelineProvider = Provider<Future<Map<String, dynamic>> Function({
  required String vehicleId,
  String city,
})>((ref) {
  final service = ref.watch(backendServiceProvider);
  return ({required String vehicleId, String city = 'Indore'}) =>
      service.runMLPipeline(vehicleId: vehicleId, city: city);
});