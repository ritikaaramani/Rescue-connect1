import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import '../models/route_model.dart';
import '../services/backend_service.dart';

// ── Providers ──────────────────────────────────────────────────────────────

final mainAppTabProvider = StateProvider<int>((ref) => 0);
final selectedIncidentForRoutingProvider = StateProvider<EmergencyRequest?>((ref) => null);
final dispatchFocusPostIdProvider = StateProvider<String?>((ref) => null);

// Supabase direct config (same as backend_service.dart)
const _supabaseUrl = 'https://uhlnwyrikuiprkuubloh.supabase.co';
const _supabaseKey = 'sb_publishable_3AB7L_OofX-B7hlO7mWUrA_vrSq5cBO';

// Emergency Requests
class EmergencyRequestsNotifier extends StateNotifier<List<EmergencyRequest>> {
  Timer? _timer;
  Timer? _pendingDispatchTimer;
  final Ref ref;

  EmergencyRequestsNotifier(this.ref) : super([]) {
    _load();
    _fetchRealData();
    // Poll every 15s for general incident data
    _timer = Timer.periodic(const Duration(seconds: 15), (_) {
      _fetchRealData();
    });
    // Poll every 5s for authority-triggered dispatches
    _pendingDispatchTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      _checkPendingFlutterDispatches();
    });
  }

  Future<void> _fetchRealData() async {
    try {
      final backendService = ref.read(backendServiceProvider);
      final incidents = await backendService.getActiveIncidents();
      
      final newRequests = incidents.map((data) {
        return EmergencyRequest(
          id: data['id'] ?? 'N/A',
          type: _parseEmergencyType(data['type']),
          rawType: data['type']?.toString() ?? 'Emergency',
          priority: _parsePriority(data['priority']),
          originCoord: LatLng(data['originCoord']['latitude'], data['originCoord']['longitude']),
          destCoord: LatLng(data['destCoord']['latitude'], data['destCoord']['longitude']),
          originLabel: data['originLabel'] ?? 'Unknown Location',
          destLabel: data['destLabel'] ?? 'Nearest Hospital',
          timestamp: DateTime.tryParse(data['timestamp'] ?? '') ?? DateTime.now(),
          callerInfo: data['callerInfo'] ?? 'Citizen Report',
          witnessReports: [], // Can parse witnesses here if provided
          videoFeedUrl: data['videoFeedUrl'],
          ambulanceEtaMin: data['ambulanceEtaMin'] ?? 10,
          patientCondition: data['patientCondition'] ?? 'Unknown',
          assignedHospital: data['assignedHospital'],
          state: _parseState(data['state']),
        );
      }).toList();
      
      newRequests.sort((a, b) => a.priority.index.compareTo(b.priority.index));
      state = newRequests;
      _save();
    } catch (e) {
      debugPrint('Error polling active incidents: $e');
    }
  }

  /// Check Supabase for posts where flutter_dispatch_pending=true.
  /// When found: clear the flag, navigate to Live Map, auto-fill the incident,
  /// and add to the Active Missions (dispatches) list.
  Future<void> _checkPendingFlutterDispatches() async {
    try {
      final url = Uri.parse(
        '$_supabaseUrl/rest/v1/posts?flutter_dispatch_pending=eq.true&limit=5',
      );
      final response = await http.get(url, headers: {
        'apikey': _supabaseKey,
        'Authorization': 'Bearer $_supabaseKey',
        'Content-Type': 'application/json',
      });

      if (response.statusCode != 200) return;
      final List<dynamic> posts = json.decode(response.body);
      if (posts.isEmpty) return;

      for (final post in posts) {
        // 1. Clear the flag immediately to avoid double-processing
        final postId = post['id'].toString();
        await http.patch(
          Uri.parse('$_supabaseUrl/rest/v1/posts?id=eq.$postId'),
          headers: {
            'apikey': _supabaseKey,
            'Authorization': 'Bearer $_supabaseKey',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal',
          },
          body: json.encode({'flutter_dispatch_pending': false}),
        );

        // 2. Extract coordinates
        double lat = 22.7196; // Default Indore
        double lon = 75.8577;
        if (post['inferred_latitude'] != null && post['inferred_longitude'] != null) {
          lat = double.tryParse(post['inferred_latitude'].toString()) ?? lat;
          lon = double.tryParse(post['inferred_longitude'].toString()) ?? lon;
        } else if (post['latitude'] != null && post['longitude'] != null) {
          lat = double.tryParse(post['latitude'].toString()) ?? lat;
          lon = double.tryParse(post['longitude'].toString()) ?? lon;
        } else if (post['location'] is Map) {
          final location = post['location'] as Map;
          final dynamic rawLat = location['lat'] ?? location['latitude'];
          final dynamic rawLon = location['lon'] ?? location['longitude'];
          if (rawLat != null && rawLon != null) {
            lat = double.tryParse(rawLat.toString()) ?? lat;
            lon = double.tryParse(rawLon.toString()) ?? lon;
          }
        }

        // 3. Extract incident type & label
        final rawType = post['disaster_type']?.toString() ?? 'Flood';
        final EmergencyType eType = _parseEmergencyType(rawType);
        String locLabel = 'Disaster Location';
        if (post['extracted_locations'] is List &&
            (post['extracted_locations'] as List).isNotEmpty) {
          locLabel = post['extracted_locations'][0].toString();
        }

        // 4. Build EmergencyRequest for HomeScreen auto-fill
        final coord = LatLng(lat, lon);
        final req = EmergencyRequest(
          id: postId,
          type: eType,
          rawType: rawType,
          priority: Priority.high,
          originCoord: coord,
          destCoord: LatLng(lat + 0.015, lon + 0.02), // Rough hospital direction
          originLabel: locLabel,
          destLabel: 'Nearest Hospital',
          timestamp: DateTime.tryParse(post['created_at'] ?? '') ?? DateTime.now(),
          callerInfo: 'Authority Dispatch',
          witnessReports: [],
          videoFeedUrl: post['image_url'],
          ambulanceEtaMin: 10,
          patientCondition: 'Unknown',
          assignedHospital: null,
          state: IncidentState.dispatched,
        );

        // 5. Set the incident for HomeScreen → triggers auto-fill + hospital search
        ref.read(selectedIncidentForRoutingProvider.notifier).state = req;

        // 6. Navigate to Incoming Dispatch tab and focus this report
        ref.read(mainAppTabProvider.notifier).state = 0;
        ref.read(dispatchFocusPostIdProvider.notifier).state = postId;

        // 7. Add an immediate ActiveDispatch entry so MISSIONS tab also updates
        final dispatch = ActiveDispatch(
          id: 'AUTH-$postId',
          type: eType,
          origin: locLabel,
          destination: 'Nearest Hospital',
          originCoord: coord,
          destCoord: LatLng(lat + 0.015, lon + 0.02),
          etaMin: 10.0,
          dispatchedAt: DateTime.now(),
          cityName: 'Disaster Zone',
          priority: Priority.high,
        );
        ref.read(activeDispatchesProvider.notifier).addDispatch(dispatch);

        debugPrint('✅ Flutter dispatch triggered for post $postId at ($lat, $lon)');
      }
    } catch (e) {
      debugPrint('Error checking pending flutter dispatches: $e');
    }
  }

  Priority _parsePriority(dynamic priorityStr) {
    if (priorityStr == 'High') return Priority.high;
    if (priorityStr == 'Medium') return Priority.medium;
    return Priority.low;
  }

  EmergencyType _parseEmergencyType(dynamic typeStr) {
    final str = typeStr.toString().toLowerCase();
    if (str.contains('flood')) return EmergencyType.flood;
    if (str.contains('fire')) return EmergencyType.fire;
    if (str.contains('police') || str.contains('crime')) return EmergencyType.police;
    if (str.contains('medical') || str.contains('ambulance') || str.contains('injury')) {
      return EmergencyType.ambulance;
    }
    if (str.contains('accident') || str.contains('crash')) return EmergencyType.accident;
    return EmergencyType.accident;
  }

  IncidentState _parseState(dynamic stateStr) {
    final str = stateStr.toString().toLowerCase();
    if (str.contains('assigned')) return IncidentState.dispatched;
    if (str.contains('in-progress')) return IncidentState.enRoute;
    if (str.contains('completed')) return IncidentState.completed;
    return IncidentState.reported;
  }
  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final data = prefs.getString('emergency_requests');
    if (data != null) {
      try {
        final List list = json.decode(data);
        state = list.map((e) => EmergencyRequest.fromJson(e)).toList();
      } catch (e) {
        debugPrint('Error loading requests: $e');
      }
    }
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    final data = json.encode(state.map((r) => r.toJson()).toList());
    await prefs.setString('emergency_requests', data);
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pendingDispatchTimer?.cancel();
    super.dispose();
  }

  void updateState(String id, IncidentState newState) {
    state = [
      for (final r in state)
        if (r.id == id) r.copyWith(state: newState) else r,
    ];
    _save();
  }

  void addWitnessReport(String id, WitnessReport report) {
    state = [
      for (final r in state)
        if (r.id == id)
          r.copyWith(witnessReports: [...r.witnessReports, report])
        else
          r,
    ];
    _save();
  }

  List<EmergencyRequest> get pending =>
      state.where((r) => r.state != IncidentState.dispatched && r.state != IncidentState.completed).toList();
}

