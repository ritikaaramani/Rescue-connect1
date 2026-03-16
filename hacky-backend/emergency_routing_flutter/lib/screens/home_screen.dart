import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';

import '../config/cities_config.dart';
import '../config/theme.dart';
import '../models/route_model.dart';
import '../models/prediction_response.dart';
import '../providers/health_provider.dart';
import '../providers/prediction_provider.dart';
import '../services/routing_service.dart';
import 'navigation_screen.dart';

// ── Home phases ────────────────────────────────────────────────────────────

enum _Phase { idle, searching, routing, results, navigating }

// ── Dark map tile filter ───────────────────────────────────────────────────

const _darkMatrix = <double>[
  -1, 0, 0, 0, 255,
  0, -1, 0, 0, 255,
  0, 0, -1, 0, 255,
  0, 0, 0, 1, 0,
];

// ── Home Screen ────────────────────────────────────────────────────────────

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen>
    with TickerProviderStateMixin {
  // Map
  final _mapCtrl = MapController();

  // State
  _Phase _phase = _Phase.idle;
  EmergencyType _emergencyType = EmergencyType.ambulance;
  CityConfig _city = kCities[0];

  // Route result
  RouteResult? _result;

  // Locations
  LatLng? _originCoord;
  LatLng? _destCoord;

  // Text controllers
  final _originCtrl = TextEditingController();
  final _destCtrl = TextEditingController();
  final _originFocus = FocusNode();
  final _destFocus = FocusNode();

  // Autocomplete
  List<Map<String, dynamic>> _suggestions = [];
  bool _showSuggestions = false;
  bool _focusingOrigin = false;

  // Loading
  bool _isRouting = false;
  String _loadingMessage = 'Analyzing route...';

  // Services
  final _routingService = RoutingService();

  // Animation controllers
  late AnimationController _pulseCtrl;
  late AnimationController _vehicleCtrl;
  late AnimationController _panelCtrl;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
        vsync: this, duration: const Duration(seconds: 2))
      ..repeat(reverse: true);
    _vehicleCtrl = AnimationController(
        vsync: this, duration: const Duration(seconds: 4))
      ..repeat();
    _panelCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 400));

    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(healthStateProvider.notifier).fetch();
    });
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    _vehicleCtrl.dispose();
    _panelCtrl.dispose();
    _originCtrl.dispose();
    _destCtrl.dispose();
    _originFocus.dispose();
    _destFocus.dispose();
    super.dispose();
  }

  // ── Input handling ─────────────────────────────────────────────────────────

  void _onInputChanged(String value, bool isOrigin) async {
    _focusingOrigin = isOrigin;
    if (value.length < 3) {
      setState(() => _showSuggestions = false);
      return;
    }
    final results = await _routingService.autocomplete(value);
    if (mounted) {
      setState(() {
        _suggestions = results;
        _showSuggestions = results.isNotEmpty;
      });
    }
  }

  void _onSuggestionTap(Map<String, dynamic> suggestion) {
    final coord = LatLng(suggestion['lat'], suggestion['lon']);
    final display = (suggestion['display'] as String).split(',').take(2).join(',').trim();
    setState(() {
      _showSuggestions = false;
      if (_focusingOrigin) {
        _originCtrl.text = display;
        _originCoord = coord;
      } else {
        _destCtrl.text = display;
        _destCoord = coord;
      }
    });
  }

  // ── City change ────────────────────────────────────────────────────────────

  void _onCityChanged(CityConfig city) {
    setState(() {
      _city = city;
      _mapCtrl.move(LatLng(city.lat, city.lng), 13.0);
    });
  }

  // ── Routing flow ───────────────────────────────────────────────────────────

  Future<void> _analyzeRoute() async {
    FocusScope.of(context).unfocus();
    setState(() => _showSuggestions = false);

    // Geocode if needed
    LatLng? origin = _originCoord;
    LatLng? dest = _destCoord;

    if (origin == null && _originCtrl.text.trim().isNotEmpty) {
      origin = await _routingService.geocode(_originCtrl.text.trim());
    }
    if (dest == null && _destCtrl.text.trim().isNotEmpty) {
      dest = await _routingService.geocode(_destCtrl.text.trim());
    }

    if (origin == null || dest == null) {
      _snack('Could not locate one or both addresses. Please be more specific.',
          error: true);
      return;
    }

    setState(() {
      _isRouting = true;
      _phase = _Phase.routing;
      _loadingMessage = 'Fetching live route via OSRM...';
      _originCoord = origin;
      _destCoord = dest;
    });

    try {
      // Nearest city detection
      final city = _routingService.nearestCity(origin);
      setState(() {
        _city = city;
        _loadingMessage = 'Running LSTM+GCN traffic model for ${city.name}...';
      });

      // Fetch AI prediction
      PredictionResponse? aiPrediction;
      try {
        final svc = ref.read(model1ServiceProvider);
        aiPrediction = await svc.predictForCity(city);
      } catch (e) {
        debugPrint('AI prediction failed: $e');
      }

      setState(
          () => _loadingMessage = 'Applying India-specific factors...');

      // Full route analysis
      final result = await _routingService.analyzeRoute(
        origin: origin!,
        destination: dest!,
        emergencyType: _emergencyType,
        city: city,
        aiPrediction: aiPrediction,
      );

      if (!mounted) return;
      setState(() {
        _result = result;
        _phase = _Phase.results;
        _isRouting = false;
      });

      // Move map to show route
      _mapCtrl.move(origin, 12.0);

      // Update prediction in provider
      if (aiPrediction != null) {
        ref.read(predictionsProvider.notifier).setBatch([aiPrediction]);
      }
    } catch (e) {
      setState(() {
        _phase = _Phase.searching;
        _isRouting = false;
      });
      _snack(e.toString().replaceAll('Exception: ', ''), error: true);
    }
  }

  void _onDispatch() {
    final result = _result;
    if (result == null) return;

    HapticFeedback.heavyImpact();

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => NavigationScreen(
          route: result,
          origin: _originCtrl.text,
          destination: _destCtrl.text,
        ),
      ),
    );
  }

  void _resetToIdle() {
    setState(() {
      _phase = _Phase.idle;
      _result = null;
      _originCoord = null;
      _destCoord = null;
      _originCtrl.clear();
      _destCtrl.clear();
    });
    _mapCtrl.move(LatLng(_city.lat, _city.lng), 13.0);
  }

  void _snack(String msg, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg,
          style: GoogleFonts.rajdhani(
              color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600)),
      backgroundColor: error ? kDanger : kSuccess,
      behavior: SnackBarBehavior.floating,
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 90),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ));
  }

  // ── BUILD ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final health = ref.watch(healthStateProvider);
    final aiOnline = health?.status == 'ok';
    final result = _result;

    return Scaffold(
      backgroundColor: Colors.black,
      extendBodyBehindAppBar: true,
      resizeToAvoidBottomInset: false,
      body: Stack(children: [
        // ── MAP ──────────────────────────────────────────────────────────────
        _buildMap(result),

        // ── GRADIENT OVERLAY (bottom fade into panel) ─────────────────────
        Positioned(
          bottom: 0,
          left: 0,
          right: 0,
          height: 280,
          child: IgnorePointer(
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Colors.transparent,
                    Colors.black.withOpacity(0.85),
                  ],
                ),
              ),
            ),
          ),
        ),

        // ── TOP BAR ──────────────────────────────────────────────────────
        _buildTopBar(aiOnline),

        // ── BOTTOM PANEL ──────────────────────────────────────────────────
        Positioned(
          bottom: 0,
          left: 0,
          right: 0,
          child: _buildBottomPanel(result),
        ),

        // ── LOADING OVERLAY ───────────────────────────────────────────────
        if (_isRouting) _buildLoadingOverlay(),

        // ── AUTOCOMPLETE OVERLAY ──────────────────────────────────────────
        if (_showSuggestions) _buildSuggestions(),
      ]),
    );
  }

  // ── Map layer ──────────────────────────────────────────────────────────────

  Widget _buildMap(RouteResult? result) {
    final Color routeColor = result?.emergencyType.color ?? kEmergencyOrange;

    return FlutterMap(
      mapController: _mapCtrl,
      options: MapOptions(
        initialCenter: LatLng(_city.lat, _city.lng),
        initialZoom: 13.0,
        interactionOptions:
            const InteractionOptions(flags: InteractiveFlag.all),
      ),
      children: [
        // Dark map tiles
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.swiftemergency.app',
          tileBuilder: (ctx, widget, tile) => ColorFiltered(
            colorFilter: const ColorFilter.matrix(_darkMatrix),
            child: widget,
          ),
        ),

        // Route glow
        if (result != null && result.polyline.isNotEmpty)
          PolylineLayer(polylines: [
            Polyline(
              points: result.polyline,
              strokeWidth: 18,
              color: routeColor.withOpacity(0.15),
            ),
          ]),

        // Route line
        if (result != null && result.polyline.isNotEmpty)
          PolylineLayer(polylines: [
            Polyline(
              points: result.polyline,
              strokeWidth: 5.5,
              color: routeColor,
              strokeCap: StrokeCap.round,
            ),
          ]),

        // Markers
        MarkerLayer(markers: [
          // Origin marker
          if (_originCoord != null)
            Marker(
              point: _originCoord!,
              width: 48,
              height: 48,
              child: _buildOriginMarker(),
            ),
          // Destination marker
          if (_destCoord != null)
            Marker(
              point: _destCoord!,
              width: 48,
              height: 48,
              child: _buildDestinationMarker(result?.emergencyType),
            ),
          // Animated vehicle along route
          if (result != null && result.polyline.length > 5)
            Marker(
              point: _getVehiclePosition(result.polyline),
              width: 40,
              height: 40,
              child: _buildVehicleMarker(result.emergencyType),
            ),
        ]),
      ],
    );
  }

  LatLng _getVehiclePosition(List<LatLng> polyline) {
    final progress = _vehicleCtrl.value;
    final idx = ((polyline.length - 1) * progress * 0.4).floor();
    return polyline[idx.clamp(0, polyline.length - 1)];
  }

  Widget _buildOriginMarker() {
    return AnimatedBuilder(
      animation: _pulseCtrl,
      builder: (_, __) => Container(
        decoration: BoxDecoration(
          color: kAiCyan,
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: kAiCyan.withOpacity(0.25 + 0.35 * _pulseCtrl.value),
              blurRadius: 18,
              spreadRadius: 3,
            ),
          ],
        ),
        child: const Icon(Icons.my_location, color: Colors.black, size: 22),
      ),
    );
  }

  Widget _buildDestinationMarker(EmergencyType? type) {
    final color = type?.color ?? kDanger;
    return Container(
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        boxShadow: [BoxShadow(color: color.withOpacity(0.55), blurRadius: 16)],
      ),
      child: Icon(type?.icon ?? Icons.location_on,
          color: Colors.white, size: 22),
    );
  }

  Widget _buildVehicleMarker(EmergencyType type) {
    return AnimatedBuilder(
      animation: _vehicleCtrl,
      builder: (_, __) {
        final glow = 0.4 + 0.6 * math.sin(_vehicleCtrl.value * 2 * math.pi);
        return Container(
          decoration: BoxDecoration(
            color: Colors.white,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: type.color.withOpacity(glow * 0.7),
                blurRadius: 20,
                spreadRadius: 4,
              ),
            ],
          ),
          child: Icon(type.icon, color: type.color, size: 20),
        );
      },
    );
  }

  // ── Top bar ────────────────────────────────────────────────────────────────

  Widget _buildTopBar(bool aiOnline) {
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Row(children: [
            // Brand
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.88),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: kEmergencyOrange.withOpacity(0.5)),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.emergency_share, color: kEmergencyOrange, size: 16),
                const SizedBox(width: 7),
                Text('SWIFT',
                    style: GoogleFonts.rajdhani(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 2)),
              ]),
            ),

            const Spacer(),

            // AI status
            _AiStatusBadge(online: aiOnline, ctrl: _pulseCtrl),
            const SizedBox(width: 8),

            // My location button
            _MapButton(
              icon: Icons.my_location,
              onTap: () => _mapCtrl.move(LatLng(_city.lat, _city.lng), 13.5),
            ),
          ]),
        ),
      ),
    );
  }

  // ── Bottom panel ───────────────────────────────────────────────────────────

  Widget _buildBottomPanel(RouteResult? result) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0C0C0C),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        border: Border.all(color: kCardBorder),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.9),
            blurRadius: 30,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SingleChildScrollView(
        physics: const BouncingScrollPhysics(),
        child: Padding(
          padding: EdgeInsets.only(
              bottom: MediaQuery.of(context).viewInsets.bottom + 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Drag handle
              Center(
                child: Container(
                  margin: const EdgeInsets.only(top: 12, bottom: 8),
                  width: 42,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey[800],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              if (_phase == _Phase.idle) ..._buildIdleContent(),
              if (_phase == _Phase.searching ||
                  _phase == _Phase.routing) ..._buildSearchContent(),
              if (_phase == _Phase.results && result != null)
                ..._buildResultsContent(result),
            ],
          ),
        ),
      ),
    );
  }

  // ── IDLE content ───────────────────────────────────────────────────────────

  List<Widget> _buildIdleContent() => [
        // Header
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Where to respond?',
                  style: GoogleFonts.rajdhani(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w800)),
              const SizedBox(height: 2),
              Text('AI-powered emergency routing for India',
                  style: GoogleFonts.rajdhani(
                      color: kTextSecondary, fontSize: 13)),
            ],
          ),
        ),

        const SizedBox(height: 16),

        // Emergency type selector
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: _EmergencyTypeRow(
            selected: _emergencyType,
            onChanged: (t) => setState(() => _emergencyType = t),
          ),
        ),

        const SizedBox(height: 14),

        // City selector
        _CityRow(selected: _city, onChanged: _onCityChanged),

        const SizedBox(height: 16),

        // "Enter Destination" button (like Uber's "Where to?")
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: GestureDetector(
            onTap: () => setState(() => _phase = _Phase.searching),
            child: Container(
              height: 56,
              decoration: BoxDecoration(
                color: const Color(0xFF181818),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: _emergencyType.color.withOpacity(0.4)),
              ),
              child: Row(children: [
                const SizedBox(width: 16),
                Icon(Icons.search, color: _emergencyType.color, size: 22),
                const SizedBox(width: 12),
                Text(
                  'Enter incident location...',
                  style: GoogleFonts.rajdhani(
                      color: Colors.grey[600], fontSize: 16),
                ),
              ]),
            ),
          ).animate().fadeIn(duration: 300.ms),
        ),

        const SizedBox(height: 14),

        // India context quick indicator
        _IndiaContextRow(),
      ];

  // ── SEARCH content ─────────────────────────────────────────────────────────

  List<Widget> _buildSearchContent() => [
        // Header with back
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 20, 0),
          child: Row(children: [
            IconButton(
              icon: const Icon(Icons.arrow_back, color: Colors.white, size: 20),
              onPressed: _resetToIdle,
            ),
            const SizedBox(width: 4),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Plan Emergency Route',
                      style: GoogleFonts.rajdhani(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w800)),
                  Text(
                    '${_emergencyType.label} · ${_city.name}',
                    style: GoogleFonts.rajdhani(
                        color: _emergencyType.color, fontSize: 12),
                  ),
                ],
              ),
            ),
            // Emergency type mini chip
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: _emergencyType.color.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                    color: _emergencyType.color.withOpacity(0.45)),
              ),
              child: Icon(_emergencyType.icon,
                  color: _emergencyType.color, size: 16),
            ),
          ]),
        ),

        const SizedBox(height: 8),

        // Origin field
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(children: [
            _LocationField(
              controller: _originCtrl,
              focusNode: _originFocus,
              hint: 'Pickup / Station location',
              icon: Icons.radio_button_checked,
              iconColor: kAiCyan,
              accentColor: kAiCyan,
              onChanged: (v) => _onInputChanged(v, true),
            ),
            const SizedBox(height: 4),
            // Vertical dots connector
            Padding(
              padding: const EdgeInsets.only(left: 27),
              child: Column(children: List.generate(
                  3,
                  (i) => Container(
                        width: 2,
                        height: 5,
                        margin: const EdgeInsets.symmetric(vertical: 1.5),
                        color: Colors.grey[800],
                      ))),
            ),
            const SizedBox(height: 4),
            _LocationField(
              controller: _destCtrl,
              focusNode: _destFocus,
              hint: 'Incident / Destination address',
              icon: Icons.location_on,
              iconColor: _emergencyType.color,
              accentColor: _emergencyType.color,
              onChanged: (v) => _onInputChanged(v, false),
            ),
          ]),
        ),

        const SizedBox(height: 16),

        // Emergency type row (compact)
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: _EmergencyTypeRow(
            selected: _emergencyType,
            onChanged: (t) => setState(() => _emergencyType = t),
            compact: true,
          ),
        ),

        const SizedBox(height: 16),

        // Analyze button
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: _AnalyzeButton(
            emergencyType: _emergencyType,
            onTap: _analyzeRoute,
          ),
        ),
      ];

  // ── RESULTS content ────────────────────────────────────────────────────────

  List<Widget> _buildResultsContent(RouteResult result) => [
        // Header with back + type
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 20, 0),
          child: Row(children: [
            IconButton(
              icon: const Icon(Icons.arrow_back, color: Colors.white, size: 20),
              onPressed: () => setState(() {
                _phase = _Phase.searching;
                _result = null;
              }),
            ),
            const SizedBox(width: 2),
            Icon(result.emergencyType.icon,
                color: result.emergencyType.color, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Route Optimized',
                      style: GoogleFonts.rajdhani(
                          color: Colors.white,
                          fontSize: 17,
                          fontWeight: FontWeight.w800)),
                  Text(
                    '${result.emergencyType.label} · ${result.cityName}',
                    style: GoogleFonts.rajdhani(
                        color: result.emergencyType.color, fontSize: 12),
                  ),
                ],
              ),
            ),
            // Confidence badge
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: kAiCyan.withOpacity(0.12),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: kAiCyan.withOpacity(0.3)),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.psychology, color: kAiCyan, size: 11),
                const SizedBox(width: 4),
                Text('${result.confidencePct}%',
                    style: GoogleFonts.rajdhani(
                        color: kAiCyan,
                        fontSize: 11,
                        fontWeight: FontWeight.bold)),
              ]),
            ),
          ]),
        ),

        const SizedBox(height: 6),

        // ETA COMPARISON CARD — the hero element
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: _EtaComparisonCard(result: result),
        )
            .animate()
            .slideY(begin: 0.3, end: 0, duration: 350.ms, curve: Curves.easeOut)
            .fadeIn(duration: 280.ms),

        // India factors
        if (result.indiaFactors.hasFactors) ...[
          const SizedBox(height: 10),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: _IndiaFactorsCard(factors: result.indiaFactors),
          )
              .animate(delay: 100.ms)
              .slideY(begin: 0.2, end: 0, duration: 300.ms)
              .fadeIn(duration: 250.ms),
        ],

        const SizedBox(height: 10),

        // Congestion forecast
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: _CongestionForecastBar(result: result),
        )
            .animate(delay: 200.ms)
            .fadeIn(duration: 300.ms),

        const SizedBox(height: 16),

        // DISPATCH button
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: _DispatchButton(
            emergencyType: result.emergencyType,
            etaMin: result.aiEtaMin,
            onDispatch: _onDispatch,
          ),
        )
            .animate(delay: 250.ms)
            .slideY(begin: 0.2, end: 0, duration: 300.ms)
            .fadeIn(duration: 280.ms),
      ];

  // ── Loading overlay ─────────────────────────────────────────────────────────

  Widget _buildLoadingOverlay() {
    return Container(
      color: Colors.black.withOpacity(0.72),
      child: Center(
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 40),
          padding: const EdgeInsets.all(28),
          decoration: BoxDecoration(
            color: const Color(0xFF0D0D0D),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: kAiCyan.withOpacity(0.35)),
          ),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            // Pulsing AI brain icon
            AnimatedBuilder(
              animation: _pulseCtrl,
              builder: (_, __) => Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: kAiCyan.withOpacity(0.08 + 0.08 * _pulseCtrl.value),
                  border: Border.all(
                      color: kAiCyan.withOpacity(0.4 + 0.4 * _pulseCtrl.value),
                      width: 1.5),
                ),
                child: const Icon(Icons.psychology_alt, color: kAiCyan, size: 32),
              ),
            ),
            const SizedBox(height: 20),
            Text('AI Analyzing',
                style: GoogleFonts.rajdhani(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1)),
            const SizedBox(height: 8),
            Text(_loadingMessage,
                textAlign: TextAlign.center,
                style: GoogleFonts.rajdhani(
                    color: kAiCyan, fontSize: 13, letterSpacing: 0.3)),
            const SizedBox(height: 20),
            SizedBox(
              width: 180,
              child: LinearProgressIndicator(
                backgroundColor: kCardBorder,
                valueColor: const AlwaysStoppedAnimation(kAiCyan),
                minHeight: 2,
              ),
            ),
            const SizedBox(height: 12),
            Text('LSTM + GCN Spatiotemporal Model',
                style: GoogleFonts.rajdhani(
                    color: kTextSecondary, fontSize: 11, letterSpacing: 0.5)),
          ]),
        ),
      ),
    );
  }

  // ── Suggestions overlay ─────────────────────────────────────────────────────

  Widget _buildSuggestions() {
    return Positioned(
      bottom: 200,
      left: 20,
      right: 20,
      child: Container(
        constraints: const BoxConstraints(maxHeight: 240),
        decoration: BoxDecoration(
          color: const Color(0xFF141414),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: kCardBorder),
          boxShadow: [
            BoxShadow(
                color: Colors.black.withOpacity(0.7), blurRadius: 20)
          ],
        ),
        child: ListView.separated(
          shrinkWrap: true,
          padding: const EdgeInsets.symmetric(vertical: 6),
          itemCount: _suggestions.length,
          separatorBuilder: (_, __) =>
              Divider(height: 1, color: kCardBorder),
          itemBuilder: (ctx, i) {
            final s = _suggestions[i];
            final parts =
                (s['display'] as String).split(',');
            return ListTile(
              dense: true,
              leading:
                  const Icon(Icons.location_on, color: kTextSecondary, size: 18),
              title: Text(
                parts.first.trim(),
                style: GoogleFonts.rajdhani(
                    color: Colors.white, fontSize: 14),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              subtitle: Text(
                parts.skip(1).take(2).join(',').trim(),
                style: GoogleFonts.rajdhani(
                    color: kTextSecondary, fontSize: 11),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              onTap: () => _onSuggestionTap(s),
            );
          },
        ),
      ),
    );
  }
}

