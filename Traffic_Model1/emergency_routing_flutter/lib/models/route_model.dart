import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';

// ── Emergency type ─────────────────────────────────────────────────────────

enum EmergencyType {
  ambulance('Ambulance', Icons.local_hospital, Color(0xFFFF1744), 'Medical Emergency'),
  fire('Fire Engine', Icons.local_fire_department, Color(0xFFFF6D00), 'Fire & Rescue'),
  police('Police', Icons.local_police, Color(0xFF2979FF), 'Law Enforcement'),
  flood('Flood Relief', Icons.water, Color(0xFF00B0FF), 'Disaster Relief'),
  accident('Accident', Icons.car_crash, Color(0xFFFFD600), 'Road Accident');

  const EmergencyType(this.label, this.icon, this.color, this.description);
  final String label;
  final IconData icon;
  final Color color;
  final String description;

  static EmergencyType fromName(String name) =>
      EmergencyType.values.firstWhere((e) => e.name == name);
}

// ── India-specific factors ─────────────────────────────────────────────────

class IndiaFactor {
  final String name;
  final String emoji;
  final double delayMultiplier; // 1.0 = no extra delay, 1.2 = 20% extra
  final String description;
  final Color color;

  const IndiaFactor({
    required this.name,
    required this.emoji,
    required this.delayMultiplier,
    required this.description,
    required this.color,
  });

  factory IndiaFactor.fromJson(Map<String, dynamic> json) {
    return IndiaFactor(
      name: json['name'],
      emoji: json['emoji'],
      delayMultiplier: (json['delay_multiplier'] as num).toDouble(),
      description: json['description'] ?? '',
      color: const Color(0xFFFFD600), // Default warning color for incoming factors
    );
  }
}

// ── Weather condition at route location ────────────────────────────────────

class WeatherCondition {
  final String label;         // "Heavy Rain", "Dense Fog", "Clear", etc.
  final String emoji;
  final double delayMultiplier;
  final String description;   // Human-readable impact on emergency routing
  final Color color;
  final double? temperatureC;
  final double? windSpeedKmh;
  final double? precipitationMm;
  final int weatherCode;      // WMO weather code

  const WeatherCondition({
    required this.label,
    required this.emoji,
    required this.delayMultiplier,
    required this.description,
    required this.color,
    this.temperatureC,
    this.windSpeedKmh,
    this.precipitationMm,
    required this.weatherCode,
  });

  bool get isSevere => delayMultiplier >= 1.15;
  bool get isClear => delayMultiplier <= 1.02;
}

// ── Road condition ─────────────────────────────────────────────────────────

class RoadCondition {
  final String name;
  final String emoji;
  final double delayMultiplier;
  final String description;
  final Color color;

  const RoadCondition({
    required this.name,
    required this.emoji,
    required this.delayMultiplier,
    required this.description,
    required this.color,
  });
}

// ── Combined India factors ─────────────────────────────────────────────────

class IndiaFactors {
  final List<IndiaFactor> active;
  final double totalMultiplier;
  final bool isRushHour;
  final bool isMonsoon;
  final WeatherCondition? weather;           // Live weather at route location
  final List<RoadCondition> roadConditions;  // Road-specific hazards

  const IndiaFactors({
    required this.active,
    required this.totalMultiplier,
    required this.isRushHour,
    required this.isMonsoon,
    this.weather,
    this.roadConditions = const [],
  });

  bool get hasFactors =>
      active.isNotEmpty ||
      isRushHour ||
      isMonsoon ||
      (weather != null && !weather!.isClear) ||
      roadConditions.isNotEmpty;

  bool get hasWeatherOrRoad =>
      (weather != null && !weather!.isClear) || roadConditions.isNotEmpty;
}

// ── Route result model ─────────────────────────────────────────────────────

class RouteResult {
  final List<LatLng> polyline;
  final double distanceKm;

  // Standard ETA (what Uber/Google shows - OSRM base, limited India context)
  final double standardEtaMin;

  // Our predicted "actual" ETA without AI routing (accounting for India factors)
  final double predictedActualEtaMin;

  // Our AI emergency route ETA (priority routing + congestion bypass)
  final double aiEtaMin;

  // Time saved vs what the user would expect from a standard app
  final double timeSavedMin;

  // Congestion data from AI model
  final double congestionScore;
  final double congestionUncertainty;

  // India factors detected
  final IndiaFactors indiaFactors;

