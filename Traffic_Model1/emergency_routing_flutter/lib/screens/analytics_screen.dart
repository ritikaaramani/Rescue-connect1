import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../config/theme.dart';

class AnalyticsScreen extends StatelessWidget {
  const AnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBackground,
      appBar: AppBar(
        title: Text('OPERATIONAL ANALYTICS', style: GoogleFonts.rajdhani(fontWeight: FontWeight.bold, letterSpacing: 1.5)),
        backgroundColor: Colors.transparent,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildStatRow(),
          const SizedBox(height: 20),
          _buildInsightCard('AI ETA Accuracy', '94.2%', 'LSTM+GCN model confidence over last 48 hours.', kSuccess, Icons.check_circle_outline),
          const SizedBox(height: 12),
          _buildInsightCard('Time Saved', '14.5 min', 'Average reduction in response time using priority routing.', kAiCyan, Icons.timer),
          const SizedBox(height: 12),
          _buildInsightCard('Critical Response', '6.2 min', 'Average time from dispatch to arrival for CRITICAL requests.', kEmergencyOrange, Icons.warning_amber),
        ],
      ),
    );
  }

  Widget _buildStatRow() {
    return Row(
      children: [
        _buildStatBox('142', 'Missions Today', kAiCyan),
        const SizedBox(width: 12),
        _buildStatBox('8.4m', 'Avg Response', Colors.purpleAccent),
        const SizedBox(width: 12),
        _buildStatBox('94%', 'Survival Rate', kSuccess),
      ],
    );
  }

  Widget _buildStatBox(String val, String label, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: color.withOpacity(0.05), borderRadius: BorderRadius.circular(16), border: Border.all(color: color.withOpacity(0.2))),
        child: Column(
          children: [
            Text(val, style: GoogleFonts.rajdhani(fontSize: 26, fontWeight: FontWeight.bold, color: color)),
            const SizedBox(height: 4),
            Text(label, style: GoogleFonts.rajdhani(fontSize: 11, color: kTextSecondary)),
          ],
        ),
      ),
    );
  }

  Widget _buildInsightCard(String title, String value, String desc, Color color, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: kCardBg, borderRadius: BorderRadius.circular(16), border: Border.all(color: kCardBorder)),
      child: Row(
        children: [
          Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: color.withOpacity(0.1), shape: BoxShape.circle), child: Icon(icon, color: color, size: 32)),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: GoogleFonts.rajdhani(color: Colors.white70, fontSize: 14)),
                Text(value, style: GoogleFonts.rajdhani(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                Text(desc, style: GoogleFonts.rajdhani(color: Colors.grey[600], fontSize: 12)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