// ── Sub-widgets ─────────────────────────────────────────────────────────────

class _AiStatusBadge extends StatelessWidget {
  final bool online;
  final AnimationController ctrl;
  const _AiStatusBadge({required this.online, required this.ctrl});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: ctrl,
      builder: (_, __) {
        final pulse = online ? (0.5 + 0.5 * ctrl.value) : 1.0;
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
          decoration: BoxDecoration(
            color: Colors.black.withOpacity(0.88),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: online
                  ? kAiCyan.withOpacity(pulse)
                  : kDanger.withOpacity(0.5),
            ),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: 7,
              height: 7,
              decoration: BoxDecoration(
                color: online ? kAiCyan : kDanger,
                shape: BoxShape.circle,
                boxShadow: online
                    ? [BoxShadow(color: kAiCyan.withOpacity(pulse), blurRadius: 8)]
                    : null,
              ),
            ),
            const SizedBox(width: 6),
            Text(online ? 'AI ONLINE' : 'AI OFFLINE',
                style: GoogleFonts.rajdhani(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.2)),
          ]),
        );
      },
    );
  }
}

class _MapButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  const _MapButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.88),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: kCardBorder),
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }
}

// ── Emergency type row ─────────────────────────────────────────────────────

class _EmergencyTypeRow extends StatelessWidget {
  final EmergencyType selected;
  final ValueChanged<EmergencyType> onChanged;
  final bool compact;