  // Emergency type used
  final EmergencyType emergencyType;

  // City
  final String cityName;

  // Confidence in AI prediction (0-100)
  final int confidencePct;

  // AI Guidance (Phase 4)
  final String? recommendedLane;
  final String? reasoning;

  const RouteResult({
    required this.polyline,
    required this.distanceKm,
    required this.standardEtaMin,
    required this.predictedActualEtaMin,
    required this.aiEtaMin,
    required this.timeSavedMin,
    required this.congestionScore,
    required this.congestionUncertainty,
    required this.indiaFactors,
    required this.emergencyType,
    required this.cityName,
    required this.confidencePct,
    this.recommendedLane,
    this.reasoning,
  });

  String get congestionLabel {
    if (congestionScore < 0.3) return 'Clear';
    if (congestionScore < 0.6) return 'Moderate';
    return 'Heavy';
  }

  Color get congestionColor {
    if (congestionScore < 0.3) return const Color(0xFF00E676);
    if (congestionScore < 0.6) return const Color(0xFFFFD600);
    return const Color(0xFFFF1744);
  }

  String get distanceLabel => '${distanceKm.toStringAsFixed(1)} km';
  String get aiEtaLabel => '${aiEtaMin.toStringAsFixed(0)} min';
  String get standardEtaLabel => '${standardEtaMin.toStringAsFixed(0)} min';
  String get timeSavedLabel => '${timeSavedMin.abs().toStringAsFixed(0)} min';
  bool get isFaster => timeSavedMin > 0;
}

// ── Dispatch log entry ─────────────────────────────────────────────────────

class ActiveDispatch {
  final String id;
  final EmergencyType type;
  final String origin;
  final String destination;
  final LatLng originCoord;
  final LatLng destCoord;
  final double etaMin;
  final DateTime dispatchedAt;
  final String cityName;
  final Priority priority;

  const ActiveDispatch({
    required this.id,
    required this.type,
    required this.origin,
    required this.destination,
    required this.originCoord,
    required this.destCoord,
    required this.etaMin,
    required this.dispatchedAt,
    required this.cityName,
    this.priority = Priority.high,
  });

  double get elapsedMin => DateTime.now().difference(dispatchedAt).inMinutes.toDouble();
  double get remainingMin => (etaMin - elapsedMin).clamp(0, double.infinity);
  bool get isArrived => remainingMin < 0.5;

  Map<String, dynamic> toJson() => {
    'id': id,
    'type': type.name,
    'origin': origin,
    'destination': destination,
    'originCoord': {'lat': originCoord.latitude, 'lng': originCoord.longitude},
    'destCoord': {'lat': destCoord.latitude, 'lng': destCoord.longitude},
    'etaMin': etaMin,
    'dispatchedAt': dispatchedAt.toIso8601String(),
    'cityName': cityName,
    'priority': priority.name,
  };

  factory ActiveDispatch.fromJson(Map<String, dynamic> json) => ActiveDispatch(
    id: json['id'],
    type: EmergencyType.fromName(json['type']),
    origin: json['origin'],
    destination: json['destination'],
    originCoord: LatLng(json['originCoord']['lat'], json['originCoord']['lng']),
    destCoord: LatLng(json['destCoord']['lat'], json['destCoord']['lng']),
    etaMin: (json['etaMin'] as num).toDouble(),
    dispatchedAt: DateTime.parse(json['dispatchedAt']),
    cityName: json['cityName'],
    priority: Priority.fromName(json['priority']),
  );
}

// ── Priority levels ────────────────────────────────────────────────────────

enum Priority {
  critical('CRITICAL', Color(0xFFFF1744), Icons.warning_amber),
  high('HIGH', Color(0xFFFF6D00), Icons.priority_high),
  medium('MEDIUM', Color(0xFFFFD600), Icons.remove),
  low('LOW', Color(0xFF00E676), Icons.arrow_downward);

  const Priority(this.label, this.color, this.icon);
  final String label;
  final Color color;
  final IconData icon;

  static Priority fromName(String name) =>
      Priority.values.firstWhere((p) => p.name == name);
}

// ── State Models ───────────────────────────────────────────────────────────

enum IncidentState { reported, verified, dispatched, enRoute, onScene, patientPicked, completed }

enum VehicleState { AVAILABLE, DISPATCHED, EN_ROUTE, AT_SCENE, TRANSPORTING, RETURNING, OFFLINE }

