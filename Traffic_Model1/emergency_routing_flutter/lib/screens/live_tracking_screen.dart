import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';
import 'package:dio/dio.dart';
import '../config/theme.dart';
import '../services/backend_service.dart';

/// Full-screen live tracking with real-time vehicle position, blockages, and AI rerouting.
/// Used by both Dispatch (to track) and Driver (to navigate).
class LiveTrackingScreen extends ConsumerStatefulWidget {
  final String origin;
  final String destination;
  final LatLng originCoord;
  final LatLng destCoord;
  final bool isDriver; // true = driver view, false = dispatch tracking view

  const LiveTrackingScreen({
    super.key,
    required this.origin,
    required this.destination,
    required this.originCoord,
    required this.destCoord,
    this.isDriver = false,
  });

  @override
  ConsumerState<LiveTrackingScreen> createState() => _LiveTrackingScreenState();
}

class _LiveTrackingScreenState extends ConsumerState<LiveTrackingScreen>
    with TickerProviderStateMixin {
  final MapController _map = MapController();
  final Dio _dio = Dio();

  // Route data
  List<LatLng> _routePoints = [];
  List<LatLng> _originalRoute = [];
  double _routeDistKm = 0;
  double _routeDurMin = 0;

  // Vehicle real-time data from backend
  double _currentLat = 0;
  double _currentLon = 0;
  double _currentSpeed = 0;
  double _etaMin = 0;
  double _reliability = 0.92;
  
  // Vehicle simulation
  int _vehicleIdx = 0;
  LatLng? _vehiclePos;
  Timer? _moveTimer;

  // State
  bool _loading = true;
  bool _hasBlockage = false;
  bool _isRerouting = false;
  bool _rerouted = false;
  String _statusText = 'Fetching optimal route...';
  int _rerouteCount = 0;
  LatLng? _blockagePoint;
  
  // Blockages from backend
  List<Map<String, dynamic>> _activeBlockages = [];
  late StreamSubscription _vehicleUpdatesSub;
  late StreamSubscription _blockageAlertsSub;
  late StreamSubscription _rerouteAlertsSub;

  late AnimationController _pulseCtrl;

  static const _darkMatrix = <double>[
    -1, 0, 0, 0, 255,
    0, -1, 0, 0, 255,
    0, 0, -1, 0, 255,
    0, 0, 0, 1, 0,
  ];

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
        vsync: this, duration: const Duration(seconds: 2))
      ..repeat(reverse: true);
    
    // Initialize with origin as current position
    _currentLat = widget.originCoord.latitude;
    _currentLon = widget.originCoord.longitude;
    
    _fetchRoute(widget.originCoord, widget.destCoord);
    _setupBackendListeners();
  }
  
  void _setupBackendListeners() {
    final backend = ref.read(backendServiceProvider);
    
    // Initialize backend first
    backend.findWorkingBackend().then((_) {
      // Start polling for blockages
      if (mounted) {
        backend.startBlockagePolling();
      }
    }).catchError((e) {
      print('Error finding backend: $e');
    });
    
    // Listen to vehicle position updates
    _vehicleUpdatesSub = backend.vehicleUpdates.listen((data) {
      if (!mounted) return;
      setState(() {
        _currentLat = (data['lat'] ?? _currentLat).toDouble();
        _currentLon = (data['lon'] ?? _currentLon).toDouble();
        _currentSpeed = (data['speed_kmh'] ?? _currentSpeed).toDouble();
        _etaMin = (data['eta_minutes'] ?? _etaMin).toDouble();
        _vehiclePos = LatLng(_currentLat, _currentLon);
      });
    });
    
    // Listen to blockage alerts
    _blockageAlertsSub = backend.blockageAlerts.listen((data) {
      if (!mounted) return;
      setState(() {
        _hasBlockage = true;
        _activeBlockages.add(data);
      });
      
      // Auto-trigger rerouting on blockage
      Future.delayed(const Duration(seconds: 2), () => _triggerReroute());
    });
    
    // Listen to reroute events
    _rerouteAlertsSub = backend.rerouteAlerts.listen((data) {
      if (!mounted) return;
      setState(() {
        _rerouted = true;
        _rerouteCount++;
        _statusText = '✅ REROUTED — ${data['reason'] ?? "Dynamic optimization"}';
      });
    });
    
    // Fetch active blockages from backend
    _fetchBlockages();
  }
  
  Future<void> _fetchBlockages() async {
    try {
      final backend = ref.read(backendServiceProvider);
      final blockages = await backend.getActiveBlockages();
      if (mounted) {
        setState(() => _activeBlockages = blockages);
      }
    } catch (e) {
      print('Error fetching blockages: $e');
    }
  }

  @override
  void dispose() {
    _moveTimer?.cancel();
    _pulseCtrl.dispose();
    _vehicleUpdatesSub.cancel();
    _blockageAlertsSub.cancel();
    _rerouteAlertsSub.cancel();
    super.dispose();
  }

  // ── Fetch route from OSRM ─────────────────────────────────────────────

  Future<void> _fetchRoute(LatLng from, LatLng to,
      {bool isReroute = false, LatLng? avoid}) async {
    setState(() {
      _loading = true;
      _statusText =
          isReroute ? '🔄 AI REROUTING...' : '📍 Calculating optimal route...';
    });

    try {
      // Build waypoints, adding a mid-point offset if rerouting to get a different path
      String coordStr;
      if (isReroute && avoid != null) {
        // Create a waypoint that's offset from the blockage to force a different route
        final offsetLat = avoid.latitude + 0.008 * (Random().nextBool() ? 1 : -1);
        final offsetLng = avoid.longitude + 0.008 * (Random().nextBool() ? 1 : -1);
        coordStr =
            '${from.longitude},${from.latitude};'
            '$offsetLng,$offsetLat;'
            '${to.longitude},${to.latitude}';
      } else {
        coordStr =
            '${from.longitude},${from.latitude};'
            '${to.longitude},${to.latitude}';
      }

      final url =
          'http://router.project-osrm.org/route/v1/driving/$coordStr?geometries=geojson&overview=full';
      final res = await _dio.get(url);

      if (res.data['code'] != 'Ok') throw Exception('No route found');

      final route = res.data['routes'][0];
      final coords = route['geometry']['coordinates'] as List;
      final distKm = (route['distance'] as num) / 1000;
      final durMin = (route['duration'] as num) / 60;

      final points =
          coords.map((c) => LatLng(c[1] as double, c[0] as double)).toList();

      setState(() {
        if (!isReroute) {
          _originalRoute = List.from(points);
        }
        _routePoints = points;
        _routeDistKm = distKm;
        _routeDurMin = durMin;
        _etaMin = durMin;
        _vehicleIdx = 0;
        _vehiclePos = points.first;
        _loading = false;
        _statusText = isReroute
            ? 'REROUTED — new path active (${distKm.toStringAsFixed(1)} km)'
            : 'Route locked — ${distKm.toStringAsFixed(1)} km';
        if (isReroute) {
          _rerouted = true;
          _isRerouting = false;
          _rerouteCount++;
          _reliability = max(0.55, _reliability - 0.08);
        }
      });

      _map.move(from, 13.5);
      _startVehicleAnimation();
    } catch (e) {
      setState(() {
        _loading = false;
        _statusText = 'Route error: $e';
      });
    }
  }

  // ── Animate vehicle along route ───────────────────────────────────────

  void _startVehicleAnimation() {
    _moveTimer?.cancel();
    // Move every 300ms, skip 2-3 points at a time for smooth but visible movement
    _moveTimer = Timer.periodic(const Duration(milliseconds: 300), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (_vehicleIdx >= _routePoints.length - 1) {
        timer.cancel();
        setState(() => _statusText = 'ARRIVED AT DESTINATION ✓');
        return;
      }

      final step = _routePoints.length > 200 ? 3 : (_routePoints.length > 80 ? 2 : 1);
      _vehicleIdx = min(_vehicleIdx + step, _routePoints.length - 1);

      setState(() {
        _vehiclePos = _routePoints[_vehicleIdx];
        final progress = _vehicleIdx / _routePoints.length;
        _etaMin = _routeDurMin * (1.0 - progress);
      });

      // Follow the vehicle on map
      _map.move(_routePoints[_vehicleIdx], _map.camera.zoom);

      // Check if vehicle hit the blockage zone
      if (_hasBlockage && _blockagePoint != null && !_rerouted) {
        final dist = const Distance().as(
            LengthUnit.Meter, _routePoints[_vehicleIdx], _blockagePoint!);
        if (dist < 300) {
          // Auto-reroute
          _moveTimer?.cancel();
          _triggerReroute();
        }
      }
    });
  }

  // ── Simulate blockage ─────────────────────────────────────────────────

  void _simulateBlockage() {
    if (_routePoints.isEmpty || _hasBlockage) return;

    // Place blockage at ~40% ahead of current vehicle position
    final blockIdx =
        min(_vehicleIdx + (_routePoints.length * 0.3).toInt(), _routePoints.length - 1);
    setState(() {
      _blockagePoint = _routePoints[blockIdx];
      _hasBlockage = true;
      _statusText = '⚠ BLOCKAGE DETECTED AHEAD — preparing reroute...';
      _reliability = max(0.4, _reliability - 0.15);
    });
  }

  void _triggerReroute() {
    if (_vehiclePos == null) return;
    setState(() => _isRerouting = true);

    // Delay to show the "rerouting" animation
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted) {
        _fetchRoute(_vehiclePos!, widget.destCoord,
            isReroute: true, avoid: _blockagePoint);
      }
    });
  }

  // ── BUILD ──────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(children: [
        // ── MAP ──
        FlutterMap(
          mapController: _map,
          options: MapOptions(
            initialCenter: widget.originCoord,
            initialZoom: 13.5,
            interactionOptions:
                const InteractionOptions(flags: InteractiveFlag.all),
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.rescueconnect.app',
              tileBuilder: (ctx, widget, tile) => ColorFiltered(
                colorFilter: const ColorFilter.matrix(_darkMatrix),
                child: widget,
              ),
            ),
            // Original route (ghost) if rerouted
            if (_rerouted && _originalRoute.isNotEmpty)
              PolylineLayer(polylines: [
                Polyline(
                  points: _originalRoute,
                  strokeWidth: 3,
                  color: Colors.redAccent.withOpacity(0.2),
                  isDotted: true,
                ),
              ]),
            // Main route glow
            if (_routePoints.isNotEmpty)
              PolylineLayer(polylines: [
                Polyline(
                  points: _routePoints,
                  strokeWidth: 12,
                  color: (_rerouted ? kAiCyan : kEmergencyOrange)
                      .withOpacity(0.15),
                ),
              ]),
            // Main route
            if (_routePoints.isNotEmpty)
              PolylineLayer(polylines: [
                Polyline(
                  points: _routePoints,
                  strokeWidth: 5,
                  color: _rerouted ? kAiCyan : kEmergencyOrange,
                ),
              ]),
            // Traversed path (green)
            if (_vehicleIdx > 1)
              PolylineLayer(polylines: [
                Polyline(
                  points: _routePoints.sublist(0, _vehicleIdx + 1),
                  strokeWidth: 5,
                  color: kSuccess,
                ),
              ]),
            // Markers
            MarkerLayer(markers: [
              // Origin
              Marker(
                point: widget.originCoord,
                width: 40,
                height: 40,
                child: Container(
                  decoration: BoxDecoration(
                    color: kAiCyan,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                          color: kAiCyan.withOpacity(0.5), blurRadius: 12)
                    ],
                  ),
                  child: const Icon(Icons.emergency, color: Colors.black, size: 20),
                ),
              ),
              // Destination
              Marker(
                point: widget.destCoord,
                width: 40,
                height: 40,
                child: Container(
                  decoration: BoxDecoration(
                    color: kDanger,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                          color: kDanger.withOpacity(0.5), blurRadius: 12)
                    ],
                  ),
                  child: const Icon(Icons.local_hospital,
                      color: Colors.white, size: 20),
                ),
              ),
              // Vehicle
              if (_vehiclePos != null)
                Marker(
                  point: _vehiclePos!,
                  width: 48,
                  height: 48,
                  child: AnimatedBuilder(
                    animation: _pulseCtrl,
                    builder: (_, __) => Container(
                      decoration: BoxDecoration(
                        color: kEmergencyOrange,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: kEmergencyOrange
                                .withOpacity(0.4 + 0.4 * _pulseCtrl.value),
                            blurRadius: 18,
                            spreadRadius: 2,
                          )
                        ],
                      ),
                      child: const Icon(Icons.local_shipping,
                          color: Colors.white, size: 24),
                    ),
                  ),
                ),
              // Blockage (legacy, from simulation)
              if (_hasBlockage && _blockagePoint != null)
                Marker(
                  point: _blockagePoint!,
                  width: 44,
                  height: 44,
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.red,
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 2),
                      boxShadow: [
                        BoxShadow(
                            color: Colors.red.withOpacity(0.6),
                            blurRadius: 14)
                      ],
                    ),
                    child: const Icon(Icons.block,
                        color: Colors.white, size: 22),
                  ),
                ),
              // Active blockages from backend
              ..._activeBlockages.map((blockage) {
                final lat = (blockage['lat'] ?? 22.74).toDouble();
                final lon = (blockage['lon'] ?? 75.89).toDouble();
                final severity = (blockage['severity'] ?? 0.5).toDouble();
                final bType = blockage['type'] ?? 'blockage';
                
                return Marker(
                  point: LatLng(lat, lon),
                  width: 44,
                  height: 44,
                  child: Tooltip(
                    message: blockage['description'] ?? 'Traffic blockage',
                    child: AnimatedBuilder(
                      animation: _pulseCtrl,
                      builder: (_, __) => Container(
                        decoration: BoxDecoration(
                          color: Color.lerp(
                            Colors.red,
                            Colors.orange,
                            severity,
                          ),
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: Colors.white,
                            width: (2.0 + (severity * _pulseCtrl.value)).toDouble(),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.red.withOpacity(0.4 + 0.3 * _pulseCtrl.value),
                              blurRadius: (12.0 + (4 * _pulseCtrl.value)).toDouble(),
                            )
                          ],
                        ),
                        child: Icon(
                          bType == 'accident' ? Icons.car_crash :
                          bType == 'congestion' ? Icons.traffic :
                          bType == 'roadwork' ? Icons.construction :
                          Icons.warning,
                          color: Colors.white,
                          size: 20,
                        ),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ]),
          ],
        ),

        // ── TOP BAR ──
        Positioned(
          top: 0,
          left: 0,
          right: 0,
          child: SafeArea(
            child: Container(
              margin: const EdgeInsets.all(12),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.85),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: kCardBorder),
              ),
              child: Row(children: [
                GestureDetector(
                  onTap: () => Navigator.pop(context),
                  child: const Icon(Icons.arrow_back, color: Colors.white, size: 20),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.isDriver
                              ? 'NAVIGATION ACTIVE'
                              : 'LIVE VEHICLE TRACKING',
                          style: GoogleFonts.rajdhani(
                              color: kEmergencyOrange,
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 1),
                        ),
                        Text(
                          '${widget.origin} → ${widget.destination}',
                          style: GoogleFonts.rajdhani(
                              color: Colors.white70, fontSize: 11),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ]),
                ),
                // AI Status
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: kAiCyan.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: kAiCyan.withOpacity(0.4)),
                  ),
                  child: Text('AI ROUTING',
                      style: GoogleFonts.rajdhani(
                          color: kAiCyan,
                          fontSize: 9,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1)),
                ),
              ]),
            ),
          ),
        ),

        // ── BOTTOM PANEL ──
        Positioned(
          bottom: 0,
          left: 0,
          right: 0,
          child: _buildBottomPanel(),
        ),

        // ── LOADING OVERLAY ──
        if (_loading)
          Container(
            color: Colors.black.withOpacity(0.7),
            child: Center(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                const SizedBox(
                  width: 48,
                  height: 48,
                  child: CircularProgressIndicator(
                      color: kEmergencyOrange, strokeWidth: 3),
                ),
                const SizedBox(height: 16),
                Text(_statusText,
                    style: GoogleFonts.rajdhani(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                Text(_isRerouting ? 'Recalculating with LSTM-GCN model...' : 'OSRM + AI congestion model',
                    style: GoogleFonts.rajdhani(
                        color: kAiCyan, fontSize: 12)),
              ]),
            ),
          ),

        // ── REROUTING BANNER ──
        if (_isRerouting && !_loading)
          Positioned(
            top: 100,
            left: 20,
            right: 20,
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.redAccent.withOpacity(0.9),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Row(children: [
                const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                        color: Colors.white, strokeWidth: 2)),
                const SizedBox(width: 12),
                Expanded(
                  child: Text('REROUTING — AI analyzing alternate paths...',
                      style: GoogleFonts.rajdhani(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.5)),
                ),
              ]),
            ),
          ),
      ]),
    );
  }

  // ── BOTTOM PANEL ──────────────────────────────────────────────────────

  Widget _buildBottomPanel() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0D0D0D),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border.all(color: kCardBorder),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withOpacity(0.8),
              blurRadius: 20,
              offset: const Offset(0, -4))
        ],
      ),
      child: SafeArea(
        top: false,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          // Handle
          Center(
            child: Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                  color: Colors.grey[800],
                  borderRadius: BorderRadius.circular(2)),
            ),
          ),

          // Status bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: _rerouted
                  ? kAiCyan.withOpacity(0.08)
                  : _hasBlockage
                      ? kDanger.withOpacity(0.08)
                      : kSuccess.withOpacity(0.08),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                  color: _rerouted
                      ? kAiCyan.withOpacity(0.3)
                      : _hasBlockage
                          ? kDanger.withOpacity(0.3)
                          : kSuccess.withOpacity(0.3)),
            ),
            child: Row(children: [
              Icon(
                _rerouted
                    ? Icons.alt_route
                    : _hasBlockage
                        ? Icons.warning_amber
                        : Icons.navigation,
                color: _rerouted
                    ? kAiCyan
                    : _hasBlockage
                        ? kDanger
                        : kSuccess,
                size: 16,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _statusText,
                  style: GoogleFonts.rajdhani(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.bold),
                ),
              ),
              if (_rerouteCount > 0)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: kAiCyan.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text('$_rerouteCount reroute${_rerouteCount > 1 ? 's' : ''}',
                      style: GoogleFonts.rajdhani(
                          color: kAiCyan,
                          fontSize: 9,
                          fontWeight: FontWeight.bold)),
                ),
            ]),
          ),

          const SizedBox(height: 12),

          // Metrics row
          Row(children: [
            _MetricTile(
                icon: Icons.timer,
                label: 'ETA',
                value: _etaMin > 0
                    ? '${_etaMin.toStringAsFixed(0)} min'
                    : '--',
                color: kEmergencyOrange),
            const SizedBox(width: 8),
            _MetricTile(
                icon: Icons.straighten,
                label: 'DISTANCE',
                value: '${_routeDistKm.toStringAsFixed(1)} km',
                color: kAiCyan),
            const SizedBox(width: 8),
            _MetricTile(
                icon: Icons.verified,
                label: 'RELIABILITY',
                value: '${(_reliability * 100).toInt()}%',
                color: _reliability > 0.7 ? kSuccess : kWarning),
          ]),

          const SizedBox(height: 12),

          // Action buttons
          Row(children: [
            Expanded(
              child: ElevatedButton.icon(
                onPressed: _hasBlockage ? null : _simulateBlockage,
                icon: const Icon(Icons.report_problem, size: 18),
                label: Text(_hasBlockage ? 'BLOCKAGE ACTIVE' : 'SIMULATE BLOCKAGE',
                    style: GoogleFonts.rajdhani(
                        fontWeight: FontWeight.bold, letterSpacing: 0.5)),
                style: ElevatedButton.styleFrom(
                  backgroundColor:
                      _hasBlockage ? Colors.grey[800] : kDanger,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: ElevatedButton.icon(
                onPressed:
                    (_hasBlockage && !_rerouted) ? _triggerReroute : null,
                icon: const Icon(Icons.alt_route, size: 18),
                label: Text(_rerouted ? 'REROUTED ✓' : 'REROUTE NOW',
                    style: GoogleFonts.rajdhani(
                        fontWeight: FontWeight.bold, letterSpacing: 0.5)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: _rerouted
                      ? kSuccess.withOpacity(0.2)
                      : kAiCyan,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
          ]),
        ]),
      ),
    );
  }
}

// ── Metric tile ──────────────────────────────────────────────────────────

class _MetricTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _MetricTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        decoration: BoxDecoration(
          color: color.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.2)),
        ),
        child: Column(children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(height: 4),
          Text(value,
              style: GoogleFonts.rajdhani(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold)),
          Text(label,
              style: GoogleFonts.rajdhani(
                  color: color, fontSize: 9, letterSpacing: 0.5)),
        ]),
      ),
    );
  }
}
