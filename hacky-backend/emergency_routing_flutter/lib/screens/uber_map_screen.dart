import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:latlong2/latlong.dart';
import 'package:dio/dio.dart';
import 'package:google_fonts/google_fonts.dart';
import '../config/theme.dart';
import '../config/cities_config.dart';
import '../models/prediction_response.dart';
import '../providers/prediction_provider.dart';
import '../providers/health_provider.dart';

class UberMapScreen extends ConsumerStatefulWidget {
  const UberMapScreen({super.key});

  @override
  ConsumerState<UberMapScreen> createState() => _UberMapScreenState();
}

class _UberMapScreenState extends ConsumerState<UberMapScreen>
    with TickerProviderStateMixin {
  final MapController _mapController = MapController();
  final TextEditingController _pickupController = TextEditingController();
  final TextEditingController _dropoffController = TextEditingController();
  final FocusNode _pickupFocus = FocusNode();
  final FocusNode _dropoffFocus = FocusNode();

  LatLng _mapCenter = const LatLng(28.6139, 77.2090);
  List<LatLng> _routePoints = [];
  LatLng? _pickupLocation;
  LatLng? _dropoffLocation;
  PredictionResponse? _prediction;
  CityConfig _selectedCity = kCities[0];
  bool _isLoading = false;
  bool _showPrediction = false;
  double _routeDistanceKm = 0;
  double _routeDurationMin = 0;
  bool _isExpanded = false; // bottom panel expand state

  final Dio _dio = Dio();

  late AnimationController _pulseCtrl;
  late AnimationController _glowCtrl;

  // Dark-mode map color matrix
  static const List<double> _darkMatrix = [
    -1, 0, 0, 0, 255,
    0, -1, 0, 0, 255,
    0, 0, -1, 0, 255,
    0, 0, 0, 1, 0,
  ];

  @override
  void initState() {
    super.initState();
    _pulseCtrl =
        AnimationController(vsync: this, duration: const Duration(seconds: 2))
          ..repeat(reverse: true);
    _glowCtrl =
        AnimationController(vsync: this, duration: const Duration(seconds: 3))
          ..repeat(reverse: true);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(healthStateProvider.notifier).fetch();
    });
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    _glowCtrl.dispose();
    _pickupController.dispose();
    _dropoffController.dispose();
    _pickupFocus.dispose();
    _dropoffFocus.dispose();
    super.dispose();
  }

  // ── Geocode via Nominatim ──────────────────────────────────────────────────

  Future<LatLng?> _geocode(String address) async {
    try {
      final res = await _dio.get(
        'https://nominatim.openstreetmap.org/search',
        queryParameters: {'q': address, 'format': 'json', 'limit': 1},
        options: Options(headers: {'User-Agent': 'EmergencyRoutingAI/1.0'}),
      );
      if (res.data is List && (res.data as List).isNotEmpty) {
        final r = res.data[0];
        return LatLng(double.parse(r['lat']), double.parse(r['lon']));
      }
    } catch (e) {
      debugPrint('Geocoding error: $e');
    }
    return null;
  }

  // ── Find nearest supported city from coordinates ───────────────────────────

  CityConfig _nearestCity(LatLng location) {
    const dist = Distance();
    CityConfig nearest = kCities[0];
    double minD = double.infinity;
    for (final c in kCities) {
      final d = dist(location, LatLng(c.lat, c.lng));
      if (d < minD) {
        minD = d;
        nearest = c;
      }
    }
    return nearest;
  }

  // ── Main search + predict flow ─────────────────────────────────────────────

  Future<void> _onAnalyzeRoute() async {
    FocusScope.of(context).unfocus();
    if (_pickupController.text.trim().isEmpty ||
        _dropoffController.text.trim().isEmpty) {
      _snack('Enter both pickup and destination', error: true);
      return;
    }

    setState(() {
      _isLoading = true;
      _showPrediction = false;
      _prediction = null;
      _routePoints = [];
    });

    try {
      final pickup = await _geocode(_pickupController.text);
      final dropoff = await _geocode(_dropoffController.text);
      if (pickup == null || dropoff == null) {
        throw Exception('Could not locate the entered addresses.');
      }

      // Route via OSRM
      final routeUrl =
          'http://router.project-osrm.org/route/v1/driving/'
          '${pickup.longitude},${pickup.latitude};'
          '${dropoff.longitude},${dropoff.latitude}'
          '?geometries=geojson&overview=full';
      final routeRes = await _dio.get(routeUrl);

      if (routeRes.data['code'] != 'Ok') {
        throw Exception('Routing engine could not find a route.');
      }

      final route = routeRes.data['routes'][0];
      final coords = route['geometry']['coordinates'] as List;
      final distKm = (route['distance'] as num) / 1000;
      final durMin = (route['duration'] as num) / 60;
      final detectedCity = _nearestCity(pickup);

      setState(() {
        _pickupLocation = pickup;
        _dropoffLocation = dropoff;
        _routePoints =
            coords.map((c) => LatLng(c[1] as double, c[0] as double)).toList();
        _mapCenter = pickup;
        _selectedCity = detectedCity;
        _routeDistanceKm = distKm;
        _routeDurationMin = durMin;
        _isExpanded = true;
      });

      _mapController.move(pickup, 12.5);

      // AI prediction (auto-routes to /predict or /predict/area)
      await _fetchAiPrediction(detectedCity);
    } catch (e) {
      _snack(e.toString().replaceAll('Exception: ', ''), error: true);
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _fetchAiPrediction(CityConfig city) async {
    try {
      final svc = ref.read(model1ServiceProvider);
      final pred = await svc.predictForCity(city);
      if (!mounted) return;
      setState(() {
        _prediction = pred;
        _showPrediction = true;
      });
    } catch (e) {
      debugPrint('AI prediction error: $e');
    }
  }

  void _snack(String msg, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg,
          style: GoogleFonts.rajdhani(
              color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600)),
      backgroundColor: error ? kDanger : kSuccess,
      behavior: SnackBarBehavior.floating,
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 80),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ));
  }

  Color get _congestionColor =>
      _prediction == null ? kAiCyan : getCongestionColor(_prediction!.congestionT5);

  // ── BUILD ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final health = ref.watch(healthStateProvider);
    final aiOnline = health?.status == 'ok';

    return Scaffold(
      backgroundColor: Colors.black,
      extendBodyBehindAppBar: true,
      body: Stack(children: [
        // ── MAP ──
        FlutterMap(
          mapController: _mapController,
          options: MapOptions(
            initialCenter: _mapCenter,
            initialZoom: 13.0,
            interactionOptions: const InteractionOptions(
              flags: InteractiveFlag.all,
            ),
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.emergencyrouting.app',
              tileBuilder: (context, widget, tile) => ColorFiltered(
                colorFilter: const ColorFilter.matrix(_darkMatrix),
                child: widget,
              ),
            ),
            // Glow shadow under route
            if (_routePoints.isNotEmpty)
              PolylineLayer(polylines: [
                Polyline(
                  points: _routePoints,
                  strokeWidth: 14,
                  color: _congestionColor.withOpacity(0.18),
                ),
              ]),
            // Main route
            if (_routePoints.isNotEmpty)
              PolylineLayer(polylines: [
                Polyline(
                  points: _routePoints,
                  strokeWidth: 5,
                  color: _congestionColor,
                ),
              ]),
            // Markers
            MarkerLayer(markers: [
              if (_pickupLocation != null)
                Marker(
                  point: _pickupLocation!,
                  width: 44,
                  height: 44,
                  child: _PickupMarker(pulseCtrl: _pulseCtrl),
                ),
              if (_dropoffLocation != null)
                Marker(
                  point: _dropoffLocation!,
                  width: 44,
                  height: 44,
                  child: _DropoffMarker(),
                ),
            ]),
          ],
        ),

        // ── TOP BAR ──
        Positioned(
          top: 0,
          left: 0,
          right: 0,
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(children: [
                _TopButton(icon: Icons.menu, onTap: () {}),
                const Spacer(),
                _AiStatusChip(online: aiOnline, ctrl: _pulseCtrl),
                const SizedBox(width: 8),
                _TopButton(
                  icon: Icons.my_location,
                  onTap: () => _mapController.move(_mapCenter, 13.0),
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
          child: _buildBottomPanel(context),
        ),

        // ── LOADING OVERLAY ──
        if (_isLoading)
          Container(
            color: Colors.black.withOpacity(0.6),
            child: Center(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                SizedBox(
                  width: 56,
                  height: 56,
                  child: CircularProgressIndicator(
                    color: kEmergencyOrange,
                    strokeWidth: 3,
                  ),
                ),
                const SizedBox(height: 20),
                Text('Analyzing with AI...',
                    style: GoogleFonts.rajdhani(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1)),
                const SizedBox(height: 6),
                Text('LSTM + GCN model running',
                    style: GoogleFonts.rajdhani(
                        color: kAiCyan, fontSize: 13, letterSpacing: 0.5)),
              ]),
            ),
          ),
      ]),
    );
  }

  // ── BOTTOM PANEL ──────────────────────────────────────────────────────────

  Widget _buildBottomPanel(BuildContext context) {
    final screenH = MediaQuery.of(context).size.height;
    return ConstrainedBox(
      constraints: BoxConstraints(maxHeight: screenH * 0.72),
      child: Container(
        decoration: BoxDecoration(
          color: const Color(0xFF0D0D0D),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          border: Border.all(color: kCardBorder),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.9),
              blurRadius: 24,
              offset: const Offset(0, -4),
            )
          ],
        ),
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Drag handle
              Center(
                child: Container(
                  margin: const EdgeInsets.only(top: 12, bottom: 4),
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey[800],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // Header row
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
                child: Row(children: [
                  // Badge
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: kEmergencyOrange.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                          color: kEmergencyOrange.withOpacity(0.45), width: 1),
                    ),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.local_hospital,
                          color: kEmergencyOrange, size: 13),
                      const SizedBox(width: 5),
                      Text('EMERGENCY AI',
                          style: GoogleFonts.rajdhani(
                              color: kEmergencyOrange,
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 1.5)),
                    ]),
                  ),
                  const Spacer(),
                  if (_prediction != null)
                    Text(
                      '${_routeDistanceKm.toStringAsFixed(1)} km  ·  '
                      '${_routeDurationMin.toStringAsFixed(0)} min',
                      style: GoogleFonts.rajdhani(
                          color: kTextSecondary, fontSize: 13),
                    ),
                ]),
              ),

              const SizedBox(height: 14),

              // City chips — pan-India
              SizedBox(
                height: 42,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  itemCount: kCities.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (ctx, i) {
                    final city = kCities[i];
                    final sel = city.name == _selectedCity.name;
                    final trained = city.hasCityModel;
                    return GestureDetector(
                      onTap: () {
                        setState(() {
                          _selectedCity = city;
                          _mapCenter = LatLng(city.lat, city.lng);
                        });
                        _mapController.move(
                            LatLng(city.lat, city.lng), 12.5);
                      },
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 0),
                        decoration: BoxDecoration(
                          color: sel
                              ? kEmergencyOrange
                              : const Color(0xFF1A1A1A),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: sel
                                ? kEmergencyOrange
                                : trained
                                    ? kAiCyan.withOpacity(0.4)
                                    : kCardBorder,
                          ),
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Row(mainAxisSize: MainAxisSize.min, children: [
                              if (trained)
                                Icon(Icons.bolt,
                                    color: sel ? Colors.black : kAiCyan,
                                    size: 11),
                              if (trained) const SizedBox(width: 2),
                              Text(
                                city.name,
                                style: GoogleFonts.rajdhani(
                                  color: sel
                                      ? Colors.black
                                      : kTextSecondary,
                                  fontWeight: sel
                                      ? FontWeight.bold
                                      : FontWeight.w500,
                                  fontSize: 13,
                                  letterSpacing: 0.4,
                                ),
                              ),
                            ]),
                            Text(
                              city.state,
                              style: GoogleFonts.rajdhani(
                                color: sel
                                    ? Colors.black54
                                    : Colors.grey[700]!,
                                fontSize: 9,
                                letterSpacing: 0.2,
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),

              const SizedBox(height: 14),

              // Input fields
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Column(children: [
                  _LocationField(
                    controller: _pickupController,
                    focusNode: _pickupFocus,
                    hint: 'Pickup / Station location',
                    icon: Icons.emergency,
                    iconColor: kAiCyan,
                    accentColor: kAiCyan,
                  ),
                  const SizedBox(height: 8),
                  _LocationField(
                    controller: _dropoffController,
                    focusNode: _dropoffFocus,
                    hint: 'Incident / Destination',
                    icon: Icons.location_on,
                    iconColor: kDanger,
                    accentColor: kDanger,
                  ),
                ]),
              ),

              const SizedBox(height: 16),

              // Analyze button
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: _AnalyzeButton(
                  loading: _isLoading,
                  onTap: _isLoading ? null : _onAnalyzeRoute,
                ),
              ),

              // AI Prediction card
              if (_showPrediction && _prediction != null) ...[
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: _PredictionCard(
                    prediction: _prediction!,
                    distKm: _routeDistanceKm,
                    durMin: _routeDurationMin,
                    cityName: _selectedCity.name,
                    isAreaModel: !_selectedCity.hasCityModel,
                    onDispatch: () => _snack(
                        'Emergency unit dispatched via ${_selectedCity.name}!'),
                  ),
                ),
              ],

              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Sub-widgets ────────────────────────────────────────────────────────────