  const _EmergencyTypeRow({
    required this.selected,
    required this.onChanged,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: compact ? 38 : 48,
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: EmergencyType.values.map((type) {
          final sel = type == selected;
          return GestureDetector(
            onTap: () => onChanged(type),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              margin: const EdgeInsets.only(right: 8),
              padding: EdgeInsets.symmetric(
                  horizontal: compact ? 10 : 12, vertical: compact ? 6 : 10),
              decoration: BoxDecoration(
                color: sel ? type.color : const Color(0xFF161616),
                borderRadius: BorderRadius.circular(compact ? 8 : 12),
                border: Border.all(
                  color: sel
                      ? type.color
                      : type.color.withOpacity(0.3),
                  width: sel ? 0 : 1,
                ),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(type.icon,
                    color: sel ? Colors.white : type.color,
                    size: compact ? 14 : 16),
                const SizedBox(width: 6),
                Text(type.label,
                    style: GoogleFonts.rajdhani(
                      color: sel ? Colors.white : kTextSecondary,
                      fontSize: compact ? 12 : 13,
                      fontWeight:
                          sel ? FontWeight.bold : FontWeight.w500,
                      letterSpacing: 0.3,
                    )),
              ]),
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ── City row ───────────────────────────────────────────────────────────────

class _CityRow extends StatelessWidget {
  final CityConfig selected;
  final ValueChanged<CityConfig> onChanged;

  const _CityRow({required this.selected, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 38,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        itemCount: kCities.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (ctx, i) {
          final city = kCities[i];
          final sel = city.name == selected.name;
          return GestureDetector(
            onTap: () => onChanged(city),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: sel ? kEmergencyOrange : const Color(0xFF161616),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: sel
                      ? kEmergencyOrange
                      : city.hasCityModel
                          ? kAiCyan.withOpacity(0.3)
                          : kCardBorder,
                ),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                if (city.hasCityModel)
                  Icon(Icons.bolt,
                      color: sel ? Colors.black : kAiCyan, size: 11),
                if (city.hasCityModel) const SizedBox(width: 2),
                Text(city.name,
                    style: GoogleFonts.rajdhani(
                      color: sel ? Colors.black : kTextSecondary,
                      fontSize: 12,
                      fontWeight:
                          sel ? FontWeight.bold : FontWeight.w500,
                    )),
              ]),
            ),
          );
        },
      ),
    );
  }
}