class WitnessReport {
  final String reporterId;
  final String textNotes;
  final List<String> hazardTags;
  final bool hasPhoto;

  WitnessReport({required this.reporterId, required this.textNotes, required this.hazardTags, this.hasPhoto = false});

  Map<String, dynamic> toJson() => {
    'reporterId': reporterId,
    'textNotes': textNotes,
    'hazardTags': hazardTags,
    'hasPhoto': hasPhoto,
  };

  factory WitnessReport.fromJson(Map<String, dynamic> json) => WitnessReport(
    reporterId: json['reporterId'],
    textNotes: json['textNotes'],
    hazardTags: List<String>.from(json['hazardTags']),
    hasPhoto: json['hasPhoto'] ?? false,
  );
}

class EmergencyRequest {
  final String id;
  final EmergencyType type;
  final Priority priority;
  final LatLng originCoord;
  final LatLng destCoord;
  final String originLabel;
  final String destLabel;
  final DateTime timestamp;
  IncidentState state;
  final String callerInfo;
  final List<WitnessReport> witnessReports;

  // Shared Situation Room fields
  final String? videoFeedUrl; // Null if no video
  final int? ambulanceEtaMin;
  final String? patientCondition;
  final String? assignedHospital;

  EmergencyRequest({
    required this.id,
    required this.type,
    required this.priority,
    required this.originCoord,
    required this.destCoord,
    required this.originLabel,
    required this.destLabel,
    required this.timestamp,
    this.state = IncidentState.reported,
    this.callerInfo = 'Unknown Caller',
    this.witnessReports = const [],
    this.videoFeedUrl,
    this.ambulanceEtaMin,
    this.patientCondition,
    this.assignedHospital,
  });

  int get photosUploaded => witnessReports.where((w) => w.hasPhoto).length;

  String get timeAgo {
    final diff = DateTime.now().difference(timestamp);
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    return '${diff.inHours}h ago';
  }

  EmergencyRequest copyWith({
    IncidentState? state, 
    List<WitnessReport>? witnessReports,
    String? patientCondition,
    int? ambulanceEtaMin,
    String? assignedHospital,
  }) {
    return EmergencyRequest(
      id: id,
      type: type,
      priority: priority,
      originCoord: originCoord,
      destCoord: destCoord,
      originLabel: originLabel,
      destLabel: destLabel,
      timestamp: timestamp,
      state: state ?? this.state,
      callerInfo: callerInfo,
      witnessReports: witnessReports ?? this.witnessReports,
      videoFeedUrl: videoFeedUrl,
      ambulanceEtaMin: ambulanceEtaMin ?? this.ambulanceEtaMin,
      patientCondition: patientCondition ?? this.patientCondition,
      assignedHospital: assignedHospital ?? this.assignedHospital,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'type': type.name,
    'priority': priority.name,
    'originCoord': {'lat': originCoord.latitude, 'lng': originCoord.longitude},
    'destCoord': {'lat': destCoord.latitude, 'lng': destCoord.longitude},
    'originLabel': originLabel,
    'destLabel': destLabel,
    'timestamp': timestamp.toIso8601String(),
    'state': state.name,
    'callerInfo': callerInfo,
    'witnessReports': witnessReports.map((e) => e.toJson()).toList(),
    'videoFeedUrl': videoFeedUrl,
    'ambulanceEtaMin': ambulanceEtaMin,
    'patientCondition': patientCondition,
    'assignedHospital': assignedHospital,
  };

  factory EmergencyRequest.fromJson(Map<String, dynamic> json) => EmergencyRequest(
    id: json['id'],
    type: EmergencyType.fromName(json['type']),
    priority: Priority.fromName(json['priority']),
    originCoord: LatLng(json['originCoord']['lat'], json['originCoord']['lng']),
    destCoord: LatLng(json['destCoord']['lat'], json['destCoord']['lng']),
    originLabel: json['originLabel'],
    destLabel: json['destLabel'],
    timestamp: DateTime.parse(json['timestamp']),
    state: IncidentState.values.firstWhere((e) => e.name == json['state']),
    callerInfo: json['callerInfo'],
    witnessReports: (json['witnessReports'] as List).map((e) => WitnessReport.fromJson(e)).toList(),
    videoFeedUrl: json['videoFeedUrl'],
    ambulanceEtaMin: json['ambulanceEtaMin'],
    patientCondition: json['patientCondition'],
    assignedHospital: json['assignedHospital'],
  );
}

