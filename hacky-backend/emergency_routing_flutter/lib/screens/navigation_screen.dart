import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';

import '../config/theme.dart';
import '../models/route_model.dart';

// ── Navigation Screen — active emergency routing ───────────────────────────

class NavigationScreen extends StatefulWidget {
  final RouteResult route;
  final String origin;
  final String destination;

  const NavigationScreen({
    super.key,
    required this.route,
    required this.origin,
    required this.destination,
  });

  @override
  State<NavigationScreen> createState() => _NavigationScreenState();
}

class _NavigationScreenState extends State<NavigationScreen>
    with TickerProviderStateMixin {
  final _mapCtrl = MapController();

  // Simulated progress along route
  double _progress = 0.0;
  double _elapsedMin = 0.0;
  bool _isArrived = false;

  late AnimationController _pulseCtrl;
  late AnimationController _sirenCtrl;
  Timer? _progressTimer;

  // Turn-by-turn simulation
  final _turns = [
    'Head north on current road',
    'Turn right at the junction',
    'Continue straight for 2.1 km',
    'Turn left onto Main Highway',
    'Continue for 1.5 km',
    'Take the ramp onto Ring Road',
    'Exit at Junction 14',
    'Arriving at destination',
  ];
  int _turnIndex = 0;

  @override
  void initState() {
    super.initState();
    HapticFeedback.vibrate();

    _pulseCtrl = AnimationController(
        vsync: this, duration: const Duration(seconds: 2))
      ..repeat(reverse: true);
    _sirenCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 600))
      ..repeat(reverse: true);

    // Simulate vehicle movement along route
    _startSimulation();
  }

  void _startSimulation() {
    const interval = Duration(seconds: 3);
    final totalSteps =
        (widget.route.aiEtaMin * 60 / interval.inSeconds).ceil();
    final progressPerStep = 1.0 / totalSteps;
    final minutesPerStep = widget.route.aiEtaMin / totalSteps;
    final turnEvery = totalSteps ~/ (_turns.length - 1);

    _progressTimer = Timer.periodic(interval, (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        _progress = (_progress + progressPerStep).clamp(0.0, 1.0);
        _elapsedMin += minutesPerStep;

        // Advance turn instruction
        final newTurnIdx =
            (_progress * (_turns.length - 1)).floor().clamp(0, _turns.length - 1);
        _turnIndex = newTurnIdx;

        if (_progress >= 1.0) {
          _isArrived = true;
          timer.cancel();
          HapticFeedback.heavyImpact();
        }
      });

      // Move map with vehicle
      final vehiclePos = _vehiclePosition;
      _mapCtrl.move(vehiclePos, 14.5);
    });
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    _sirenCtrl.dispose();
    _progressTimer?.cancel();
    super.dispose();
  }

  LatLng get _vehiclePosition {
    final pts = widget.route.polyline;
    if (pts.isEmpty) return const LatLng(28.6139, 77.2090);
    final idx = ((_progress) * (pts.length - 1)).floor().clamp(0, pts.length - 1);
    return pts[idx];
  }

  double get _remainingMin =>
      (widget.route.aiEtaMin - _elapsedMin).clamp(0, widget.route.aiEtaMin);

  double get _remainingKm =>
      widget.route.distanceKm * (1.0 - _progress);

  // ── BUILD ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final r = widget.route;
    final type = r.emergencyType;

    if (_isArrived) return _buildArrivedScreen(type);

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(children: [
        // Map
        _buildNavigationMap(r, type),

        // Siren bar at top
        _buildSirenBar(type),

        // Turn instruction
        Positioned(
          top: 90,
          left: 0,
          right: 0,
          child: _buildTurnInstruction(type),
        ),

        // Bottom panel
        Positioned(
          bottom: 0,
          left: 0,
          right: 0,
          child: _buildBottomPanel(r, type),
        ),
      ]),
    );
  }

  // ── Navigation map ─────────────────────────────────────────────────────────

  Widget _buildNavigationMap(RouteResult r, EmergencyType type) {
    final polyline = r.polyline;
    final vehicle = _vehiclePosition;

    // Completed portion
    final completedIdx =
        ((_progress) * (polyline.length - 1)).floor().clamp(0, polyline.length - 1);
    final completed = polyline.take(completedIdx + 1).toList();
    final remaining = completedIdx < polyline.length - 1
        ? polyline.skip(completedIdx).toList()
        : <LatLng>[];

    return FlutterMap(
      mapController: _mapCtrl,
      options: MapOptions(
        initialCenter: vehicle,
        initialZoom: 15.0,
        interactionOptions:
            const InteractionOptions(flags: InteractiveFlag.all),
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.swiftemergency.app',
          tileBuilder: (ctx, widget, tile) => ColorFiltered(
            colorFilter: const ColorFilter.matrix([
              -1, 0, 0, 0, 255,
              0, -1, 0, 0, 255,
              0, 0, -1, 0, 255,
              0, 0, 0, 1, 0,
            ]),
            child: widget,
          ),
        ),

        // Remaining route glow
        if (remaining.isNotEmpty)
          PolylineLayer(polylines: [
            Polyline(
              points: remaining,
              strokeWidth: 16,
              color: type.color.withOpacity(0.15),
            ),
          ]),

        // Remaining route line
        if (remaining.isNotEmpty)
          PolylineLayer(polylines: [
            Polyline(
              points: remaining,
              strokeWidth: 5,
              color: type.color,
              strokeCap: StrokeCap.round,
            ),
          ]),

        // Completed route (dimmed)
        if (completed.isNotEmpty)
          PolylineLayer(polylines: [
            Polyline(
              points: completed,
              strokeWidth: 3,
              color: Colors.grey[700]!,
              strokeCap: StrokeCap.round,
            ),
          ]),

        // Destination marker
        if (r.polyline.isNotEmpty)
          MarkerLayer(markers: [
            Marker(
              point: r.polyline.last,
              width: 44,
              height: 44,
              child: Container(
                decoration: BoxDecoration(
                  color: type.color,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                        color: type.color.withOpacity(0.6), blurRadius: 16)
                  ],
                ),
                child:
                    Icon(type.icon, color: Colors.white, size: 22),
              ),
            ),
          ]),

        // Animated vehicle
        MarkerLayer(markers: [
          Marker(
            point: vehicle,
            width: 48,
            height: 48,
            child: _buildVehicleMarker(type),
          ),
        ]),
      ],
    );
  }

  Widget _buildVehicleMarker(EmergencyType type) {
    return AnimatedBuilder(
      animation: _sirenCtrl,
      builder: (_, __) {
        final glow = 0.4 + 0.6 * _sirenCtrl.value;
        return Container(
          decoration: BoxDecoration(
            color: Colors.white,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: type.color.withOpacity(glow),
                blurRadius: 22,
                spreadRadius: 6,
              ),
            ],
          ),
          child: Icon(type.icon, color: type.color, size: 24),
        );
      },
    );
  }

  // ── Siren bar ──────────────────────────────────────────────────────────────

  Widget _buildSirenBar(EmergencyType type) {
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: SafeArea(
        child: AnimatedBuilder(
          animation: _sirenCtrl,
          builder: (_, __) {
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: type.color
                    .withOpacity(0.8 + 0.2 * _sirenCtrl.value),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [
                  BoxShadow(
                    color: type.color
                        .withOpacity(0.4 + 0.3 * _sirenCtrl.value),
                    blurRadius: 20,
                  )
                ],
              ),
              child: Row(children: [
                Icon(type.icon, color: Colors.white, size: 18),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    '${type.label.toUpperCase()} EN ROUTE — PRIORITY ACTIVE',
                    style: GoogleFonts.rajdhani(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1),
                  ),
                ),
                GestureDetector(
                  onTap: () => Navigator.of(context).pop(),
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Icon(Icons.close,
                        color: Colors.white, size: 14),
                  ),
                ),
              ]),
            );
          },
        ),
      ),
    );
  }

  // ── Turn instruction ───────────────────────────────────────────────────────

  Widget _buildTurnInstruction(EmergencyType type) {
    final turn = _turns[_turnIndex];
    final isLeft = turn.contains('left');
    final isRight = turn.contains('right');
    final icon = isLeft
        ? Icons.turn_left
        : isRight
            ? Icons.turn_right
            : Icons.straight;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: const Color(0xF00D0D0D),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: kCardBorder),
        ),
        child: Row(children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: type.color.withOpacity(0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: type.color, size: 28),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(turn,
                      style: GoogleFonts.rajdhani(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w700)),
                  Text(
                    '${((_remainingKm * 0.4)).toStringAsFixed(1)} km',
                    style: GoogleFonts.rajdhani(
                        color: kTextSecondary, fontSize: 13),
                  ),
                ]),
          ),
        ]),
      ).animate().slideX(begin: -0.05, end: 0, duration: 300.ms).fadeIn(),
    );
  }

  // ── Bottom panel ───────────────────────────────────────────────────────────

  Widget _buildBottomPanel(RouteResult r, EmergencyType type) {
    final progress = _progress.clamp(0.0, 1.0);

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0C0C0C),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border.all(color: kCardBorder),
      ),
      padding: EdgeInsets.fromLTRB(
          20, 16, 20, MediaQuery.of(context).padding.bottom + 16),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        // Progress bar
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: progress,
            backgroundColor: Colors.grey[900],
            valueColor: AlwaysStoppedAnimation(type.color),
            minHeight: 6,
          ),
        ),

        const SizedBox(height: 16),

        // Stats row
        Row(children: [
          // ETA
          Expanded(
            child: _StatBlock(
              label: 'ETA',
              value: '${_remainingMin.toStringAsFixed(0)} min',
              sublabel: 'remaining',
              color: type.color,
            ),
          ),
          Container(width: 1, height: 40, color: kCardBorder),
          // Distance
          Expanded(
            child: _StatBlock(
              label: 'Distance',
              value: '${_remainingKm.toStringAsFixed(1)} km',
              sublabel: 'remaining',
              color: Colors.white,
            ),
          ),
          Container(width: 1, height: 40, color: kCardBorder),
          // Speed
          Expanded(
            child: _StatBlock(
              label: 'Priority',
              value: 'ACTIVE',
              sublabel: type.label,
              color: kSuccess,
            ),
          ),
        ]),

        const SizedBox(height: 16),

        // Route info
        Row(children: [
          const Icon(Icons.location_on, color: kTextSecondary, size: 13),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              '${widget.origin} → ${widget.destination}',
              style: GoogleFonts.rajdhani(
                  color: kTextSecondary, fontSize: 12),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ]),

        const SizedBox(height: 12),

        // AI model indicator
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          decoration: BoxDecoration(
            color: kAiCyan.withOpacity(0.06),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: kAiCyan.withOpacity(0.2)),
          ),
          child: Row(children: [
            AnimatedBuilder(
              animation: _pulseCtrl,
              builder: (_, __) => Container(
                width: 6,
                height: 6,
                decoration: BoxDecoration(
                  color: kAiCyan,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                        color: kAiCyan.withOpacity(0.4 + 0.4 * _pulseCtrl.value),
                        blurRadius: 6)
                  ],
                ),
              ),
            ),
            const SizedBox(width: 8),
            Text('LSTM+GCN AI actively monitoring route conditions',
                style: GoogleFonts.rajdhani(
                    color: kAiCyan, fontSize: 11, letterSpacing: 0.3)),
          ]),
        ),
      ]),
    );
  }

  // ── Arrived screen ─────────────────────────────────────────────────────────

  Widget _buildArrivedScreen(EmergencyType type) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Arrival icon
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: kSuccess.withOpacity(0.1),
                  border: Border.all(color: kSuccess, width: 2),
                ),
                child: const Icon(Icons.check_circle,
                    color: kSuccess, size: 56),
              )
                  .animate()
                  .scale(begin: const Offset(0.5, 0.5), duration: 500.ms,
                      curve: Curves.elasticOut),

              const SizedBox(height: 28),

              Text('ARRIVED',
                  style: GoogleFonts.rajdhani(
                      color: Colors.white,
                      fontSize: 36,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 4))
                  .animate()
                  .fadeIn(delay: 300.ms, duration: 400.ms),

              const SizedBox(height: 8),

              Text(widget.destination,
                  textAlign: TextAlign.center,
                  style: GoogleFonts.rajdhani(
                      color: kTextSecondary, fontSize: 16))
                  .animate()
                  .fadeIn(delay: 400.ms),

              const SizedBox(height: 36),

              // Trip summary card
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: const Color(0xFF0E0E0E),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: kSuccess.withOpacity(0.3)),
                ),
                child: Column(children: [
                  _TripSummaryRow(
                      label: 'Total Time',
                      value: '${widget.route.aiEtaMin.toStringAsFixed(0)} min'),
                  const Divider(color: kCardBorder, height: 20),
                  _TripSummaryRow(
                      label: 'Distance',
                      value: widget.route.distanceLabel),
                  const Divider(color: kCardBorder, height: 20),
                  _TripSummaryRow(
                      label: 'AI Time Saved',
                      value:
                          '${widget.route.timeSavedMin.abs().toStringAsFixed(0)} min',
                      valueColor: kSuccess),
                  const Divider(color: kCardBorder, height: 20),
                  _TripSummaryRow(
                      label: 'Emergency Type',
                      value: type.label,
                      valueColor: type.color),
                ]),
              ).animate().fadeIn(delay: 500.ms).slideY(begin: 0.1, end: 0),

              const SizedBox(height: 32),

              // Done button
              GestureDetector(
                onTap: () {
                  Navigator.of(context).popUntil((r) => r.isFirst);
                },
                child: Container(
                  height: 56,
                  decoration: BoxDecoration(
                    color: kSuccess,
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: [
                      BoxShadow(
                          color: kSuccess.withOpacity(0.4),
                          blurRadius: 18,
                          offset: const Offset(0, 5)),
                    ],
                  ),
                  child: Center(
                    child: Text('INCIDENT COMPLETE',
                        style: GoogleFonts.rajdhani(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.5)),
                  ),
                ),
              ).animate().fadeIn(delay: 700.ms),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Sub-widgets ────────────────────────────────────────────────────────────

class _StatBlock extends StatelessWidget {
  final String label;
  final String value;
  final String sublabel;
  final Color color;

  const _StatBlock({
    required this.label,
    required this.value,
    required this.sublabel,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Text(label,
          style: GoogleFonts.rajdhani(
              color: kTextSecondary, fontSize: 10, letterSpacing: 1)),
      const SizedBox(height: 4),
      Text(value,
          style: GoogleFonts.rajdhani(
              color: color,
              fontSize: 20,
              fontWeight: FontWeight.w800)),
      Text(sublabel,
          style: GoogleFonts.rajdhani(
              color: kTextSecondary, fontSize: 10)),
    ]);
  }
}

class _TripSummaryRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;

  const _TripSummaryRow(
      {required this.label, required this.value, this.valueColor});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label,
            style: GoogleFonts.rajdhani(
                color: kTextSecondary, fontSize: 14)),
        Text(value,
            style: GoogleFonts.rajdhani(
                color: valueColor ?? Colors.white,
                fontSize: 14,
                fontWeight: FontWeight.bold)),
      ],
    );
  }
}
