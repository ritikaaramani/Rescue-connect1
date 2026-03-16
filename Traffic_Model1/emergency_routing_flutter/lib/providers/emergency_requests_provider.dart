import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'package:latlong2/latlong.dart';
import '../models/route_model.dart';

// ── Mock Emergency Requests Generator ──────────────────────────────────────

final _rng = Random();

// Indore area locations for realistic mock data
const _indoreLocations = [
  {'label': 'Rajwada Palace, Indore', 'lat': 22.7196, 'lng': 75.8577},
  {'label': 'Palasia Square', 'lat': 22.7234, 'lng': 75.8821},
  {'label': 'Vijay Nagar', 'lat': 22.7533, 'lng': 75.8937},
  {'label': 'Sapna Sangeeta Rd', 'lat': 22.7282, 'lng': 75.8744},
  {'label': 'MR-10 Ring Road', 'lat': 22.7600, 'lng': 75.9200},
  {'label': 'Bhawarkuan Square', 'lat': 22.7053, 'lng': 75.8679},
  {'label': 'Rau Circle', 'lat': 22.6568, 'lng': 75.8250},
  {'label': 'LIG Colony', 'lat': 22.6913, 'lng': 75.8679},
  {'label': 'Bombay Hospital', 'lat': 22.7500, 'lng': 75.9100},
  {'label': 'MY Hospital', 'lat': 22.7180, 'lng': 75.8520},
  {'label': 'Indore Airport', 'lat': 22.7216, 'lng': 75.8019},
  {'label': 'Geeta Bhawan Square', 'lat': 22.7136, 'lng': 75.8647},
  {'label': 'Scheme 78', 'lat': 22.7401, 'lng': 75.9050},
  {'label': 'Khajrana Temple Rd', 'lat': 22.7327, 'lng': 75.9097},
  {'label': 'AB Road, Mhow Naka', 'lat': 22.6900, 'lng': 75.8500},
];

const _hospitals = [
  {'label': 'Apollo Hospital, Indore', 'lat': 22.7533, 'lng': 75.8937},
  {'label': 'CHL Hospital', 'lat': 22.7441, 'lng': 75.8901},
  {'label': 'Medanta Super Specialty', 'lat': 22.7600, 'lng': 75.9000},
  {'label': 'Bombay Hospital Indore', 'lat': 22.7500, 'lng': 75.9100},
  {'label': 'MY Hospital', 'lat': 22.7180, 'lng': 75.8520},
];

const _callers = [
  'Rajesh Kumar — #112',
  'Smt. Priya Sharma',
  'PCR Van Patrol Unit',
  'Indore Fire Station #3',
  'Auto Driver — Bystander',
  'Traffic Police HQ',
  'Control Room Relay',
  'NDRF Alert System',
  'Ambulance Dispatch',
  'Citizen App Report',
];

EmergencyRequest _generateRequest(int index) {
  final origin = _indoreLocations[_rng.nextInt(_indoreLocations.length)];
  final dest = _hospitals[_rng.nextInt(_hospitals.length)];
  final types = EmergencyType.values;
  final priorities = Priority.values;

  return EmergencyRequest(
    id: 'REQ-${1000 + index}',
    type: types[_rng.nextInt(types.length)],
    priority: priorities[_rng.nextInt(priorities.length)],
    originCoord: LatLng(origin['lat'] as double, origin['lng'] as double),
    destCoord: LatLng(dest['lat'] as double, dest['lng'] as double),
    originLabel: origin['label'] as String,
    destLabel: dest['label'] as String,
    timestamp: DateTime.now().subtract(Duration(minutes: _rng.nextInt(45))),
    callerInfo: _callers[_rng.nextInt(_callers.length)],
    witnessReports: [
      if (_rng.nextBool()) WitnessReport(reporterId: 'USR-${1000 + _rng.nextInt(9000)}', textNotes: 'Loud crash heard.', hazardTags: ['Vehicle overturned', 'Possible fuel leak'], hasPhoto: true),
      if (_rng.nextBool()) WitnessReport(reporterId: 'USR-${1000 + _rng.nextInt(9000)}', textNotes: 'Need an ambulance fast', hazardTags: ['Multiple injured'], hasPhoto: true),
      if (_rng.nextBool()) WitnessReport(reporterId: 'USR-${1000 + _rng.nextInt(9000)}', textNotes: 'Road is blocked', hazardTags: ['Road debris'], hasPhoto: false),
    ],
    videoFeedUrl: _rng.nextBool() ? 'live_feed_active' : null,
    ambulanceEtaMin: 4 + _rng.nextInt(10),
    patientCondition: _rng.nextBool() ? 'Unconscious' : 'Stable',
    assignedHospital: dest['label'] as String,
  );
}

// ── Providers ──────────────────────────────────────────────────────────────

// Emergency Requests
class EmergencyRequestsNotifier extends StateNotifier<List<EmergencyRequest>> {
  Timer? _timer;

  EmergencyRequestsNotifier() : super([]) {
    _load();

    // Add a new one every 30s
    _timer = Timer.periodic(const Duration(seconds: 30), (_) {
      final req = _generateRequest(state.length + 100);
      state = [req, ...state]
        ..sort((a, b) => a.priority.index.compareTo(b.priority.index));
      _save();
    });
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
        _seed();
      }
    } else {
      _seed();
    }
  }

  void _seed() {
    state = List.generate(6, (i) => _generateRequest(i))
      ..sort((a, b) => a.priority.index.compareTo(b.priority.index));
    _save();
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    final data = json.encode(state.map((r) => r.toJson()).toList());
    await prefs.setString('emergency_requests', data);
  }

  @override
  void dispose() {
    _timer?.cancel();
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
  (ref) => EmergencyRequestsNotifier(),
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
