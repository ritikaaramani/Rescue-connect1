import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../config/theme.dart';

class TrafficControlScreen extends StatelessWidget {
  const TrafficControlScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBackground,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('TRAFFIC CONTROL INTERFACE', style: GoogleFonts.rajdhani(fontWeight: FontWeight.bold, letterSpacing: 1.5)),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _buildSmartCityBanner(),
            const SizedBox(height: 20),
            Expanded(
              child: GridView.count(
                crossAxisCount: 2,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                childAspectRatio: 1.5,
                children: [
                  _buildControlCard(Icons.traffic, 'ACTIVATE GREEN CORRIDOR', 'Syncs all traffic lights to green for active critical missions.', Colors.green),
                  _buildControlCard(Icons.warning_amber, 'OVERRIDE SIGNAL #442', 'Manual override of Palasia intersection signal.', Colors.orange),
                  _buildControlCard(Icons.speaker_phone, 'BROADCAST ROAD ALERT', 'Sends "Emergency Vehicle Approaching" to local nav apps.', kAiCyan),
                  _buildControlCard(Icons.bar_chart, 'SUMO SIMULATION SYNC', 'Real-time sync with city digital twin.', Colors.purple),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSmartCityBanner() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(gradient: LinearGradient(colors: [Colors.green.withOpacity(0.2), kAiCyan.withOpacity(0.1)]), borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.green.withOpacity(0.5))),
      child: Row(
        children: [
          const Icon(Icons.hub, color: Colors.green, size: 30),
          const SizedBox(width: 12),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('INTELLIGENT TRAFFIC CONTROL ACTIVE', style: GoogleFonts.rajdhani(color: Colors.green, fontWeight: FontWeight.bold)),
              Text('Connected to 142 smart intersections in Indore. IoT latency: 12ms', style: GoogleFonts.rajdhani(color: Colors.white70, fontSize: 12)),
            ],
          )),
        ],
      ),
    );
  }

  Widget _buildControlCard(IconData icon, String title, String desc, Color color) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: color.withOpacity(0.05), borderRadius: BorderRadius.circular(16), border: Border.all(color: color.withOpacity(0.3))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 36),
          const SizedBox(height: 12),
          Text(title, style: GoogleFonts.rajdhani(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 8),
          Text(desc, style: GoogleFonts.rajdhani(color: Colors.white70, fontSize: 12)),
        ],
      ),
    );
  }
}
