import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../config/theme.dart';
import '../models/route_model.dart';
import '../providers/dispatch_provider.dart';
import '../widgets/dispatch_log_entry_tile.dart';

// Provider for active dispatches (simulated)
final _activeDispatchesProvider =
    StateProvider<List<ActiveDispatch>>((ref) => []);

class DispatchScreen extends ConsumerWidget {
  const DispatchScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final log = ref.watch(dispatchLogProvider);
    final active = ref.watch(_activeDispatchesProvider);

    return Scaffold(
      backgroundColor: kBackground,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: Row(children: [
                const Icon(Icons.local_fire_department,
                    color: kEmergencyOrange, size: 22),
                const SizedBox(width: 10),
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('DISPATCH CENTER',
                      style: GoogleFonts.rajdhani(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 1.5)),
                  Text('Live emergency unit tracking',
                      style: GoogleFonts.rajdhani(
                          color: kTextSecondary, fontSize: 12)),
                ]),
                const Spacer(),
                // Active count badge
                if (active.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: kDanger.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: kDanger.withOpacity(0.4)),
                    ),
                    child: Text('${active.length} ACTIVE',
                        style: GoogleFonts.rajdhani(
                            color: kDanger,
                            fontSize: 11,
                            fontWeight: FontWeight.bold)),
                  ),
              ]),
            ),

            const SizedBox(height: 16),

            // Active dispatches section
            if (active.isNotEmpty) ...[
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Text('ACTIVE UNITS',
                    style: GoogleFonts.rajdhani(
                        color: kTextSecondary,
                        fontSize: 10,
                        letterSpacing: 1.5,
                        fontWeight: FontWeight.bold)),
              ),
              const SizedBox(height: 8),
              ...active.map((d) => _ActiveDispatchCard(dispatch: d)),
              const SizedBox(height: 16),
            ],

            // Log header
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Row(children: [
                Text('DISPATCH LOG',
                    style: GoogleFonts.rajdhani(
                        color: kTextSecondary,
                        fontSize: 10,
                        letterSpacing: 1.5,
                        fontWeight: FontWeight.bold)),
                const Spacer(),
                if (log.isNotEmpty)
                  GestureDetector(
                    onTap: () =>
                        ref.read(dispatchLogProvider.notifier).clear(),
                    child: Text('Clear',
                        style: GoogleFonts.rajdhani(
                            color: kDanger.withOpacity(0.7), fontSize: 12)),
                  ),
              ]),
            ),

            const SizedBox(height: 8),

            // Log list
            Expanded(
              child: log.isEmpty
                  ? _buildEmptyState()
                  : ListView.separated(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 4),
                      itemCount: log.length,
                      separatorBuilder: (_, __) =>
                          const SizedBox(height: 6),
                      itemBuilder: (ctx, i) {
                        final entry = log[i];
                        return DispatchLogEntryTile(entry: entry)
                            .animate()
                            .fadeIn(
                                duration: 250.ms,
                                delay: Duration(milliseconds: i * 40))
                            .slideX(begin: 0.05, end: 0);
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.local_shipping_outlined,
              color: Colors.grey[800], size: 56),
          const SizedBox(height: 16),
          Text('No dispatches yet',
              style: GoogleFonts.rajdhani(
                  color: kTextSecondary, fontSize: 16)),
          const SizedBox(height: 6),
          Text('Route an emergency from the Map tab',
              style: GoogleFonts.rajdhani(
                  color: Colors.grey[800], fontSize: 13)),
        ],
      ),
    );
  }
}

// ── Active dispatch card ───────────────────────────────────────────────────

class _ActiveDispatchCard extends StatefulWidget {
  final ActiveDispatch dispatch;
  const _ActiveDispatchCard({required this.dispatch});

  @override
  State<_ActiveDispatchCard> createState() => _ActiveDispatchCardState();
}

class _ActiveDispatchCardState extends State<_ActiveDispatchCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulse;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
        vsync: this, duration: const Duration(seconds: 2))
      ..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.dispatch;
    final type = d.type;
    final remaining = d.remainingMin;
    final progress =
        (1.0 - remaining / d.etaMin).clamp(0.0, 1.0);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: AnimatedBuilder(
        animation: _pulse,
        builder: (_, __) => Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: type.color.withOpacity(0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
                color: type.color
                    .withOpacity(0.3 + 0.2 * _pulse.value)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                // Pulsing dot
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    color: type.color,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                          color: type.color
                              .withOpacity(0.5 + 0.4 * _pulse.value),
                          blurRadius: 10)
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Text(type.label.toUpperCase(),
                    style: GoogleFonts.rajdhani(
                        color: type.color,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1)),
                const Spacer(),
                Text(
                  remaining <= 0.5
                      ? 'ARRIVING'
                      : '${remaining.toStringAsFixed(0)} min remaining',
                  style: GoogleFonts.rajdhani(
                    color: remaining <= 1
                        ? kSuccess
                        : Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ]),

              const SizedBox(height: 8),

              // Route
              Text(
                '${d.origin} → ${d.destination}',
                style: GoogleFonts.rajdhani(
                    color: kTextSecondary, fontSize: 12),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),

              const SizedBox(height: 10),

              // Progress bar
              ClipRRect(
                borderRadius: BorderRadius.circular(3),
                child: LinearProgressIndicator(
                  value: progress,
                  backgroundColor: Colors.grey[900],
                  valueColor: AlwaysStoppedAnimation(type.color),
                  minHeight: 4,
                ),
              ),

              const SizedBox(height: 6),

              Text(
                'Dispatched ${DateFormat('hh:mm a').format(d.dispatchedAt)} · ${d.cityName}',
                style: GoogleFonts.rajdhani(
                    color: Colors.grey[700], fontSize: 10),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
