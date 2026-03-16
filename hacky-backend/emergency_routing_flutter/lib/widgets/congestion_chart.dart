import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../models/prediction_response.dart';
import '../config/theme.dart';

class CongestionChart extends StatelessWidget {
  final PredictionResponse prediction;
  const CongestionChart(this.prediction, {super.key});

  @override
  Widget build(BuildContext context) {
    final color = getCongestionColor(prediction.congestionT5);
    
    return Container(
      height: 180,
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          const Text('Congestion Forecast', style: TextStyle(color: kTextSecondary, fontSize: 12)),
          const SizedBox(height: 16),
          Expanded(
            child: LineChart(
              LineChartData(
                minY: 0,
                maxY: 1.0,
                gridData: const FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: 0.25,
                ),
                borderData: FlBorderData(show: false),
                titlesData: FlTitlesData(
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 22,
                      getTitlesWidget: (val, meta) {
                        const labels = ['T+5', 'T+10', 'T+20', 'T+30'];
                        if (val.toInt() >= 0 && val.toInt() < labels.length) {
                          return Text(labels[val.toInt()], style: const TextStyle(color: kTextSecondary, fontSize: 10));
                        }
                        return const SizedBox.shrink();
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 30,
                      interval: 0.25,
                      getTitlesWidget: (val, meta) => Text(val.toStringAsFixed(2), style: const TextStyle(color: kTextSecondary, fontSize: 10)),
                    )
                  )
                ),
                lineBarsData: [
                  LineChartBarData(
                    spots: [
                      FlSpot(0, prediction.congestionT5),
                      FlSpot(1, prediction.congestionT10),
                      FlSpot(2, prediction.congestionT20),
                      FlSpot(3, prediction.congestionT30),
                    ],
                    color: color,
                    barWidth: 2.5,
                    isCurved: true,
                    dotData: const FlDotData(show: true),
                    belowBarData: BarAreaData(
                      show: true,
                      color: color.withOpacity(0.15),
                    ),
                  ),
                  LineChartBarData(
                    spots: [
                      FlSpot(0, (prediction.congestionT5 + prediction.uncertaintyT5).clamp(0.0, 1.0)),
                      FlSpot(1, (prediction.congestionT10 + prediction.uncertaintyT10).clamp(0.0, 1.0)),
                      FlSpot(2, (prediction.congestionT20 + prediction.uncertaintyT20).clamp(0.0, 1.0)),
                      FlSpot(3, (prediction.congestionT30 + prediction.uncertaintyT30).clamp(0.0, 1.0)),
                    ],
                    color: color.withOpacity(0.4),
                    barWidth: 1,
                    isCurved: true,
                    dashArray: [4, 4],
                    dotData: const FlDotData(show: false),
                  )
                ]
              )
            ),
          ),
        ],
      ),
    );
  }
}