class _TopButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  const _TopButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.82),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: kCardBorder),
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }
}

class _AiStatusChip extends StatelessWidget {
  final bool online;
  final AnimationController ctrl;
  const _AiStatusChip({required this.online, required this.ctrl});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: ctrl,
      builder: (_, __) {
        final pulse = online ? (0.5 + 0.5 * ctrl.value) : 1.0;
        final dotColor = online ? kAiCyan : kDanger;
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          decoration: BoxDecoration(
            color: Colors.black.withOpacity(0.85),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: online
                  ? kAiCyan.withOpacity(pulse)
                  : kDanger.withOpacity(0.5),
            ),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: dotColor,
                shape: BoxShape.circle,
                boxShadow: online
                    ? [
                        BoxShadow(
                            color: kAiCyan.withOpacity(pulse), blurRadius: 8)
                      ]
                    : null,
              ),
            ),
            const SizedBox(width: 7),
            Text(
              online ? 'AI ONLINE' : 'AI OFFLINE',
              style: GoogleFonts.rajdhani(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.2),
            ),
          ]),
        );
      },
    );
  }
}

class _PickupMarker extends StatelessWidget {
  final AnimationController pulseCtrl;
  const _PickupMarker({required this.pulseCtrl});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: pulseCtrl,
      builder: (_, __) => Container(
        decoration: BoxDecoration(
          color: kAiCyan,
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: kAiCyan.withOpacity(0.3 + 0.4 * pulseCtrl.value),
              blurRadius: 16,
              spreadRadius: 2,
            )
          ],
        ),
        child: const Icon(Icons.emergency, color: Colors.black, size: 22),
      ),
    );
  }
}

