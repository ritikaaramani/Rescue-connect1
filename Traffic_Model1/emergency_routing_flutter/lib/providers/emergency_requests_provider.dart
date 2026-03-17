import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'package:latlong2/latlong.dart';
import '../models/route_model.dart';
import '../services/backend_service.dart';
import '../services/supabase_location_service.dart';

// ── Providers ──────────────────────────────────────────────────────────────

final mainAppTabProvider = StateProvider<int>((ref) => 0);
final selectedIncidentForRoutingProvider = StateProvider<EmergencyRequest?>((ref) => null);

// Emergency Requests
class EmergencyRequestsNotifier extends StateNotifier<List<EmergencyRequest>> {
  Timer? _timer;
  StreamSubscription<IncidentLocationUpdate>? _locationSub;
  final Ref ref;

  EmergencyRequestsNotifier(this.ref) : super([]) {
    _load();
    _fetchRealData();
    // Poll every 15s as a safety net for missed realtime events
    _timer = Timer.periodic(const Duration(seconds: 15), (_) {
      _fetchRealData();
    });
    // Also listen to Supabase realtime for instant updates
    _subscribeToRealtime();
  }

  void _subscribeToRealtime() {
    final locationService = ref.read(supabaseLocationServiceProvider);
    _locationSub = locationService.locationUpdates.listen((update) {
      // Check if this post already exists in state
      final exists = state.any((r) => r.id == update.postId);
      if (!exists) {
        // Create a new EmergencyRequest from the realtime update
        final newRequest = EmergencyRequest(
          id: update.postId,
          type: _parseEmergencyType(update.disasterType),
          rawType: update.disasterType,
          priority: _parseRealtimePriority(update.severity),
          originCoord: update.incidentCoord,
          destCoord: update.hospitalCoord ?? const LatLng(22.7533, 75.8937),
          originLabel: update.locationLabel,
          destLabel: update.hospitalName ?? 'Nearest Hospital',
          timestamp: update.receivedAt,
          callerInfo: 'ML Auto-Detected',
          witnessReports: [],
          ambulanceEtaMin: 10,
          patientCondition: 'Unknown',
          state: IncidentState.reported,
        );
        state = [newRequest, ...state];
        _save();
        debugPrint('🚨 Realtime: New incident added → ${update.locationLabel}');
      }
    });
  }

  Priority _parseRealtimePriority(String severity) {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'high':
        return Priority.high;
      case 'medium':
        return Priority.medium;
      default:
        return Priority.low;
    }
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

  Priority _parsePriority(dynamic priorityStr) {
    if (priorityStr == 'High') return Priority.high;
    if (priorityStr == 'Medium') return Priority.medium;
    return Priority.low;
  }

  EmergencyType _parseEmergencyType(dynamic typeStr) {
    final str = typeStr.toString().toLowerCase();
    if (str.contains('medical')) return EmergencyType.ambulance;
    if (str.contains('fire')) return EmergencyType.fire;
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
    _locationSub?.cancel();
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
