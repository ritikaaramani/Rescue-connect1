import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/prediction_response.dart';
import '../config/theme.dart';
import 'status_badge.dart';

class CongestionCard extends StatelessWidget {
  final PredictionResponse prediction;
  final bool isSelected;

  const CongestionCard(this.prediction, {super.key, this.isSelected = false});

  @override
  Widget build(BuildContext context) {
    final t5 = prediction.congestionT5;
    
    List<Color> gradientColors;
    if (t5 < 0.3) {
      gradientColors = [const Color(0xFF0A2E1A), const Color(0xFF0D3D22)];
    } else if (t5 < 0.6) {
      gradientColors = [const Color(0xFF2E1A00), const Color(0xFF3D2A00)];
    } else {
      gradientColors = [const Color(0xFF2E0A0A), const Color(0xFF3D1010)];
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: gradientColors),
        border: Border.all(color: getCongestionColor(t5).withOpacity(0.5), width: 1.5),
        borderRadius: BorderRadius.circular(16),
        boxShadow: isSelected 
          ? [BoxShadow(color: kAccent.withOpacity(0.3), blurRadius: 8)] 
          : null,
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(prediction.city, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
              StatusBadge(score: t5),
            ],
          ),
          const SizedBox(height: 16),
          Text('${(t5 * 100).toStringAsFixed(1)}%', style: TextStyle(fontSize: 44, fontWeight: FontWeight.bold, color: getCongestionColor(t5))),
          const Text('T+5 Congestion', style: TextStyle(color: kTextSecondary, fontSize: 12)),
          const SizedBox(height: 16),
          const Divider(color: kCardBorder),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildHorizonCol('T+10', prediction.congestionT10),
              _buildHorizonCol('T+20', prediction.congestionT20),
              _buildHorizonCol('T+30', prediction.congestionT30),
            ],
          ),
          const Divider(color: kCardBorder),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              Chip(
                label: Text('⚡ ${formatLatency(prediction.latencyMs)}'),
                backgroundColor: kAccentDim,
                side: BorderSide.none,
              ),
              Chip(
                label: Text('± ${prediction.uncertaintyT5.toStringAsFixed(2)}'),
                backgroundColor: kCardBorder,
                side: BorderSide.none,
              ),
            ],
          )
        ],
      ),
    ).animate().fadeIn().slideY(begin: 0.2, end: 0);
  }

  Widget _buildHorizonCol(String label, double val) {
    return Column(
      children: [
        Text(label, style: const TextStyle(color: Colors.grey, fontSize: 11)),
        Text('${(val * 100).toStringAsFixed(1)}%', style: TextStyle(color: getCongestionColor(val), fontSize: 16, fontWeight: FontWeight.bold)),
      ],
    );
  }
}
