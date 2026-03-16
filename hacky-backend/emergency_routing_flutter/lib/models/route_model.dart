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
}

class IndiaFactors {
  final List<IndiaFactor> active;
  final double totalMultiplier;
  final bool isRushHour;
  final bool isMonsoon;

  const IndiaFactors({
    required this.active,
    required this.totalMultiplier,
    required this.isRushHour,
    required this.isMonsoon,
  });

  bool get hasFactors => active.isNotEmpty || isRushHour || isMonsoon;
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
  final double etaMin;
  final DateTime dispatchedAt;
  final String cityName;

  const ActiveDispatch({
    required this.id,
    required this.type,
    required this.origin,
    required this.destination,
    required this.etaMin,
    required this.dispatchedAt,
    required this.cityName,
  });

  double get elapsedMin =>
      DateTime.now().difference(dispatchedAt).inSeconds / 60.0;
  double get remainingMin => (etaMin - elapsedMin).clamp(0, double.infinity);
  bool get isArrived => remainingMin < 0.5;
}