class _DropoffMarker extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kDanger,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(color: kDanger.withOpacity(0.55), blurRadius: 14)
        ],
      ),
      child: const Icon(Icons.location_on, color: Colors.white, size: 22),
    );
  }
}

class _LocationField extends StatelessWidget {
  final TextEditingController controller;
  final FocusNode focusNode;
  final String hint;
  final IconData icon;
  final Color iconColor;
  final Color accentColor;

  const _LocationField({
    required this.controller,
    required this.focusNode,
    required this.hint,
    required this.icon,
    required this.iconColor,
    required this.accentColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF181818),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accentColor.withOpacity(0.25)),
      ),
      child: TextField(
        controller: controller,
        focusNode: focusNode,
        style: GoogleFonts.rajdhani(color: Colors.white, fontSize: 15),
        decoration: InputDecoration(
          border: InputBorder.none,
          prefixIcon:
              Icon(icon, color: iconColor.withOpacity(0.85), size: 20),
          hintText: hint,
          hintStyle:
              GoogleFonts.rajdhani(color: Colors.grey[600], fontSize: 15),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
        ),
      ),
    );
  }
}

class _AnalyzeButton extends StatelessWidget {
  final bool loading;
  final VoidCallback? onTap;
  const _AnalyzeButton({required this.loading, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 54,
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFFFF6B35), Color(0xFFFF3D00)],
          ),
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: kEmergencyOrange.withOpacity(0.35),
              blurRadius: 16,
              offset: const Offset(0, 4),
            )
          ],
        ),
        child: Center(
          child: loading
              ? const SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(
                      color: Colors.white, strokeWidth: 2.5),
                )
              : Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.route, color: Colors.white, size: 20),
                  const SizedBox(width: 10),
                  Text(
                    'ANALYZE ROUTE WITH AI',
                    style: GoogleFonts.rajdhani(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.5),
                  ),
                ]),
        ),
      ),
    );
  }
}

