import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';
import '../config/theme.dart';
import '../services/unified_service.dart';
import '../services/backend_service.dart';

// Provider to fetch hospitals from backend API
final _hospitalsListProvider = FutureProvider<List<Hospital>>((ref) async {
  final backend = ref.read(backendServiceProvider);
  final data = await backend.getAllHospitals();
  
  return data.map((json) => Hospital(
    id: json['id'],
    name: json['name'],
    location: LatLng(json['lat'], json['lon']),
    icuBeds: json['icu_beds'],
    traumaSpecialty: json['trauma'],
    distanceKm: 0.0, // This can be calculated on frontend if needed
  )).toList();
});

class HospitalsScreen extends ConsumerWidget {
  const HospitalsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hospState = ref.watch(_hospitalsListProvider);

    return Scaffold(
      backgroundColor: kBackground,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('CITY HOSPITAL NETWORK', style: GoogleFonts.rajdhani(fontWeight: FontWeight.bold, letterSpacing: 1.5)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: kAiCyan),
            onPressed: () => ref.refresh(_hospitalsListProvider),
          )
        ],
      ),
      body: hospState.when(
        loading: () => const Center(child: CircularProgressIndicator(color: kAiCyan)),
        error: (e, st) => Center(child: Text('Failed to load: $e', style: const TextStyle(color: Colors.red))),
        data: (hospitals) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _buildSmartSuggestionBanner(),
            const SizedBox(height: 20),
            ...hospitals.map((h) => _buildHospitalCard(h)),
          ],
        ),
      ),
    );
  }

  Widget _buildSmartSuggestionBanner() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.05), borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.white24)),
      child: Row(
        children: [
          const Icon(Icons.auto_awesome, color: kEmergencyOrange, size: 28),
          const SizedBox(width: 12),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('SMART LOAD BALANCING', style: GoogleFonts.rajdhani(color: kEmergencyOrange, fontWeight: FontWeight.bold)),
              Text('Diverting non-critical trauma from MY Hospital to Bombay Hospital due to 95% ER capacity.', style: GoogleFonts.rajdhani(color: Colors.white70, fontSize: 12)),
            ],
          )),
        ],
      ),
    );
  }

  Widget _buildHospitalCard(Hospital h) {
    final capacityPct = h.icuBeds > 5 ? 0.4 : (h.icuBeds > 0 ? 0.75 : 1.0);
    final capacityColor = h.icuBeds == 0 ? Colors.red : (h.icuBeds < 3 ? Colors.orange : Colors.green);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: kCardBg, borderRadius: BorderRadius.circular(12), border: Border.all(color: capacityColor.withOpacity(0.3))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(h.traumaSpecialty ? Icons.health_and_safety : Icons.local_hospital, color: capacityColor, size: 24),
              const SizedBox(width: 12),
              Expanded(child: Text(h.name, style: GoogleFonts.rajdhani(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold))),
              Text('${h.distanceKm} km', style: GoogleFonts.rajdhani(color: kTextSecondary, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('ICU Beds: ${h.icuBeds}', style: GoogleFonts.rajdhani(color: Colors.white70, fontSize: 14)),
              if (h.traumaSpecialty)
                Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2), decoration: BoxDecoration(color: Colors.purple.withOpacity(0.2), borderRadius: BorderRadius.circular(4)), child: Text('TRAUMA CENTER', style: TextStyle(color: Colors.purple[200], fontSize: 10, fontWeight: FontWeight.bold))),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: capacityPct,
              backgroundColor: Colors.white10,
              valueColor: AlwaysStoppedAnimation(capacityColor),
              minHeight: 6,
            ),
          ),
          const SizedBox(height: 4),
          Text('ER Load: ${(capacityPct * 100).toInt()}%', style: GoogleFonts.rajdhani(color: kTextSecondary, fontSize: 11)),
        ],
      ),
    );
  }
}
