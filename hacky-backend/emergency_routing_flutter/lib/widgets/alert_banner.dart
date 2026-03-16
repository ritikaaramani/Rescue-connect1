import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../config/theme.dart';

class AlertBanner extends StatelessWidget {
  final double? score;
  const AlertBanner({super.key, this.score});

  @override
  Widget build(BuildContext context) {
    if (score == null) return const SizedBox.shrink();

    final color = getCongestionColor(score!);
    final msg = getCongestionMessage(score!);
    
    IconData iconData = Icons.check_circle_outline;
    if (score! >= 0.3) iconData = Icons.warning_amber_rounded;
    if (score! >= 0.6) iconData = Icons.error_outline;

    Widget banner = Container(
      color: color.withOpacity(0.15),
      padding: const EdgeInsets.all(12),
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        border: Border(left: BorderSide(color: color, width: 3)),
      ),
      child: Row(
        children: [
          Icon(iconData, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Text(msg, style: const TextStyle(color: kTextSecondary, fontSize: 13)),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(20)),
            child: Text(
              '${(score! * 100).toStringAsFixed(0)}%',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
            ),
          )
        ],
      ),
    ).animate().slideY(begin: -1, end: 0, duration: 300.ms, curve: Curves.easeOut);

    if (score! >= 0.6) {
      banner = banner.animate(onPlay: (c) => c.repeat()).shimmer(duration: 2000.ms, color: kDanger.withOpacity(0.3));
    }

    return banner;
  }
}