final emergencyRequestsProvider =
    StateNotifierProvider<EmergencyRequestsNotifier, List<EmergencyRequest>>(
  (ref) => EmergencyRequestsNotifier(ref),
);

// Active Dispatches (multi-dispatch)
class ActiveDispatchesNotifier extends StateNotifier<List<ActiveDispatch>> {
  Timer? _cleanupTimer;

  ActiveDispatchesNotifier() : super([]) {
    _load();
    _cleanupTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      // Auto-remove arrived dispatches after 2 minutes
      final newState = state.where((d) => !d.isArrived || d.elapsedMin < d.etaMin + 2).toList();
      if (newState.length != state.length) {
        state = newState;
        _save();
      }
    });
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final data = prefs.getString('active_dispatches');
    if (data != null) {
      try {
        final List list = json.decode(data);
        state = list.map((e) => ActiveDispatch.fromJson(e)).toList();
      } catch (e) {
        debugPrint('Error loading dispatches: $e');
      }
    }
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    final data = json.encode(state.map((d) => d.toJson()).toList());
    await prefs.setString('active_dispatches', data);
  }

  @override
  void dispose() {
    _cleanupTimer?.cancel();
    super.dispose();
  }

  void addDispatch(ActiveDispatch dispatch) {
    state = [dispatch, ...state];
    _save();
  }

  void removeDispatch(String id) {
    state = state.where((d) => d.id != id).toList();
    _save();
  }
}