// ── India context quick row ────────────────────────────────────────────────

class _IndiaContextRow extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final hour = now.hour;
    final month = now.month;

    final items = <String>[];
    if (hour >= 7 && hour < 10 || hour >= 17 && hour < 21) {
      items.add('🕐 Rush Hour Active');
    }
    if (month >= 6 && month <= 9) items.add('🌧️ Monsoon Season');
    if (month >= 11 || month <= 2) items.add('💒 Wedding Season');
    if (month >= 4 && month <= 6) items.add('🏏 IPL Season');

    if (items.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 0),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          color: kWarning.withOpacity(0.06),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: kWarning.withOpacity(0.2)),
        ),
        child: Row(children: [
          const Icon(Icons.info_outline, color: kWarning, size: 14),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              items.join('  ·  '),
              style: GoogleFonts.rajdhani(
                  color: kWarning, fontSize: 12, letterSpacing: 0.2),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ]),
      ),
    );
  }
}

// ── Location text field ────────────────────────────────────────────────────

class _LocationField extends StatelessWidget {
  final TextEditingController controller;
  final FocusNode focusNode;
  final String hint;
  final IconData icon;
  final Color iconColor;
  final Color accentColor;
  final ValueChanged<String> onChanged;

  const _LocationField({
    required this.controller,
    required this.focusNode,
    required this.hint,
    required this.icon,
    required this.iconColor,
    required this.accentColor,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF161616),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accentColor.withOpacity(0.25)),
      ),
      child: TextField(
        controller: controller,
        focusNode: focusNode,
        style: GoogleFonts.rajdhani(color: Colors.white, fontSize: 15),
        onChanged: onChanged,
        decoration: InputDecoration(
          border: InputBorder.none,
          prefixIcon: Icon(icon, color: iconColor.withOpacity(0.9), size: 18),
          hintText: hint,
          hintStyle:
              GoogleFonts.rajdhani(color: Colors.grey[600], fontSize: 14),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
          suffixIcon: controller.text.isNotEmpty
              ? IconButton(
                  icon: const Icon(Icons.close,
                      color: kTextSecondary, size: 16),
                  onPressed: () => controller.clear(),
                )
              : null,
        ),
      ),
    );
  }
}