class _PredictionCard extends StatelessWidget {
  final PredictionResponse prediction;
  final double distKm;
  final double durMin;
  final String cityName;
  final bool isAreaModel;
  final VoidCallback onDispatch;

  const _PredictionCard({
    required this.prediction,
    required this.distKm,
    required this.durMin,
    required this.cityName,
    required this.isAreaModel,
    required this.onDispatch,
  });

  @override
  Widget build(BuildContext context) {
    final color = getCongestionColor(prediction.congestionT5);
    final label = getCongestionLabel(prediction.congestionT5);
    final message = getCongestionMessage(prediction.congestionT5);
    final confidence =
        ((1 - prediction.uncertaintyT5) * 100).clamp(0, 100).toInt();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF111111),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withOpacity(0.35)),
        boxShadow: [
          BoxShadow(
              color: color.withOpacity(0.08), blurRadius: 20, spreadRadius: 2)
        ],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Header
        Row(children: [
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: color.withOpacity(0.15),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: color.withOpacity(0.4)),
            ),
            child: Text(label,
                style: GoogleFonts.rajdhani(
                    color: color,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1)),
          ),
          const SizedBox(width: 10),
          Icon(Icons.psychology, color: kAiCyan, size: 14),
          const SizedBox(width: 4),
          Text('$confidence% confidence',
              style: GoogleFonts.rajdhani(color: kAiCyan, fontSize: 12)),
          const Spacer(),
          Text('$cityName',
              style: GoogleFonts.rajdhani(
                  color: kTextSecondary, fontSize: 12)),
        ]),

        const SizedBox(height: 14),

        // Congestion forecast label
        Text('CONGESTION FORECAST',
            style: GoogleFonts.rajdhani(
                color: kTextSecondary,
                fontSize: 10,
                letterSpacing: 1.5)),
        const SizedBox(height: 10),

        // Horizon bars
        Row(children: [
          _HorizonBar(label: 'T+5', value: prediction.congestionT5),
          const SizedBox(width: 10),
          _HorizonBar(label: 'T+10', value: prediction.congestionT10),
          const SizedBox(width: 10),
          _HorizonBar(label: 'T+20', value: prediction.congestionT20),
          const SizedBox(width: 10),
          _HorizonBar(label: 'T+30', value: prediction.congestionT30),
        ]),

        const SizedBox(height: 12),

        // Message
        Container(
          padding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: color.withOpacity(0.07),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(children: [
            Icon(Icons.info_outline, color: color, size: 14),
            const SizedBox(width: 8),
            Expanded(
              child: Text(message,
                  style: GoogleFonts.rajdhani(
                      color: kTextSecondary, fontSize: 12)),
            ),
          ]),
        ),

        const SizedBox(height: 12),

        // Inference mode + latency
        Row(children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: isAreaModel
                  ? kWarning.withOpacity(0.12)
                  : kAiCyan.withOpacity(0.12),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              isAreaModel ? 'AREA MODEL' : 'CITY MODEL',
              style: GoogleFonts.rajdhani(
                color: isAreaModel ? kWarning : kAiCyan,
                fontSize: 9,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.8,
              ),
            ),
          ),
          const SizedBox(width: 8),
          const Icon(Icons.timer, color: kAiCyan, size: 12),
          const SizedBox(width: 3),
          Text(
            '${prediction.latencyMs.toStringAsFixed(0)} ms  ·  '
            '${distKm.toStringAsFixed(1)} km  ·  '
            '${durMin.toStringAsFixed(0)} min ETA',
            style:
                GoogleFonts.rajdhani(color: kTextSecondary, fontSize: 11),
          ),
        ]),

        const SizedBox(height: 14),

        // Dispatch button
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: onDispatch,
            icon: const Icon(Icons.local_hospital, size: 16),
            label: Text(
              'DISPATCH EMERGENCY UNIT',
              style: GoogleFonts.rajdhani(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.2),
            ),
            style: ElevatedButton.styleFrom(
              backgroundColor: kDanger,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 13),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
              elevation: 0,
            ),
          ),
        ),
      ]),
    )
        .animate()
        .slideY(begin: 0.3, end: 0, duration: 350.ms, curve: Curves.easeOut)
        .fadeIn(duration: 300.ms);
  }
}

class _HorizonBar extends StatelessWidget {
  final String label;
  final double value;
  const _HorizonBar({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    final color = getCongestionColor(value);
    return Expanded(
      child: Column(children: [
        Text(
          '${(value * 100).toStringAsFixed(0)}%',
          style: GoogleFonts.rajdhani(
              color: color, fontSize: 15, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 5),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: value,
            backgroundColor: Colors.grey[900],
            valueColor: AlwaysStoppedAnimation(color),
            minHeight: 7,
          ),
        ),
        const SizedBox(height: 4),
        Text(label,
            style: GoogleFonts.rajdhani(
                color: kTextSecondary, fontSize: 10, letterSpacing: 0.5)),
      ]),
    );
  }
}
