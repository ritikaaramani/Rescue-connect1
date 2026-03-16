import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import '../config/theme.dart';
import '../config/api_config.dart';
import '../providers/health_provider.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final health = ref.watch(healthStateProvider);
    final modelInfo = ref.watch(modelInfoStateProvider);

    return Scaffold(
      backgroundColor: kBackground,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              const SizedBox(height: 8),
              Row(children: [
                const Icon(Icons.emergency_share,
                    color: kEmergencyOrange, size: 22),
                const SizedBox(width: 10),
                Text('SWIFT EMERGENCY',
                    style: GoogleFonts.rajdhani(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 2)),
              ]),
              const SizedBox(height: 4),
              Text('Settings & System Info',
                  style: GoogleFonts.rajdhani(
                      color: kTextSecondary, fontSize: 13)),

              const SizedBox(height: 28),

              // AI Model status
              _SectionHeader('AI MODEL'),
              _InfoCard(children: [
                _InfoRow(
                  icon: Icons.psychology,
                  iconColor: kAiCyan,
                  label: 'Model',
                  value: 'LSTM + GCN (Spatiotemporal)',
                ),
                const _RowDivider(),
                _InfoRow(
                  icon: Icons.circle,
                  iconColor: health?.status == 'ok' ? kSuccess : kDanger,
                  label: 'Status',
                  value: health?.status == 'ok' ? 'Online' : 'Offline',
                  valueColor: health?.status == 'ok' ? kSuccess : kDanger,
                ),
                const _RowDivider(),
                _InfoRow(
                  icon: Icons.memory,
                  iconColor: kAiCyan,
                  label: 'Parameters',
                  value: modelInfo != null
                      ? _formatParams(modelInfo.parameterCount)
                      : 'N/A',
                ),
                const _RowDivider(),
                _InfoRow(
                  icon: Icons.layers,
                  iconColor: kAiCyan,
                  label: 'LSTM Hidden',
                  value: modelInfo != null ? '${modelInfo.lstmHiddenSize}' : 'N/A',
                ),
                const _RowDivider(),
                _InfoRow(
                  icon: Icons.hub,
                  iconColor: kAiCyan,
                  label: 'GCN Hidden',
                  value: modelInfo != null ? '${modelInfo.gcnHiddenDim}' : 'N/A',
                ),
                const _RowDivider(),
                _InfoRow(
                  icon: Icons.timer,
                  iconColor: kAiCyan,
                  label: 'Horizons',
                  value: 'T+5, T+10, T+20, T+30 min',
                ),
              ]),

              const SizedBox(height: 20),

              _SectionHeader('API'),
              _InfoCard(children: [
                _InfoRow(
                  icon: Icons.cloud,
                  iconColor: kAccent,
                  label: 'Base URL',
                  value: kApiBaseUrl,
                ),
                const _RowDivider(),
                _InfoRow(
                  icon: Icons.access_time,
                  iconColor: kAccent,
                  label: 'Uptime',
                  value: health != null
                      ? _formatUptime(health.uptimeSeconds)
                      : 'N/A',
                ),
                const _RowDivider(),
                _InfoRow(
                  icon: Icons.location_city,
                  iconColor: kAccent,
                  label: 'Trained Cities',
                  value: health?.citiesAvailable.join(', ') ?? 'N/A',
                ),
              ]),

              const SizedBox(height: 20),

              _SectionHeader('INDIA INTELLIGENCE'),
              _InfoCard(children: [
                const _FeatureRow('🪔', 'Festival Calendar',
                    'Diwali, Navratri, Eid, Holi, Durga Puja, Ganesh Chaturthi'),
                const _RowDivider(),
                const _FeatureRow('🌧️', 'Monsoon Detection',
                    'June–September rain impact modeling'),
                const _RowDivider(),
                const _FeatureRow('🕐', 'Rush Hour Engine',
                    '7–10 AM & 5–9 PM weekday peak traffic'),
                const _RowDivider(),
                const _FeatureRow('💒', 'Wedding Season',
                    'Nov–Feb weekend procession routing'),
                const _RowDivider(),
                const _FeatureRow('🏏', 'IPL/Cricket Events',
                    'Stadium traffic pattern recognition'),
                const _RowDivider(),
                const _FeatureRow('🛣️', 'Road Quality',
                    'OSM road class weights for Indian infrastructure'),
              ]),

              const SizedBox(height: 20),

              _SectionHeader('ROUTING'),
              _InfoCard(children: [
                const _FeatureRow('🗺️', 'Base Routing',
                    'OSRM (Open Source Routing Machine)'),
                const _RowDivider(),
                const _FeatureRow('📍', 'Geocoding', 'Nominatim / OpenStreetMap'),
                const _RowDivider(),
                const _FeatureRow('⚡', 'AI ETA Adjustment',
                    'Congestion + India factors + emergency priority'),
                const _RowDivider(),
                const _FeatureRow('🚨', 'Emergency Priority',
                    '10–25% time savings via priority routing'),
              ]),

              const SizedBox(height: 20),

              GestureDetector(
                onTap: () {
                  ref.read(healthStateProvider.notifier).fetch();
                  ref.read(modelInfoStateProvider.notifier).fetch();
                },
                child: Container(
                  height: 50,
                  decoration: BoxDecoration(
                    color: kAccent.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: kAccent.withOpacity(0.35)),
                  ),
                  child: Center(
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.refresh, color: kAccent, size: 18),
                      const SizedBox(width: 8),
                      Text('REFRESH MODEL STATUS',
                          style: GoogleFonts.rajdhani(
                              color: kAccent,
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 1)),
                    ]),
                  ),
                ),
              ),

              const SizedBox(height: 16),

              Center(
                child: Text('Swift Emergency v1.0 · LSTM+GCN AI Model',
                    style: GoogleFonts.rajdhani(
                        color: Colors.grey[800], fontSize: 11)),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }

  String _formatParams(int count) {
    if (count >= 1000000) return '${(count / 1000000).toStringAsFixed(1)}M';
    if (count >= 1000) return '${(count / 1000).toStringAsFixed(0)}K';
    return '$count';
  }

  String _formatUptime(double seconds) {
    final h = (seconds / 3600).floor();
    final m = ((seconds % 3600) / 60).floor();
    return '${h}h ${m}m';
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Text(title,
          style: GoogleFonts.rajdhani(
              color: kTextSecondary,
              fontSize: 11,
              fontWeight: FontWeight.bold,
              letterSpacing: 1.5)),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final List<Widget> children;
  const _InfoCard({required this.children});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kCardBorder),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Column(children: children),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String label;
  final String value;
  final Color? valueColor;

  const _InfoRow({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.value,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 13),
      child: Row(children: [
        Icon(icon, color: iconColor, size: 16),
        const SizedBox(width: 12),
        Text(label,
            style: GoogleFonts.rajdhani(color: kTextSecondary, fontSize: 14)),
        const Spacer(),
        Flexible(
          child: Text(value,
              textAlign: TextAlign.right,
              style: GoogleFonts.rajdhani(
                  color: valueColor ?? Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w600)),
        ),
      ]),
    );
  }
}

class _FeatureRow extends StatelessWidget {
  final String emoji;
  final String title;
  final String description;

  const _FeatureRow(this.emoji, this.title, this.description);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(emoji, style: const TextStyle(fontSize: 16)),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title,
                style: GoogleFonts.rajdhani(
                    color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600)),
            Text(description,
                style: GoogleFonts.rajdhani(
                    color: kTextSecondary, fontSize: 12)),
          ]),
        ),
      ]),
    );
  }
}

class _RowDivider extends StatelessWidget {
  const _RowDivider();

  @override
  Widget build(BuildContext context) {
    return const Divider(height: 1, color: Color(0xFF1A1A1A));
  }
}