final activeDispatchesProvider =
    StateNotifierProvider<ActiveDispatchesNotifier, List<ActiveDispatch>>(
  (ref) => ActiveDispatchesNotifier(),
);

// Dispatch team messages / alerts
class AlertsNotifier extends StateNotifier<List<Map<String, String>>> {
  AlertsNotifier()
      : super([
          {'from': 'Control Room', 'msg': 'All units standby — peak traffic hour active.', 'time': '12:45 PM', 'type': 'info'},
          {'from': 'Traffic Police HQ', 'msg': 'AB Road blocked near Mhow Naka — accident reported.', 'time': '12:38 PM', 'type': 'warning'},
          {'from': 'NDRF', 'msg': 'Monsoon alert: waterlogging on MR-10 Ring Road.', 'time': '12:30 PM', 'type': 'critical'},
          {'from': 'Ambulance UP-14-342', 'msg': 'Patient picked up. ETA to Bombay Hospital: 8 min.', 'time': '12:25 PM', 'type': 'success'},
        ]);

  void addAlert(String from, String msg, String type) {
    final now = DateTime.now();
    final hour = now.hour > 12 ? now.hour - 12 : now.hour;
    final ampm = now.hour >= 12 ? 'PM' : 'AM';
    final time = '$hour:${now.minute.toString().padLeft(2, '0')} $ampm';
    state = [
      {'from': from, 'msg': msg, 'time': time, 'type': type},
      ...state,
    ];
    if (state.length > 50) state = state.sublist(0, 50);
  }
}

final alertsProvider =
    StateNotifierProvider<AlertsNotifier, List<Map<String, String>>>(
  (ref) => AlertsNotifier(),
);