// ── Analyze button ─────────────────────────────────────────────────────────

class _AnalyzeButton extends StatelessWidget {
  final EmergencyType emergencyType;
  final VoidCallback onTap;

  const _AnalyzeButton({required this.emergencyType, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 56,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              emergencyType.color,
              emergencyType.color.withOpacity(0.75),
            ],
          ),
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: emergencyType.color.withOpacity(0.4),
              blurRadius: 18,
              offset: const Offset(0, 5),
            ),
          ],
        ),
        child: Center(
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(emergencyType.icon, color: Colors.white, size: 20),
            const SizedBox(width: 10),
            Text('FIND EMERGENCY ROUTE',
                style: GoogleFonts.rajdhani(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.5)),
          ]),
        ),
      ),
    );
  }
}

// ── ETA Comparison Card — HERO ELEMENT ────────────────────────────────────

class _EtaComparisonCard extends StatelessWidget {
  final RouteResult result;
  const _EtaComparisonCard({required this.result});

  @override
  Widget build(BuildContext context) {
    final saved = result.timeSavedMin;
    final isFaster = result.isFaster;

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF101010),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: result.emergencyType.color.withOpacity(0.3)),
        boxShadow: [
          BoxShadow(
            color: result.emergencyType.color.withOpacity(0.06),
            blurRadius: 24,
            spreadRadius: 2,
          ),
        ],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Title
        Row(children: [
          Icon(Icons.compare_arrows,
              color: result.emergencyType.color, size: 16),
          const SizedBox(width: 8),
          Text('ROUTE COMPARISON',
              style: GoogleFonts.rajdhani(
                  color: kTextSecondary,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.5)),
          const Spacer(),
          Text(result.distanceLabel,
              style: GoogleFonts.rajdhani(
                  color: kTextSecondary, fontSize: 12)),
        ]),

        const SizedBox(height: 16),

        // Side-by-side comparison
        Row(children: [
          // Standard (what generic apps show)
          Expanded(
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFF161616),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: kCardBorder),
              ),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      const Icon(Icons.navigation_outlined,
                          color: kTextSecondary, size: 13),
                      const SizedBox(width: 5),
                      Text('GENERIC APP',
                          style: GoogleFonts.rajdhani(
                              color: kTextSecondary,
                              fontSize: 9,
                              letterSpacing: 1.2)),
                    ]),
                    const SizedBox(height: 8),
                    Text(result.standardEtaLabel,
                        style: GoogleFonts.rajdhani(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 4),
                    Text('Est. arrival time',
                        style: GoogleFonts.rajdhani(
                            color: kTextSecondary, fontSize: 11)),
                    const SizedBox(height: 8),
                    // Warning: actual will be worse
                    if (result.indiaFactors.hasFactors)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: kWarning.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'Actual: ~${result.predictedActualEtaMin.toStringAsFixed(0)} min',
                          style: GoogleFonts.rajdhani(
                              color: kWarning, fontSize: 10),
                        ),
                      ),
                  ]),
            ),
          ),

          // Arrow
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Column(children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: isFaster
                      ? kSuccess.withOpacity(0.15)
                      : kDanger.withOpacity(0.15),
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: isFaster
                        ? kSuccess.withOpacity(0.5)
                        : kDanger.withOpacity(0.5),
                  ),
                ),
                child: Icon(
                  isFaster ? Icons.bolt : Icons.trending_up,
                  color: isFaster ? kSuccess : kDanger,
                  size: 16,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                isFaster
                    ? '${saved.abs().toStringAsFixed(0)}m\nsaved'
                    : '${saved.abs().toStringAsFixed(0)}m\nextra',
                textAlign: TextAlign.center,
                style: GoogleFonts.rajdhani(
                  color: isFaster ? kSuccess : kDanger,
                  fontSize: 9,
                  fontWeight: FontWeight.bold,
                  height: 1.2,
                ),
              ),
            ]),
          ),

          // AI Route
          Expanded(
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: result.emergencyType.color.withOpacity(0.08),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                    color: result.emergencyType.color.withOpacity(0.4)),
              ),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Icon(Icons.psychology,
                          color: result.emergencyType.color, size: 13),
                      const SizedBox(width: 5),
                      Text('SWIFT AI',
                          style: GoogleFonts.rajdhani(
                              color: result.emergencyType.color,
                              fontSize: 9,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 1.2)),
                    ]),
                    const SizedBox(height: 8),
                    Text(result.aiEtaLabel,
                        style: GoogleFonts.rajdhani(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 4),
                    Text('Priority route',
                        style: GoogleFonts.rajdhani(
                            color: kTextSecondary, fontSize: 11)),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: isFaster
                            ? kSuccess.withOpacity(0.1)
                            : kWarning.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        isFaster
                            ? '${saved.toStringAsFixed(0)} min faster'
                            : 'Most accurate',
                        style: GoogleFonts.rajdhani(
                          color: isFaster ? kSuccess : kWarning,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ]),
            ),
          ),
        ]),

        const SizedBox(height: 14),

        // Why our AI is better explanation
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: kAiCyan.withOpacity(0.05),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: kAiCyan.withOpacity(0.15)),
          ),
          child: Row(children: [
            const Icon(Icons.lightbulb_outline, color: kAiCyan, size: 13),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                _buildExplanation(result),
                style: GoogleFonts.rajdhani(
                    color: kTextSecondary, fontSize: 12, height: 1.3),
              ),
            ),
          ]),
        ),
      ]),
    );
  }

  String _buildExplanation(RouteResult r) {
    final parts = <String>[];
    if (r.congestionScore > 0.5) {
      parts.add('Heavy congestion detected ahead — AI found alternate route');
    } else if (r.congestionScore > 0.3) {
      parts.add('Moderate traffic — priority lane routing applied');
    } else {
      parts.add('Clear route predicted — minimal delays expected');
    }
    if (r.indiaFactors.active.isNotEmpty) {
      final f = r.indiaFactors.active.first;
      parts.add('${f.emoji} ${f.name} adds ~${((f.delayMultiplier - 1) * r.standardEtaMin).toStringAsFixed(0)} min delay bypassed');
    }
    return parts.join('. ');
  }
}

