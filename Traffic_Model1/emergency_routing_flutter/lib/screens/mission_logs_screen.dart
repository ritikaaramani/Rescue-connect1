import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../config/theme.dart';

class MissionLogsScreen extends StatelessWidget {
  const MissionLogsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBackground,
      appBar: AppBar(
        title: Text('HISTORICAL MISSION LOGS', style: GoogleFonts.rajdhani(fontWeight: FontWeight.bold, letterSpacing: 1.5)),
        backgroundColor: Colors.transparent,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildMissionLogEntry('DSP-1092', 'Heart Attack', 'CHL Hospital', 'Completed', '14.2 min ETA | Arrived 13.8 min', kSuccess),
          _buildMissionLogEntry('DSP-1091', 'Traffic Accident', 'Apollo Hospital', 'Completed', '19.0 min ETA | Arrived 19.5 min', kSuccess),
          _buildMissionLogEntry('DSP-1090', 'Fire Emergency', 'MY Hospital', 'Failed - Rerouted', 'Ambulance broke down. Reassigned to UP-14-342.', kDanger),
          _buildMissionLogEntry('DSP-1089', 'Stroke', 'Medanta', 'Completed', '8.5 min ETA | Arrived 8.1 min', kSuccess),
          _buildMissionLogEntry('DSP-1088', 'Childbirth', 'Bombay Hospital', 'Completed', '11.0 min ETA | Arrived 11.0 min', kSuccess),
        ],
      ),
    );
  }

  Widget _buildMissionLogEntry(String id, String type, String dest, String status, String details, Color statusColor) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: kCardBg, borderRadius: BorderRadius.circular(12), border: Border.all(color: kCardBorder)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('$id • $type', style: GoogleFonts.rajdhani(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white)),
              Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4), decoration: BoxDecoration(color: statusColor.withOpacity(0.1), borderRadius: BorderRadius.circular(4)), child: Text(status, style: TextStyle(color: statusColor, fontSize: 12, fontWeight: FontWeight.bold))),
            ],
          ),
          const SizedBox(height: 8),
          Text('Destination: $dest', style: GoogleFonts.rajdhani(color: Colors.white70, fontSize: 14)),
          Text(details, style: GoogleFonts.rajdhani(color: Colors.grey, fontSize: 13)),
          const SizedBox(height: 12),
          Row(
            children: [
              OutlinedButton.icon(onPressed: () {}, icon: const Icon(Icons.play_circle_outline, size: 16, color: kAiCyan), label: Text('REPLAY ROUTE', style: GoogleFonts.rajdhani(color: kAiCyan, fontWeight: FontWeight.bold)), style: OutlinedButton.styleFrom(side: const BorderSide(color: kAiCyan))),
              const SizedBox(width: 8),
              OutlinedButton.icon(onPressed: () {}, icon: const Icon(Icons.picture_as_pdf, size: 16, color: Colors.orange), label: Text('DOWNLOAD REPORT', style: GoogleFonts.rajdhani(color: Colors.orange, fontWeight: FontWeight.bold)), style: OutlinedButton.styleFrom(side: const BorderSide(color: Colors.orange))),
            ],
          ),
        ],
      ),
    );
  }
}
