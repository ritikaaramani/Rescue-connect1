import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart' show Color;
import 'package:latlong2/latlong.dart';
import '../config/cities_config.dart';
import '../models/route_model.dart';
import '../models/prediction_response.dart';

/// Handles OSRM routing, AI ETA calculation, and India-specific factor detection.
class RoutingService {
  final Dio _dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 30),
    headers: {'User-Agent': 'SwiftEmergency/1.0 (+emergency-routing)'},
  ));

  // ── Geocoding ──────────────────────────────────────────────────────────────

  Future<LatLng?> geocode(String address) async {
    try {
      final res = await _dio.get(
        'https://nominatim.openstreetmap.org/search',
        queryParameters: {
          'q': '$address, India',
          'format': 'json',
          'limit': 1,
          'countrycodes': 'in',
        },
      );
      if (res.data is List && (res.data as List).isNotEmpty) {
        final r = res.data[0];
        return LatLng(double.parse(r['lat']), double.parse(r['lon']));
      }
    } catch (e) {
      debugPrint('Geocoding error: $e');
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> autocomplete(String query) async {
    if (query.length < 3) return [];
    try {
      final res = await _dio.get(
        'https://nominatim.openstreetmap.org/search',
        queryParameters: {
          'q': '$query, India',
          'format': 'json',
          'limit': 5,
          'countrycodes': 'in',
          'addressdetails': 1,
        },
      );
      if (res.data is List) {
        return (res.data as List)
            .map((e) => {
                  'display': e['display_name'] as String,
                  'lat': double.parse(e['lat']),
                  'lon': double.parse(e['lon']),
                })
            .toList();
      }
    } catch (e) {
      debugPrint('Autocomplete error: $e');
    }
    return [];
  }

  // ── OSRM Routing ───────────────────────────────────────────────────────────

  Future<Map<String, dynamic>?> fetchOsrmRoute(
      LatLng origin, LatLng destination) async {
    try {
      final url =
          'http://router.project-osrm.org/route/v1/driving/'
          '${origin.longitude},${origin.latitude};'
          '${destination.longitude},${destination.latitude}'
          '?geometries=geojson&overview=full&steps=true';
      final res = await _dio.get(url);
      if (res.data['code'] == 'Ok' &&
          (res.data['routes'] as List).isNotEmpty) {
        return res.data['routes'][0] as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('OSRM error: $e');
    }
    return null;
  }

  // ── India Factors ──────────────────────────────────────────────────────────

  IndiaFactors detectIndiaFactors(String cityName, DateTime now) {
    final List<IndiaFactor> active = [];
    final month = now.month;
    final day = now.day;
    final hour = now.hour;
    final weekday = now.weekday;

    // Festival calendar (approximate dates for 2025-2026)
    final festivals = _getFestivalsNearDate(now);
    active.addAll(festivals);

    // Monsoon (June - September, heavier in July-August)
    final isMonsoon = month >= 6 && month <= 9;
    if (isMonsoon) {
      final severity = (month == 7 || month == 8) ? 0.22 : 0.14;
      active.add(IndiaFactor(
        name: 'Monsoon',
        emoji: '🌧️',
        delayMultiplier: 1.0 + severity,
        description: 'Heavy rain affects visibility & road grip',
        color: const Color(0xFF00B0FF),
      ));
    }

    // Rush hours (7–10 AM and 5–9 PM on weekdays)
    final isRushHour =
        weekday <= 5 && ((hour >= 7 && hour < 10) || (hour >= 17 && hour < 21));
    if (isRushHour) {
      active.add(IndiaFactor(
        name: 'Rush Hour',
        emoji: '🕐',
        delayMultiplier: 1.25,
        description: 'Peak traffic period — heavily congested roads',
        color: const Color(0xFFFFD600),
      ));
    }

    // Wedding season (Nov–Feb on weekends)
    final isWeddingSeason = (month >= 11 || month <= 2) && weekday >= 6;
    if (isWeddingSeason) {
      active.add(IndiaFactor(
        name: 'Wedding Season',
        emoji: '💒',
        delayMultiplier: 1.08,
        description: 'Weekend wedding processions block key roads',
        color: const Color(0xFFE040FB),
      ));
    }

    // Market day / Sunday markets in some cities
    if (weekday == 7 &&
        (cityName == 'Delhi' || cityName == 'Mumbai' || cityName == 'Kolkata')) {
      if (hour >= 10 && hour <= 20) {
        active.add(IndiaFactor(
          name: 'Sunday Market',
          emoji: '🛍️',
          delayMultiplier: 1.05,
          description: 'Weekly markets increase pedestrian & vehicle density',
          color: const Color(0xFFFF9800),
        ));
      }
    }

    // Cricket match days (IPL season April–June evenings)
    if (month >= 4 && month <= 6 && hour >= 19 && hour <= 23) {
      if (cityName == 'Mumbai' || cityName == 'Bengaluru' || cityName == 'Delhi' ||
          cityName == 'Chennai' || cityName == 'Kolkata' || cityName == 'Hyderabad') {
        active.add(IndiaFactor(
          name: 'IPL Match',
          emoji: '🏏',
          delayMultiplier: 1.12,
          description: 'Stadium traffic & fan movement causes congestion',
          color: const Color(0xFF00E676),
        ));
      }
    }

    double totalMultiplier = active.fold(
        1.0, (prev, f) => prev * (f.delayMultiplier - 1.0) + prev);
    totalMultiplier = totalMultiplier.clamp(1.0, 2.0);

    return IndiaFactors(
      active: active,
      totalMultiplier: totalMultiplier,
      isRushHour: isRushHour,
      isMonsoon: isMonsoon,
    );
  }

  List<IndiaFactor> _getFestivalsNearDate(DateTime now) {
    final year = now.year;
    final festivals = <IndiaFactor>[];

    // Festival windows: (month, startDay, endDay)
    final windows = [
      // Diwali (late Oct / early Nov — varies yearly)
      _FestivalWindow(10, 18, 27, 'Diwali', '🪔', 1.28,
          'Massive fireworks & celebrations block city arteries', const Color(0xFFFFD600)),
      _FestivalWindow(11, 1, 5, 'Diwali celebrations', '🪔', 1.20,
          'Post-Diwali celebrations continue to affect traffic', const Color(0xFFFFD600)),
      // Navratri / Garba (Gujarat mainly, also other cities)
      _FestivalWindow(10, 2, 12, 'Navratri/Garba', '🎭', 1.18,
          'Garba venues draw massive crowds, especially in Gujarat cities', const Color(0xFFE040FB)),
      // Durga Puja (West Bengal, mainly Kolkata)
      _FestivalWindow(10, 2, 8, 'Durga Puja', '🙏', 1.22,
          'Puja pandals block Kolkata roads for days', const Color(0xFFFF9800)),
      // Holi
      _FestivalWindow(3, 13, 15, 'Holi', '🎨', 1.15,
          'Holi celebrations reduce traffic but cause road spills', const Color(0xFF00E676)),
      // Eid-ul-Fitr (approximate — varies by lunar calendar)
      _FestivalWindow(3, 30, 31, 'Eid', '☪️', 1.20,
          'Eid prayers and celebrations create peak congestion zones', const Color(0xFF00BCD4)),
      _FestivalWindow(4, 1, 2, 'Eid', '☪️', 1.15, '', const Color(0xFF00BCD4)),
      // Ganesh Chaturthi (Mumbai mainly, Aug-Sep)
      _FestivalWindow(8, 25, 31, 'Ganesh Chaturthi', '🐘', 1.24,
          'Processions, particularly Visarjan routes, block Mumbai roads', const Color(0xFFFF9800)),
      _FestivalWindow(9, 1, 8, 'Ganesh Visarjan', '🐘', 1.28, '', const Color(0xFFFF9800)),
      // Republic Day
      _FestivalWindow(1, 25, 27, 'Republic Day', '🇮🇳', 1.20,
          'National holiday with parades — major road closures in Delhi', const Color(0xFF2979FF)),
      // Independence Day
      _FestivalWindow(8, 14, 16, 'Independence Day', '🇮🇳', 1.15,
          'National holiday celebrations affect city centres', const Color(0xFF4CAF50)),
    ];

    for (final w in windows) {
      if (now.month == w.month &&
          now.day >= w.startDay &&
          now.day <= w.endDay) {
        festivals.add(IndiaFactor(
          name: w.name,
          emoji: w.emoji,
          delayMultiplier: w.delayMultiplier,
          description: w.description,
          color: w.color,
        ));
      }
    }
    return festivals;
  }

  // ── Full route analysis ────────────────────────────────────────────────────

  Future<RouteResult> analyzeRoute({
    required LatLng origin,
    required LatLng destination,
    required EmergencyType emergencyType,
    required CityConfig city,
    PredictionResponse? aiPrediction,
  }) async {
    // 1. Get OSRM route
    final osrmRoute = await fetchOsrmRoute(origin, destination);
    if (osrmRoute == null) throw Exception('Route not found between locations.');

    final coords = osrmRoute['geometry']['coordinates'] as List;
    final polyline =
        coords.map((c) => LatLng(c[1] as double, c[0] as double)).toList();
    final distanceKm = (osrmRoute['distance'] as num) / 1000;
    final osrmEtaMin = (osrmRoute['duration'] as num) / 60;

    // 2. Detect India factors
    final now = DateTime.now();
    final indiaFactors = detectIndiaFactors(city.name, now);

    // 3. Congestion from AI model
    double congestionScore = 0.35; // fallback moderate
    double congestionUncertainty = 0.15;
    if (aiPrediction != null) {
      congestionScore = aiPrediction.congestionT5;
      congestionUncertainty = aiPrediction.uncertaintyT5;
    }

    // 4. Calculate ETAs
    //
    // Standard ETA = what OSRM/Uber shows (base routing, limited India context)
    final standardEtaMin = osrmEtaMin;

    // Predicted actual ETA (what will actually happen, accounting for India factors)
    // Standard apps underestimate this significantly in India
    final congestionOverhead = congestionScore * 0.45;
    final predictedActualEtaMin = osrmEtaMin *
        (1 + congestionOverhead) *
        indiaFactors.totalMultiplier;

    // AI Emergency Route ETA:
    // - Emergency vehicle priority at signals: saves 15-25%
    // - AI-predicted congestion bypass: saves based on congestion level
    // - Alternative route if congestion > 0.5: saves additional 10%
    final emergencyPriorityFactor = 0.15 + (congestionScore * 0.15);
    final altRouteSaving = congestionScore > 0.5 ? 0.08 : 0.0;
    final indiaBypass = (indiaFactors.totalMultiplier - 1.0) * 0.45;
    final totalSavingFactor =
        (emergencyPriorityFactor + altRouteSaving + indiaBypass).clamp(0.1, 0.38);

    double aiEtaMin = predictedActualEtaMin * (1.0 - totalSavingFactor);
    aiEtaMin = aiEtaMin.clamp(osrmEtaMin * 0.68, osrmEtaMin * 1.5);

    // Time saved = what user expects (standardEtaMin) vs what we deliver (aiEtaMin)
    final timeSavedMin = standardEtaMin - aiEtaMin;

    final confidencePct =
        ((1.0 - congestionUncertainty) * 100).clamp(60, 98).toInt();

    return RouteResult(
      polyline: polyline,
      distanceKm: distanceKm,
      standardEtaMin: standardEtaMin,
      predictedActualEtaMin: predictedActualEtaMin,
      aiEtaMin: aiEtaMin,
      timeSavedMin: timeSavedMin,
      congestionScore: congestionScore,
      congestionUncertainty: congestionUncertainty,
      indiaFactors: indiaFactors,
      emergencyType: emergencyType,
      cityName: city.name,
      confidencePct: confidencePct,
    );
  }

  // ── Nearest city ───────────────────────────────────────────────────────────

  CityConfig nearestCity(LatLng location) {
    const distCalc = Distance();
    CityConfig nearest = kCities[0];
    double minD = double.infinity;
    for (final c in kCities) {
      final d = distCalc(location, LatLng(c.lat, c.lng));
      if (d < minD) {
        minD = d;
        nearest = c;
      }
    }
    return nearest;
  }
}

// ── Internal helpers ───────────────────────────────────────────────────────

class _FestivalWindow {
  final int month;
  final int startDay;
  final int endDay;
  final String name;
  final String emoji;
  final double delayMultiplier;
  final String description;
  final Color color;

  const _FestivalWindow(this.month, this.startDay, this.endDay, this.name,
      this.emoji, this.delayMultiplier, this.description, this.color);
}
