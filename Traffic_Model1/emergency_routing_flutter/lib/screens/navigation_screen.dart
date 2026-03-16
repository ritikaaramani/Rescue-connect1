import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' as ui;
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

  // Progress
  double _progress = 0.0;
  double _elapsedMin = 0.0;
  bool _isArrived = false;

  // 3D buildings toggle (perspective is ALWAYS on in both modes)
  bool _showBuildings = true;

  // Heading (bearing) of travel, used to rotate map heading-up
  double _bearing = 0.0;

  late AnimationController _pulseCtrl;
  late AnimationController _sirenCtrl;
  Timer? _progressTimer;

  // Turn instructions — updated as progress advances
  final _turns = [
    'Head forward on current road',
    'Turn right at the junction',
    'Continue straight — 2.1 km',
    'Turn left onto main road',
    'Continue straight — 1.5 km',
    'Take the ramp — merge right',
    'Exit ahead — prepare to turn',
    'Arriving at destination',
  ];
  int _turnIndex = 0;

  // ── Lifecycle ──────────────────────────────────────────────────────────────

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

    _startSimulation();
  }

  void _startSimulation() {
    const interval = Duration(seconds: 3);
    final totalSteps =
        (widget.route.aiEtaMin * 60 / interval.inSeconds).ceil().clamp(1, 9999);
    final progressPerStep = 1.0 / totalSteps;
    final minutesPerStep = widget.route.aiEtaMin / totalSteps;

    _progressTimer = Timer.periodic(interval, (timer) {
      if (!mounted) { timer.cancel(); return; }

      setState(() {
        _progress = (_progress + progressPerStep).clamp(0.0, 1.0);
        _elapsedMin += minutesPerStep;
        _turnIndex =
            (_progress * (_turns.length - 1)).floor().clamp(0, _turns.length - 1);
        _bearing = _calculateBearing();

        if (_progress >= 1.0) {
          _isArrived = true;
          timer.cancel();
          HapticFeedback.heavyImpact();
        }
      });

      // Move map — look-ahead camera, rotated to heading
      try {
        _mapCtrl.moveAndRotate(_lookAheadPosition, _navZoom, _bearing);
      } catch (_) {
        _mapCtrl.move(_lookAheadPosition, _navZoom);
      }
    });
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    _sirenCtrl.dispose();
    _progressTimer?.cancel();
    super.dispose();
  }

  // ── Route helpers ──────────────────────────────────────────────────────────

  /// Always navigation zoom (close street level for both modes).
  double get _navZoom => 17.0;

  LatLng get _vehiclePosition {
    final pts = widget.route.polyline;
    if (pts.isEmpty) return const LatLng(28.6139, 77.2090);
    final idx = ((_progress) * (pts.length - 1)).floor().clamp(0, pts.length - 1);
    return pts[idx];
  }

  /// Camera is placed slightly AHEAD of the vehicle so the vehicle appears
  /// in the lower portion of the screen — like Google Maps navigation mode.
  LatLng get _lookAheadPosition {
    final pts = widget.route.polyline;
    if (pts.length < 2) return _vehiclePosition;
    final currentIdx =
        ((_progress) * (pts.length - 1)).floor().clamp(0, pts.length - 1);
    final lookIdx = (currentIdx + 10).clamp(0, pts.length - 1);
    final v = _vehiclePosition;
    final t = pts[lookIdx];
    // Interpolate 35% toward the look-ahead point
    return LatLng(
      v.latitude + (t.latitude - v.latitude) * 0.35,
      v.longitude + (t.longitude - v.longitude) * 0.35,
    );
  }

  /// Bearing (degrees) from current vehicle position toward upcoming route.
  double _calculateBearing() {
    final pts = widget.route.polyline;
    if (pts.length < 2) return _bearing;
    final idx =
        ((_progress) * (pts.length - 1)).floor().clamp(0, pts.length - 3);
    final A = pts[idx];
    final B = pts[(idx + 5).clamp(0, pts.length - 1)];
    final dLon = (B.longitude - A.longitude) * math.pi / 180;
    final lat1 = A.latitude * math.pi / 180;
    final lat2 = B.latitude * math.pi / 180;
    final x = math.sin(dLon) * math.cos(lat2);
    final y = math.cos(lat1) * math.sin(lat2) -
        math.sin(lat1) * math.cos(lat2) * math.cos(dLon);
    return ((math.atan2(x, y) * 180 / math.pi) + 360) % 360;
  }

  double get _remainingMin =>
      (widget.route.aiEtaMin - _elapsedMin).clamp(0, widget.route.aiEtaMin);

  double get _remainingKm => widget.route.distanceKm * (1.0 - _progress);

  int get _vehicleIdx =>
      ((_progress) * (widget.route.polyline.length - 1))
          .floor()
          .clamp(0, widget.route.polyline.length - 1);

  // ── BUILD ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final r = widget.route;
    final type = r.emergencyType;

    if (_isArrived) return _buildArrivedScreen(type);

    return Scaffold(
      backgroundColor: const Color(0xFF0A0A0A),
      body: Stack(children: [
        // ── MAP with navigation perspective ───────────────────────────────
        _buildNavigationView(r, type),

        // ── SIREN BAR ─────────────────────────────────────────────────────
        _buildSirenBar(type),

        // ── TURN INSTRUCTION ──────────────────────────────────────────────
        Positioned(
          top: 90,
          left: 0,
          right: 0,
          child: _buildTurnInstruction(type),
        ),

        // ── 3D BUILDINGS TOGGLE ───────────────────────────────────────────
        Positioned(
          right: 16,
          bottom: 195,
          child: _build3DToggle(),
        ),

        // ── BOTTOM PANEL ──────────────────────────────────────────────────
        Positioned(
          bottom: 0, left: 0, right: 0,
          child: _buildBottomPanel(r, type),
        ),
      ]),
    );
  }

  // ── Navigation view (perspective + optional buildings) ────────────────────

  Widget _buildNavigationView(RouteResult r, EmergencyType type) {
    final polyline = r.polyline;
    final vehicle = _vehiclePosition;
    final completedIdx = _vehicleIdx;

    final completed = polyline.take(completedIdx + 1).toList();
    final remaining = completedIdx < polyline.length - 1
        ? polyline.skip(completedIdx).toList()
        : <LatLng>[];

    // The flat map — tiles load normally at zoom 17 for the flat viewport
    final flatMap = FlutterMap(
      mapController: _mapCtrl,
      options: MapOptions(
        initialCenter: _lookAheadPosition,
        initialZoom: _navZoom,
        rotation: _bearing,
        interactionOptions: const InteractionOptions(flags: InteractiveFlag.none),
      ),
      children: [
        TileLayer(
          // Carto Dark Matter — dark emergency-style basemap
          urlTemplate:
              'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
          subdomains: const ['a', 'b', 'c', 'd'],
          userAgentPackageName: 'com.swiftemergency.app',
          keepBuffer: 6,
        ),

        // Route — dark glow border (drawn first, acts as outline)
        if (remaining.isNotEmpty)
          PolylineLayer(polylines: [
            Polyline(points: remaining, strokeWidth: 14,
                color: const Color(0xFFFF1744).withOpacity(0.35),
                strokeCap: StrokeCap.round),
          ]),

        // Route — red emergency route line
        if (remaining.isNotEmpty)
          PolylineLayer(polylines: [
            Polyline(points: remaining, strokeWidth: 6,
                color: const Color(0xFFFF1744), strokeCap: StrokeCap.round),
          ]),

        // Completed (dim gray)
        if (completed.isNotEmpty)
          PolylineLayer(polylines: [
            Polyline(points: completed, strokeWidth: 3,
                color: Colors.grey[700]!, strokeCap: StrokeCap.round),
          ]),

        // Destination
        if (polyline.isNotEmpty)
          MarkerLayer(markers: [
            Marker(
              point: polyline.last, width: 44, height: 44,
              child: Container(
                decoration: BoxDecoration(
                  color: const Color(0xFFFF1744), shape: BoxShape.circle,
                  boxShadow: [BoxShadow(color: const Color(0xFFFF1744).withOpacity(0.6),
                      blurRadius: 16, spreadRadius: 2)],
                ),
                child: const Icon(Icons.local_hospital, color: Colors.white, size: 22),
              ),
            ),
          ]),

        // Vehicle marker
        MarkerLayer(markers: [
          Marker(
            point: vehicle, width: 52, height: 52,
            child: _buildVehicleMarker(type),
          ),
        ]),
      ],
    );

    // Stack: flat map + buildings overlay (when 3D is on)
    final mapStack = Stack(children: [
      Positioned.fill(child: flatMap),

      // 3D buildings drawn over the map
      if (_showBuildings)
        Positioned.fill(
          child: IgnorePointer(
            child: CustomPaint(
              painter: _BuildingsPainter(
                vehiclePosition: vehicle,
                zoom: _navZoom,
                bearing: _bearing,
                emergencyColor: type.color,
              ),
            ),
          ),
        ),

      // Horizon fade — blends distant tiles into sky
      Positioned(
        top: 0, left: 0, right: 0,
        child: IgnorePointer(
          child: Container(
            height: 80,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  const Color(0xFF0A0A0A),
                  const Color(0xFF0A0A0A).withOpacity(0.6),
                  Colors.transparent,
                ],
                stops: const [0.0, 0.4, 1.0],
              ),
            ),
          ),
        ),
      ),
    ]);

    // ── PERSPECTIVE TRANSFORM — makes map look like front/road view ──────
    // Camera is at the bottom, road recedes into the horizon.
    // This is applied to BOTH 2D and 3D modes.
    return ClipRect(
      child: Transform(
        transform: Matrix4.identity()
          ..setEntry(3, 2, 0.00055)   // perspective depth (focal length)
          ..rotateX(-0.62),           // ~35° forward tilt = navigation angle
        alignment: Alignment.bottomCenter,
        child: mapStack,
      ),
    );
  }

  Widget _buildVehicleMarker(EmergencyType type) {
    return AnimatedBuilder(
      animation: _sirenCtrl,
      builder: (_, __) {
        final glow = 0.5 + 0.5 * _sirenCtrl.value;
        return Container(
          decoration: BoxDecoration(
            color: const Color(0xFF1A1A1A),
            shape: BoxShape.circle,
            border: Border.all(color: type.color, width: 3),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.6),
                blurRadius: 12, spreadRadius: 2,
              ),
              BoxShadow(
                color: type.color.withOpacity(glow),
                blurRadius: 24, spreadRadius: 6,
              ),
            ],
          ),
          child: Icon(type.icon, color: type.color, size: 22),
        );
      },
    );
  }

  // ── 3D toggle ──────────────────────────────────────────────────────────────

  Widget _build3DToggle() {
    return GestureDetector(
      onTap: () {
        setState(() => _showBuildings = !_showBuildings);
        HapticFeedback.selectionClick();
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: _showBuildings
              ? const Color(0xFFFF1744).withOpacity(0.9)
              : const Color(0xFF1A1A1A),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: _showBuildings
                ? const Color(0xFFFF1744)
                : Colors.white24,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.5),
              blurRadius: 10, offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(
            _showBuildings ? Icons.location_city : Icons.map_outlined,
            color: Colors.white,
            size: 16,
          ),
          const SizedBox(width: 6),
          Text(
            _showBuildings ? '3D' : '2D',
            style: GoogleFonts.rajdhani(
              color: Colors.white,
              fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 0.5,
            ),
          ),
        ]),
      ),
    );
  }

  // ── Siren bar ──────────────────────────────────────────────────────────────

  Widget _buildSirenBar(EmergencyType type) {
    return Positioned(
      top: 0, left: 0, right: 0,
      child: SafeArea(
        child: AnimatedBuilder(
          animation: _sirenCtrl,
          builder: (_, __) => Container(
            margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: type.color.withOpacity(0.82 + 0.18 * _sirenCtrl.value),
              borderRadius: BorderRadius.circular(14),
              boxShadow: [
                BoxShadow(
                  color: type.color.withOpacity(0.4 + 0.3 * _sirenCtrl.value),
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
                      color: Colors.white, fontSize: 13,
                      fontWeight: FontWeight.bold, letterSpacing: 1),
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
                  child: const Icon(Icons.close, color: Colors.white, size: 14),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }

  // ── Turn instruction ───────────────────────────────────────────────────────

  Widget _buildTurnInstruction(EmergencyType type) {
    final turn = _turns[_turnIndex];
    final isLeft = turn.contains('left');
    final isRight = turn.contains('right');
    final isRamp = turn.contains('ramp') || turn.contains('merge');
    final icon = isLeft
        ? Icons.turn_left
        : isRight
            ? Icons.turn_right
            : isRamp
                ? Icons.merge_type
                : Icons.straight;

    final distToTurn = (_remainingKm * 0.35).clamp(0, _remainingKm);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: const Color(0xFF111111),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white12),
          boxShadow: [
            BoxShadow(color: Colors.black.withOpacity(0.5),
                blurRadius: 16, offset: const Offset(0, 4)),
          ],
        ),
        child: Row(children: [
          Container(
            width: 50, height: 50,
            decoration: BoxDecoration(
              color: type.color.withOpacity(0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: type.color, size: 28),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(turn,
                      style: GoogleFonts.rajdhani(
                          color: Colors.white, fontSize: 16,
                          fontWeight: FontWeight.w700)),
                  Row(children: [
                    Text(
                      distToTurn >= 1
                          ? '${distToTurn.toStringAsFixed(1)} km'
                          : '${(distToTurn * 1000).toStringAsFixed(0)} m',
                      style: GoogleFonts.rajdhani(
                          color: Colors.grey[400], fontSize: 13),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      width: 4, height: 4,
                      decoration: BoxDecoration(
                          color: Colors.grey[600], shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '${_remainingMin.toStringAsFixed(0)} min remaining',
                      style: GoogleFonts.rajdhani(
                          color: type.color, fontSize: 12,
                          fontWeight: FontWeight.w600),
                    ),
                  ]),
                ]),
          ),
          // Bearing indicator
          Column(children: [
            Text('▲', style: TextStyle(color: type.color, fontSize: 10)),
            Text(
              '${(_bearing).toStringAsFixed(0)}°',
              style: GoogleFonts.rajdhani(color: Colors.grey[600], fontSize: 10),
            ),
          ]),
        ]),
      ).animate().slideX(begin: -0.05, end: 0, duration: 300.ms).fadeIn(),
    );
  }

  // ── Bottom panel ───────────────────────────────────────────────────────────

  Widget _buildBottomPanel(RouteResult r, EmergencyType type) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0E0E0E),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: const Border(top: BorderSide(color: Colors.white12)),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.6), blurRadius: 20,
              offset: const Offset(0, -4)),
        ],
      ),
      padding: EdgeInsets.fromLTRB(
          20, 16, 20, MediaQuery.of(context).padding.bottom + 16),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        // Progress bar
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: _progress.clamp(0.0, 1.0),
            backgroundColor: Colors.white12,
            valueColor: AlwaysStoppedAnimation(type.color),
            minHeight: 6,
          ),
        ),

        const SizedBox(height: 16),

        // Stats
        Row(children: [
          Expanded(child: _StatBlock(
            label: 'ETA', value: '${_remainingMin.toStringAsFixed(0)} min',
            sublabel: 'remaining', color: type.color,
          )),
          Container(width: 1, height: 40, color: Colors.white12),
          Expanded(child: _StatBlock(
            label: 'Distance', value: '${_remainingKm.toStringAsFixed(1)} km',
            sublabel: 'remaining', color: Colors.white,
          )),
          Container(width: 1, height: 40, color: Colors.white12),
          Expanded(child: _StatBlock(
            label: 'Priority', value: 'ACTIVE',
            sublabel: type.label, color: kSuccess,
          )),
        ]),

        const SizedBox(height: 16),

        // Route info
        Row(children: [
          Icon(Icons.location_on, color: Colors.grey[600], size: 13),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              '${widget.origin} → ${widget.destination}',
              style: GoogleFonts.rajdhani(color: Colors.grey[600], fontSize: 12),
              maxLines: 1, overflow: TextOverflow.ellipsis,
            ),
          ),
        ]),

        const SizedBox(height: 12),

        // AI indicator
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
                width: 6, height: 6,
                decoration: BoxDecoration(
                  color: kAiCyan, shape: BoxShape.circle,
                  boxShadow: [BoxShadow(
                      color: kAiCyan.withOpacity(0.4 + 0.4 * _pulseCtrl.value),
                      blurRadius: 6)],
                ),
              ),
            ),
            const SizedBox(width: 8),
            Text('LSTM+GCN AI actively monitoring route conditions',
                style: GoogleFonts.rajdhani(
                    color: kAiCyan, fontSize: 11, letterSpacing: 0.3)),
          ]),
        ),

        const SizedBox(height: 14),

        // END MISSION button — return to home for new dispatch
        GestureDetector(
          onTap: () {
            HapticFeedback.mediumImpact();
            Navigator.of(context).popUntil((r) => r.isFirst);
          },
          child: Container(
            height: 48,
            decoration: BoxDecoration(
              color: Colors.transparent,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white24),
            ),
            child: Center(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.arrow_back, color: Colors.white70, size: 16),
                  const SizedBox(width: 8),
                  Text('END MISSION — NEW DISPATCH',
                      style: GoogleFonts.rajdhani(
                          color: Colors.white70, fontSize: 14,
                          fontWeight: FontWeight.bold, letterSpacing: 1)),
                ],
              ),
            ),
          ),
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
              Container(
                width: 100, height: 100,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: kSuccess.withOpacity(0.1),
                  border: Border.all(color: kSuccess, width: 2),
                ),
                child: const Icon(Icons.check_circle, color: kSuccess, size: 56),
              ).animate().scale(begin: const Offset(0.5, 0.5), duration: 500.ms,
                  curve: Curves.elasticOut),

              const SizedBox(height: 28),

              Text('ARRIVED',
                  style: GoogleFonts.rajdhani(
                      color: Colors.white, fontSize: 36,
                      fontWeight: FontWeight.w900, letterSpacing: 4))
                  .animate().fadeIn(delay: 300.ms, duration: 400.ms),

              const SizedBox(height: 8),

              Text(widget.destination,
                  textAlign: TextAlign.center,
                  style: GoogleFonts.rajdhani(
                      color: kTextSecondary, fontSize: 16))
                  .animate().fadeIn(delay: 400.ms),

              const SizedBox(height: 36),

              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: const Color(0xFF0E0E0E),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: kSuccess.withOpacity(0.3)),
                ),
                child: Column(children: [
                  _TripSummaryRow(label: 'Total Time',
                      value: '${widget.route.aiEtaMin.toStringAsFixed(0)} min'),
                  const Divider(color: kCardBorder, height: 20),
                  _TripSummaryRow(label: 'Distance',
                      value: widget.route.distanceLabel),
                  const Divider(color: kCardBorder, height: 20),
                  _TripSummaryRow(label: 'AI Time Saved',
                      value: '${widget.route.timeSavedMin.abs().toStringAsFixed(0)} min',
                      valueColor: kSuccess),
                  const Divider(color: kCardBorder, height: 20),
                  _TripSummaryRow(label: 'Emergency Type',
                      value: type.label, valueColor: type.color),
                ]),
              ).animate().fadeIn(delay: 500.ms).slideY(begin: 0.1, end: 0),

              const SizedBox(height: 32),

              GestureDetector(
                onTap: () => Navigator.of(context).popUntil((r) => r.isFirst),
                child: Container(
                  height: 56,
                  decoration: BoxDecoration(
                    color: kSuccess,
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: [BoxShadow(
                        color: kSuccess.withOpacity(0.4), blurRadius: 18,
                        offset: const Offset(0, 5))],
                  ),
                  child: Center(
                    child: Text('INCIDENT COMPLETE',
                        style: GoogleFonts.rajdhani(
                            color: Colors.white, fontSize: 16,
                            fontWeight: FontWeight.bold, letterSpacing: 1.5)),
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

// ── 3D City Buildings Painter ──────────────────────────────────────────────
//
// Generates a deterministic city grid around the vehicle position and draws
// 3D-extruded buildings using Web Mercator projection + map rotation correction.
// Works independently of polyline segment density — looks great for any route.

class _BuildingsPainter extends CustomPainter {
  final LatLng vehiclePosition;
  final double zoom;
  final double bearing; // map rotation in degrees (heading-up)
  final Color emergencyColor;

  static const double _tileSize = 256.0;

  const _BuildingsPainter({
    required this.vehiclePosition,
    required this.zoom,
    required this.bearing,
    required this.emergencyColor,
  });

  // ── Web Mercator LatLng → flat screen point (north-up) ──────────────────

  Offset _projectFlat(LatLng pt, Size size) {
    final scale = _tileSize * math.pow(2, zoom);

    double lonToX(double lon) => (lon + 180.0) / 360.0 * scale;
    double latToY(double lat) {
      final sinLat = math.sin(lat * math.pi / 180.0);
      return (0.5 -
              math.log((1.0 + sinLat) / (1.0 - sinLat)) / (4.0 * math.pi)) *
          scale;
    }

    final cx = lonToX(vehiclePosition.longitude);
    final cy = latToY(vehiclePosition.latitude);
    return Offset(
      size.width / 2.0 + (lonToX(pt.longitude) - cx),
      size.height / 2.0 + (latToY(pt.latitude) - cy),
    );
  }

  // Apply map rotation correction: when map is rotated bearing° (heading-up),
  // screen points need to be rotated by -bearing around screen center.
  Offset _project(LatLng pt, Size size) {
    final flat = _projectFlat(pt, size);
    if (bearing.abs() < 0.5) return flat;
    final angle = -bearing * math.pi / 180.0;
    final cx = size.width / 2.0;
    final cy = size.height / 2.0;
    final dx = flat.dx - cx;
    final dy = flat.dy - cy;
    return Offset(
      cx + dx * math.cos(angle) - dy * math.sin(angle),
      cy + dx * math.sin(angle) + dy * math.cos(angle),
    );
  }

  @override
  void paint(Canvas canvas, Size size) {
    // At zoom 17, 1° lat ≈ 110574 * 256 * 2^17 / (360 * 2^17 * 256) = ...
    // Simpler: at zoom 17, 0.0003° ≈ 35px — use as grid step
    const gridStepDeg = 0.00035; // ~38m per building slot
    const gridRange = 0.0035;    // ±385m around vehicle

    // Sort rows from farthest to nearest (painter's algorithm) so near
    // buildings occlude far ones correctly.
    final rowOffsets = <double>[];
    for (double dLat = -gridRange; dLat <= gridRange; dLat += gridStepDeg) {
      rowOffsets.add(dLat);
    }
    // Sort: draw buildings farther from vehicle first (back-to-front)
    rowOffsets.sort((a, b) => b.abs().compareTo(a.abs()));

    for (final dLat in rowOffsets) {
      for (double dLon = -gridRange; dLon <= gridRange; dLon += gridStepDeg) {
        // Skip the road corridor (centre strip) — leave space for the road
        final absLon = dLon.abs();
        final absLat = dLat.abs();
        if (absLon < 0.00010 && absLat < 0.00010) continue; // vehicle zone
        if (absLon < gridStepDeg * 0.55) continue;         // road strip

        final buildingPos = LatLng(
          vehiclePosition.latitude + dLat,
          vehiclePosition.longitude + dLon,
        );

        final screen = _project(buildingPos, size);

        // Cull offscreen buildings
        if (!_isOnScreen(screen, size)) continue;

        // Deterministic seed from coordinates
        final seed =
            ((buildingPos.latitude * 1e5).abs().toInt() * 31337 +
                    (buildingPos.longitude * 1e5).abs().toInt())
                .abs() %
                999983;

        // Skip ~30% of slots to create natural gaps/parks
        if (seed % 10 < 3) continue;

        final rng = math.Random(seed);
        _drawBuilding(canvas, size, screen, rng, dLat, dLon, seed);
      }
    }
  }

  bool _isOnScreen(Offset pt, Size size) =>
      pt.dx > -60 && pt.dx < size.width + 60 &&
      pt.dy > -60 && pt.dy < size.height + 60;

  void _drawBuilding(
    Canvas canvas,
    Size size,
    Offset screen,
    math.Random rng,
    double dLat,
    double dLon,
    int seed,
  ) {
    // Building dimensions in pixels
    // At zoom 17, 0.0003° ≈ 35px, so buildings ~20-28px wide
    final w = (16.0 + rng.nextDouble() * 14).clamp(14.0, 30.0);
    final d = (10.0 + rng.nextDouble() * 8).clamp(8.0, 18.0); // depth offset
    final h = (30.0 + rng.nextDouble() * 55).clamp(25.0, 85.0);

    // Distance-based fade: buildings further from vehicle appear smaller/fainter
    final distFactor = math.sqrt(dLat * dLat + dLon * dLon) / 0.0035;
    final alpha = (1.0 - distFactor * 0.6).clamp(0.3, 1.0);

    // Colour palette — dark city night buildings
    final palettes = [
      // Dark concrete (most common)
      [const Color(0xFF2A2A2E), const Color(0xFF3A3A3F), const Color(0xFF1E1E22)],
      // Warm orange-brown (residential)
      [const Color(0xFF3D2B1F), const Color(0xFF4E3828), const Color(0xFF2C1E15)],
      // Teal-blue (commercial/glass)
      [const Color(0xFF1A2F35), const Color(0xFF243D44), const Color(0xFF132228)],
      // Warm amber (older buildings)
      [const Color(0xFF332A1A), const Color(0xFF443820), const Color(0xFF241E12)],
      // Cool steel (modern towers)
      [const Color(0xFF1E2530), const Color(0xFF28323F), const Color(0xFF161C24)],
    ];
    final pal = palettes[rng.nextInt(palettes.length)];

    final frontColor = pal[0].withOpacity(alpha);
    final topColor = pal[1].withOpacity(alpha);
    final sideColor = pal[2].withOpacity(alpha);

    final cx = screen.dx;
    final cy = screen.dy;

    // Front face corners
    final bl = Offset(cx - w / 2, cy);
    final br = Offset(cx + w / 2, cy);
    final tl = Offset(cx - w / 2, cy - h);
    final tr = Offset(cx + w / 2, cy - h);

    // Depth offset (isometric-ish depth)
    final depX = d * 0.75;
    final depY = -d * 0.5;

    // ── Front face ─────────────────────────────────────────────────────────
    canvas.drawPath(
      ui.Path()
        ..moveTo(bl.dx, bl.dy)
        ..lineTo(br.dx, br.dy)
        ..lineTo(tr.dx, tr.dy)
        ..lineTo(tl.dx, tl.dy)
        ..close(),
      Paint()..color = frontColor,
    );

    // ── Top face ───────────────────────────────────────────────────────────
    canvas.drawPath(
      ui.Path()
        ..moveTo(tl.dx, tl.dy)
        ..lineTo(tr.dx, tr.dy)
        ..lineTo(tr.dx + depX, tr.dy + depY)
        ..lineTo(tl.dx + depX, tl.dy + depY)
        ..close(),
      Paint()..color = topColor,
    );

    // ── Side (right) face ──────────────────────────────────────────────────
    canvas.drawPath(
      ui.Path()
        ..moveTo(br.dx, br.dy)
        ..lineTo(br.dx + depX, br.dy + depY)
        ..lineTo(tr.dx + depX, tr.dy + depY)
        ..lineTo(tr.dx, tr.dy)
        ..close(),
      Paint()..color = sideColor,
    );

    // ── Windows — warm glowing lights (night city style) ───────────────────
    if (h > 25) {
      final floors = (h / 12).floor().clamp(1, 5);
      final cols = (w / 8).floor().clamp(1, 4);
      // Window colors: warm yellow, cool blue, or orange
      final windowColors = [
        const Color(0xFFFFD580), // warm yellow
        const Color(0xFF80C8FF), // cool blue
        const Color(0xFFFFB347), // orange
      ];
      for (int row = 0; row < floors; row++) {
        for (int col = 0; col < cols; col++) {
          // ~60% of windows are lit
          if ((seed + row * 7 + col * 3) % 10 < 4) continue;
          final wx = cx - w / 2 + (col + 0.5) * w / cols;
          final wy = cy - (row + 0.6) * h / floors;
          final wColor = windowColors[(seed + row + col) % windowColors.length];
          canvas.drawRect(
            Rect.fromCenter(center: Offset(wx, wy), width: 2.5, height: 3.0),
            Paint()..color = wColor.withOpacity(0.75 * alpha),
          );
        }
      }
    }

    // ── Outline ────────────────────────────────────────────────────────────
    canvas.drawRect(
      Rect.fromLTWH(cx - w / 2, cy - h, w, h),
      Paint()
        ..color = Colors.white.withOpacity(0.10 * alpha)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.5,
    );
  }

  @override
  bool shouldRepaint(_BuildingsPainter old) =>
      old.vehiclePosition.latitude != vehiclePosition.latitude ||
      old.vehiclePosition.longitude != vehiclePosition.longitude ||
      old.bearing != bearing ||
      old.zoom != zoom;
}

// ── Sub-widgets ─────────────────────────────────────────────────────────────

class _StatBlock extends StatelessWidget {
  final String label, value, sublabel;
  final Color color;

  const _StatBlock({
    required this.label, required this.value,
    required this.sublabel, required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Text(label,
          style: GoogleFonts.rajdhani(
              color: Colors.grey[600], fontSize: 10, letterSpacing: 1)),
      const SizedBox(height: 4),
      Text(value,
          style: GoogleFonts.rajdhani(
              color: color, fontSize: 20, fontWeight: FontWeight.w800)),
      Text(sublabel,
          style: GoogleFonts.rajdhani(color: Colors.grey[600], fontSize: 10)),
    ]);
  }
}

class _TripSummaryRow extends StatelessWidget {
  final String label, value;
  final Color? valueColor;
  const _TripSummaryRow({required this.label, required this.value, this.valueColor});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label,
            style: GoogleFonts.rajdhani(color: kTextSecondary, fontSize: 14)),
        Text(value,
            style: GoogleFonts.rajdhani(
                color: valueColor ?? Colors.white, fontSize: 14,
                fontWeight: FontWeight.bold)),
      ],
    );
  }
}
