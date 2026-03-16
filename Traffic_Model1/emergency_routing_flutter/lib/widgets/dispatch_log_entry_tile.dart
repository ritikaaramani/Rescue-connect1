import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/dispatch_log_entry.dart';
import '../config/theme.dart';

class DispatchLogEntryTile extends StatelessWidget {
  final DispatchLogEntry entry;
  const DispatchLogEntryTile({super.key, required this.entry});

  @override
  Widget build(BuildContext context) {
    final timeStr = DateFormat('HH:mm:ss').format(DateTime.parse(entry.timestamp));
    final color = getCongestionColor(entry.score);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border(left: BorderSide(color: color, width: 3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(entry.city, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
              const Spacer(),
              Text(timeStr, style: const TextStyle(color: kTextSecondary, fontSize: 11)),
            ],
          ),
          const SizedBox(height: 4),
          Text(entry.message, style: const TextStyle(color: kTextSecondary, fontSize: 13)),
          const SizedBox(height: 8),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(4)),
                child: Text('${(entry.score * 100).toStringAsFixed(1)}%', 
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11)),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: kCardBorder, borderRadius: BorderRadius.circular(4)),
                child: Text(entry.level.toUpperCase(), 
                  style: const TextStyle(color: kTextSecondary, fontSize: 11)),
              )
            ],
          )
        ],
      ),
    );
  }
}