// ── India factors card ─────────────────────────────────────────────────────

class _IndiaFactorsCard extends StatelessWidget {
  final IndiaFactors factors;
  const _IndiaFactorsCard({required this.factors});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0E0E0E),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: kWarning.withOpacity(0.25)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.flag, color: kWarning, size: 13),
          const SizedBox(width: 6),
          Text('INDIA-SPECIFIC FACTORS DETECTED',
              style: GoogleFonts.rajdhani(
                  color: kWarning,
                  fontSize: 9,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.2)),
        ]),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 6,
          children: factors.active.map((f) {
            return Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: f.color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: f.color.withOpacity(0.35)),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text(f.emoji, style: const TextStyle(fontSize: 12)),
                const SizedBox(width: 5),
                Text(f.name,
                    style: GoogleFonts.rajdhani(
                        color: f.color,
                        fontSize: 11,
                        fontWeight: FontWeight.bold)),
                const SizedBox(width: 4),
                Text(
                  '+${((f.delayMultiplier - 1) * 100).toStringAsFixed(0)}%',
                  style: GoogleFonts.rajdhani(
                      color: f.color.withOpacity(0.7), fontSize: 10),
                ),
              ]),
            );
          }).toList(),
        ),
        const SizedBox(height: 8),
        Text(
          'Generic apps don\'t account for these factors. Our AI does.',
          style: GoogleFonts.rajdhani(
              color: kTextSecondary, fontSize: 11, fontStyle: FontStyle.italic),
        ),
      ]),
    );
  }
}

// ── Congestion forecast bar ────────────────────────────────────────────────

class _CongestionForecastBar extends StatelessWidget {
  final RouteResult result;
  const _CongestionForecastBar({required this.result});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF0E0E0E),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: result.congestionColor.withOpacity(0.3)),
      ),
      child: Row(children: [
        // Congestion dot
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: result.congestionColor,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                  color: result.congestionColor.withOpacity(0.6),
                  blurRadius: 8)
            ],
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${result.congestionLabel} Congestion — ${(result.congestionScore * 100).toStringAsFixed(0)}%',
                  style: GoogleFonts.rajdhani(
                      color: result.congestionColor,
                      fontSize: 13,
                      fontWeight: FontWeight.bold),
                ),
                Text('AI confidence: ${result.confidencePct}%  ·  LSTM+GCN model',
                    style: GoogleFonts.rajdhani(
                        color: kTextSecondary, fontSize: 11)),
              ]),
        ),
        const Icon(Icons.psychology, color: kAiCyan, size: 18),
      ]),
    );
  }
}

// ── Dispatch button ────────────────────────────────────────────────────────

class _DispatchButton extends StatelessWidget {
  final EmergencyType emergencyType;
  final double etaMin;
  final VoidCallback onDispatch;

  const _DispatchButton({
    required this.emergencyType,
    required this.etaMin,
    required this.onDispatch,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onDispatch,
      child: Container(
        height: 60,
        decoration: BoxDecoration(
          color: emergencyType.color,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: emergencyType.color.withOpacity(0.45),
              blurRadius: 22,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(emergencyType.icon, color: Colors.white, size: 22),
            const SizedBox(width: 12),
            Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('DISPATCH ${emergencyType.label.toUpperCase()}',
                    style: GoogleFonts.rajdhani(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.2)),
                Text('ETA: ${etaMin.toStringAsFixed(0)} min via AI route',
                    style: GoogleFonts.rajdhani(
                        color: Colors.white.withOpacity(0.8),
                        fontSize: 11)),
              ],
            ),
            const Spacer(),
            const Icon(Icons.arrow_forward_ios,
                color: Colors.white, size: 16),
            const SizedBox(width: 16),
          ],
        ),
      ),
    );
  }
}
