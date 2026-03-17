import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';

import '../config/theme.dart';
import '../models/route_model.dart';
import '../providers/emergency_requests_provider.dart';
import '../services/backend_service.dart';
import '../services/supabase_location_service.dart';

import 'live_tracking_screen.dart';

// ── Dispatch Command Center ───────────────────────────────────────────────

class DispatchScreen extends ConsumerStatefulWidget {
  final int initialTab;
  const DispatchScreen({super.key, this.initialTab = 0});

  @override
  ConsumerState<DispatchScreen> createState() => _DispatchScreenState();
}

class _DispatchScreenState extends ConsumerState<DispatchScreen>
    with TickerProviderStateMixin {
  // 0 = INCOMING, 1 = ACTIVE, 2 = ALERTS
  late int _tab;
  bool _showMap = true;
  final _mapCtrl = MapController();
  Timer? _refreshTimer;


  late AnimationController _pulseCtrl;

  List<Map<String, dynamic>> _availableVehicles = [];
  List<Map<String, dynamic>> _availableHospitals = [];
  bool _isLoadingResources = false;
  StreamSubscription<IncidentLocationUpdate>? _realtimeSub;

  @override
  void initState() {
    super.initState();
    _tab = widget.initialTab;
    _pulseCtrl = AnimationController(
        vsync: this, duration: const Duration(seconds: 2))
      ..repeat(reverse: true);
    // Force rebuild and refresh resources every 30s
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      _loadResources();
      if (mounted) setState(() {});
    });
    
    // Initialize backend and start polling
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final backend = ref.read(backendServiceProvider);
      try {
        await backend.findWorkingBackend();
        if (mounted) {
          backend.startBlockagePolling();
          _loadResources();
        }
      } catch (e) {
        print('Error initializing backend: $e');
        ref.read(alertsProvider.notifier).addAlert(
          'Connection Error',
          'Could not connect to backend. Check if server is running.',
          'error',
        );
      }

      // Subscribe to realtime location updates from authority dashboard
      final locationService = ref.read(supabaseLocationServiceProvider);
      _realtimeSub = locationService.locationUpdates.listen((update) {
        if (!mounted) return;
        HapticFeedback.heavyImpact();
        // Switch to INCOMING tab so dispatcher sees the new event
        setState(() => _tab = 0);
        // Show a persistent notification banner
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            duration: const Duration(seconds: 6),
            backgroundColor: kDanger,
            behavior: SnackBarBehavior.floating,
            margin: const EdgeInsets.fromLTRB(16, 0, 16, 80),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            content: Row(children: [
              const Icon(Icons.location_on, color: Colors.white, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('🚨 NEW ML LOCATION DETECTED',
                      style: GoogleFonts.rajdhani(
                          color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 0.8)),
                  Text('${update.disasterType} at ${update.locationLabel}',
                      style: GoogleFonts.rajdhani(color: Colors.white70, fontSize: 11),
                      overflow: TextOverflow.ellipsis),
                ]),
              ),
            ]),
          ),
        );
      });
    });
  }

  Future<void> _loadResources() async {
    if (!mounted) return;
    setState(() => _isLoadingResources = true);
    try {
      final backend = ref.read(backendServiceProvider);
      final vehicles = await backend.getAllVehicles();
      final hospitals = await backend.getAllHospitals();
      if (mounted) {
        setState(() {
          _availableVehicles = vehicles;
          _availableHospitals = hospitals;
          _isLoadingResources = false;
        });
      }
    } catch (e) {
      print('Error loading resources: $e');
      if (mounted) setState(() => _isLoadingResources = false);
    }
  }

  Future<void> _dispatchRequest(EmergencyRequest req) async {
    HapticFeedback.heavyImpact();

    if (_availableHospitals.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No hospitals available via backend. Wait for resources.')));
      return;
    }

    final availableVehicles = _availableVehicles.where((v) => v['status'] == 'AVAILABLE').toList();
    if (availableVehicles.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No available vehicles right now.')));
      return;
    }

    // Auto-select nearest hospital
    const distance = Distance();
    final sortedHospitals = List<Map<String, dynamic>>.from(_availableHospitals);
    sortedHospitals.sort((a, b) {
      final distA = distance.as(LengthUnit.Meter, req.originCoord, LatLng(a['lat'], a['lon']));
      final distB = distance.as(LengthUnit.Meter, req.originCoord, LatLng(b['lat'], b['lon']));
      return distA.compareTo(distB);
    });

    try {
      final backend = ref.read(backendServiceProvider);
      final vehicle = availableVehicles.first;
      final hospital = sortedHospitals.first;

      // Call backend dispatch API
      final result = await backend.dispatchIncident(
        incidentId: req.id,
        vehicleId: vehicle['id'],
        vehicleStartLat: vehicle['lat'],
        vehicleStartLon: vehicle['lon'],
        incidentLat: req.originCoord.latitude,
        incidentLon: req.originCoord.longitude,
        hospitalId: hospital['id'],
        hospitalLat: hospital['lat'],
        hospitalLon: hospital['lon'],
        cityName: 'Indore',
      );

      // Update local state for UI
      ref.read(emergencyRequestsProvider.notifier).updateState(req.id, IncidentState.dispatched);

      // Create active dispatch with real data from backend
      final dispatch = ActiveDispatch(
        id: 'DSP-${DateTime.now().millisecondsSinceEpoch}',
        type: req.type,
        origin: req.originLabel,
        destination: hospital['name'],
        originCoord: req.originCoord,
        destCoord: LatLng(hospital['lat'], hospital['lon']),
        etaMin: (result['route']?['eta_min'] ?? 8.0).toDouble(),
        dispatchedAt: DateTime.now(),
        cityName: 'Indore',
        priority: req.priority,
      );
      ref.read(activeDispatchesProvider.notifier).addDispatch(dispatch);

      // Start polling vehicle position
      await backend.startVehiclePolling(vehicle['id']);

      // Add alert
      ref.read(alertsProvider.notifier).addAlert(
        'Dispatch System',
        '${req.type.label} ${vehicle['id']} dispatched to ${req.originLabel}',
        'success',
      );

      // Show snackbar
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('✅ ${req.type.label} ${vehicle['id']} → ${req.originLabel}',
            style: GoogleFonts.rajdhani(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: kSuccess,
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.fromLTRB(16, 0, 16, 70),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        duration: const Duration(seconds: 3),
      ));

      setState(() => _tab = 1); // Switch to ACTIVE tab
    } catch (e) {
      print('❌ Dispatch error: $e');
      
      // Show error snackbar
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('❌ Dispatch failed: $e',
            style: GoogleFonts.rajdhani(color: Colors.white)),
        backgroundColor: kDanger,
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.fromLTRB(16, 0, 16, 70),
      ));
    } finally {
      // Dispatch request completed
    }
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    _refreshTimer?.cancel();
    _realtimeSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final allRequests = ref.watch(emergencyRequestsProvider);
    final pending = allRequests.where((r) => r.state == IncidentState.reported).toList();
    final active = ref.watch(activeDispatchesProvider);
    final alerts = ref.watch(alertsProvider);

    return Scaffold(
      backgroundColor: kBackground,
      body: SafeArea(
        child: Column(children: [
          // ── Header ──────────────────────────────────────────────
          _buildHeader(pending.length, active.length),
          const SizedBox(height: 8),

          // ── Tab bar ─────────────────────────────────────────────
          _buildTabBar(pending.length, active.length, alerts.length),
          const SizedBox(height: 6),

          // ── Map toggle ──────────────────────────────────────────
          if (_tab < 2)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(children: [
                GestureDetector(
                  onTap: () => setState(() => _showMap = !_showMap),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: _showMap ? kAiCyan.withOpacity(0.15) : Colors.white.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                          color: _showMap ? kAiCyan.withOpacity(0.4) : Colors.white12),
                    ),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      Icon(_showMap ? Icons.map : Icons.map_outlined,
                          color: _showMap ? kAiCyan : kTextSecondary, size: 14),
                      const SizedBox(width: 5),
                      Text(_showMap ? 'MAP ON' : 'MAP OFF',
                          style: GoogleFonts.rajdhani(
                              color: _showMap ? kAiCyan : kTextSecondary,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 1)),
                    ]),
                  ),
                ),
                const Spacer(),
                if (_tab == 0)
                  Text('${pending.length} INCOMING',
                      style: GoogleFonts.rajdhani(
                          color: kDanger, fontSize: 11, fontWeight: FontWeight.bold)),
                if (_tab == 1)
                  Text('${active.length} EN ROUTE',
                      style: GoogleFonts.rajdhani(
                          color: kSuccess, fontSize: 11, fontWeight: FontWeight.bold)),
              ]),
            ),

          const SizedBox(height: 6),

          // ── Map view ────────────────────────────────────────────
          if (_showMap && _tab < 2)
            _buildMapSection(pending, active),

          // ── Content ─────────────────────────────────────────────
          Expanded(
            child: _tab == 0
                ? _buildIncomingList(pending)
                : _tab == 1
                    ? _buildActiveList(active)
                    : _buildAlertsList(alerts),
          ),
        ]),
      ),
    );
  }

  // ── Header ──────────────────────────────────────────────────────────────

  Widget _buildHeader(int pendingCount, int activeCount) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      child: Row(children: [
        AnimatedBuilder(
          animation: _pulseCtrl,
          builder: (_, __) => Icon(Icons.local_fire_department,
              color: kEmergencyOrange.withOpacity(0.7 + 0.3 * _pulseCtrl.value),
              size: 22),
        ),
        const SizedBox(width: 10),
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('DISPATCH CENTER',
              style: GoogleFonts.rajdhani(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.5)),
          Text('Priority-based emergency scheduling',
              style: GoogleFonts.rajdhani(color: kTextSecondary, fontSize: 11)),
        ]),
        const Spacer(),
        if (pendingCount > 0)
          _CountBadge(count: pendingCount, color: kDanger, label: 'PENDING'),
        const SizedBox(width: 6),
        if (activeCount > 0)
          _CountBadge(count: activeCount, color: kSuccess, label: 'ACTIVE'),
      ]),
    );
  }

  // ── Tab bar ─────────────────────────────────────────────────────────────

  Widget _buildTabBar(int pending, int active, int alerts) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(children: [
        _TabButton(
          label: 'INCOMING',
          icon: Icons.notifications_active,
          selected: _tab == 0,
          color: kDanger,
          badge: pending,
          onTap: () => setState(() => _tab = 0),
        ),
        const SizedBox(width: 6),
        _TabButton(
          label: 'ACTIVE',
          icon: Icons.local_shipping,
          selected: _tab == 1,
          color: kSuccess,
          badge: active,
          onTap: () => setState(() => _tab = 1),
        ),
        const SizedBox(width: 6),
        _TabButton(
          label: 'COMMS',
          icon: Icons.chat_bubble,
          selected: _tab == 2,
          color: kAiCyan,
          badge: alerts,
          onTap: () => setState(() => _tab = 2),
        ),
      ]),
    );
  }

  // ── Map section ─────────────────────────────────────────────────────────

  Widget _buildMapSection(List<EmergencyRequest> pending, List<ActiveDispatch> active) {
    final markers = <Marker>[];

    // Pending requests — pulsing colored markers
    for (final req in pending) {
      markers.add(Marker(
        point: req.originCoord,
        width: 36, height: 36,
        child: GestureDetector(
          onTap: () => _showDispatchDialog(req),
          child: Container(
            decoration: BoxDecoration(
              color: req.priority.color.withOpacity(0.2),
              shape: BoxShape.circle,
              border: Border.all(color: req.priority.color, width: 2),
            ),
            child: Icon(req.type.icon, color: req.priority.color, size: 16),
          ),
        ),
      ));
    }

    // Active dispatches — green pulsing markers
    for (final d in active) {
      markers.add(Marker(
        point: d.originCoord,
        width: 32, height: 32,
        child: Container(
          decoration: BoxDecoration(
            color: kSuccess.withOpacity(0.25),
            shape: BoxShape.circle,
            border: Border.all(color: kSuccess, width: 2),
            boxShadow: [BoxShadow(color: kSuccess.withOpacity(0.3), blurRadius: 8)],
          ),
          child: Icon(d.type.icon, color: kSuccess, size: 14),
        ),
      ));
    }

    const darkMatrix = <double>[
      -1, 0, 0, 0, 255,
      0, -1, 0, 0, 255,
      0, 0, -1, 0, 255,
      0, 0, 0, 1, 0,
    ];

    return Container(
      height: 200,
      margin: const EdgeInsets.symmetric(horizontal: 16),
      clipBehavior: Clip.hardEdge,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kCardBorder),
      ),
      child: FlutterMap(
        mapController: _mapCtrl,
        options: MapOptions(
          initialCenter: const LatLng(22.7196, 75.8577), // Indore
          initialZoom: 12.5,
          interactionOptions: const InteractionOptions(flags: InteractiveFlag.all),
        ),
        children: [
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'com.swiftemergency.app',
            tileBuilder: (ctx, widget, tile) => ColorFiltered(
              colorFilter: const ColorFilter.matrix(darkMatrix),
              child: widget,
            ),
          ),
          MarkerLayer(markers: markers),
        ],
      ),
    );
  }

  // ── Incoming requests list ──────────────────────────────────────────────

  Widget _buildIncomingList(List<EmergencyRequest> pending) {
    if (pending.isEmpty) {
      return Center(
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(Icons.check_circle, color: kSuccess.withOpacity(0.3), size: 56),
          const SizedBox(height: 12),
          Text('All clear — no pending requests',
              style: GoogleFonts.rajdhani(color: kTextSecondary, fontSize: 15)),
        ]),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      itemCount: pending.length,
      itemBuilder: (ctx, i) {
        final req = pending[i];
        return _IncomingRequestCard(
          request: req,
          onDispatch: () {
            ref.read(selectedIncidentForRoutingProvider.notifier).state = req;
            ref.read(mainAppTabProvider.notifier).state = 1;
          },
        ).animate().fadeIn(duration: 250.ms, delay: Duration(milliseconds: i * 50))
            .slideX(begin: 0.05, end: 0);
      },
    );
  }

  void _showDispatchDialog(EmergencyRequest req) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF151515),
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
            side: BorderSide(color: req.priority.color.withOpacity(0.4))),
        title: Row(children: [
          Icon(req.type.icon, color: req.type.color, size: 22),
          const SizedBox(width: 10),
          Text('DISPATCH ${req.type.label.toUpperCase()}?',
              style: GoogleFonts.rajdhani(
                  color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
        ]),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          _DialogRow(Icons.priority_high, req.priority.label, req.priority.color),
          _DialogRow(Icons.location_on, req.originLabel, Colors.white70),
          _DialogRow(Icons.local_hospital, req.destLabel, Colors.white70),
          _DialogRow(Icons.person, req.callerInfo, kTextSecondary),
          _DialogRow(Icons.access_time, req.timeAgo, kTextSecondary),
        ]),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('CANCEL',
                style: GoogleFonts.rajdhani(color: kTextSecondary, fontWeight: FontWeight.bold)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: req.type.color,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            onPressed: () {
              Navigator.pop(ctx);
              ref.read(selectedIncidentForRoutingProvider.notifier).state = req;
              ref.read(mainAppTabProvider.notifier).state = 1;
            },
            child: Text('ASSIGN VEHICLE',
                style: GoogleFonts.rajdhani(
                    color: Colors.white, fontWeight: FontWeight.bold, letterSpacing: 1)),
          ),
        ],
      ),
    );
  }

  // ── Active dispatches list ──────────────────────────────────────────────

  Widget _buildActiveList(List<ActiveDispatch> active) {
    if (active.isEmpty) {
      return Center(
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(Icons.local_shipping_outlined, color: Colors.grey[800], size: 56),
          const SizedBox(height: 12),
          Text('No active dispatches',
              style: GoogleFonts.rajdhani(color: kTextSecondary, fontSize: 15)),
          const SizedBox(height: 6),
          Text('Tap an incoming request to dispatch',
              style: GoogleFonts.rajdhani(color: Colors.grey[800], fontSize: 13)),
        ]),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      itemCount: active.length,
      itemBuilder: (ctx, i) {
        final d = active[i];
        return _ActiveDispatchCard(
          dispatch: d,
          onEnd: () {
            ref.read(activeDispatchesProvider.notifier).removeDispatch(d.id);
            ref.read(alertsProvider.notifier).addAlert(
              'System',
              '${d.type.label} dispatch ${d.id} completed — ${d.destination}.',
              'info',
            );
          },
        ).animate().fadeIn(duration: 250.ms, delay: Duration(milliseconds: i * 50))
            .slideX(begin: 0.05, end: 0);
      },
    );
  }

  // ── Alerts / Comms list ─────────────────────────────────────────────────

  Widget _buildAlertsList(List<Map<String, String>> alerts) {
    if (alerts.isEmpty) {
      return Center(
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(Icons.chat_bubble_outline, color: Colors.grey[800], size: 56),
          const SizedBox(height: 12),
          Text('No messages yet',
              style: GoogleFonts.rajdhani(color: kTextSecondary, fontSize: 15)),
        ]),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      itemCount: alerts.length,
      itemBuilder: (ctx, i) {
        final a = alerts[i];
        final type = a['type'] ?? 'info';
        final color = type == 'critical'
            ? kDanger
            : type == 'warning'
                ? kWarning
                : type == 'success'
                    ? kSuccess
                    : kAiCyan;
        final icon = type == 'critical'
            ? Icons.warning_amber
            : type == 'warning'
                ? Icons.report_problem
                : type == 'success'
                    ? Icons.check_circle
                    : Icons.info_outline;

        return Container(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: color.withOpacity(0.06),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: color.withOpacity(0.2)),
          ),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(icon, color: color, size: 16),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Text(a['from'] ?? '',
                      style: GoogleFonts.rajdhani(
                          color: color, fontSize: 12, fontWeight: FontWeight.bold)),
                  const Spacer(),
                  Text(a['time'] ?? '',
                      style: GoogleFonts.rajdhani(color: Colors.grey[700], fontSize: 10)),
                ]),
                const SizedBox(height: 3),
                Text(a['msg'] ?? '',
                    style: GoogleFonts.rajdhani(color: Colors.white70, fontSize: 13)),
              ]),
            ),
          ]),
        ).animate().fadeIn(duration: 200.ms, delay: Duration(milliseconds: i * 40));
      },
    );
  }
}

// ══════════════════════════════════════════════════════════════════════════
//  Sub-widgets
// ══════════════════════════════════════════════════════════════════════════

class _CountBadge extends StatelessWidget {
  final int count;
  final Color color;
  final String label;
  const _CountBadge({required this.count, required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text('$count $label',
          style: GoogleFonts.rajdhani(
              color: color, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 0.5)),
    );
  }
}

class _TabButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool selected;
  final Color color;
  final int badge;
  final VoidCallback onTap;

  const _TabButton({
    required this.label,
    required this.icon,
    required this.selected,
    required this.color,
    required this.badge,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: selected ? color.withOpacity(0.12) : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
                color: selected ? color.withOpacity(0.4) : Colors.white10),
          ),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(icon, color: selected ? color : kTextSecondary, size: 14),
            const SizedBox(width: 5),
            Text(label,
                style: GoogleFonts.rajdhani(
                    color: selected ? color : kTextSecondary,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.8)),
            if (badge > 0) ...[
              const SizedBox(width: 5),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                decoration: BoxDecoration(
                  color: color.withOpacity(selected ? 0.3 : 0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text('$badge',
                    style: GoogleFonts.rajdhani(
                        color: color, fontSize: 9, fontWeight: FontWeight.bold)),
              ),
            ],
          ]),
        ),
      ),
    );
  }
}

class _IncomingRequestCard extends StatelessWidget {
  final EmergencyRequest request;
  final VoidCallback onDispatch;

  const _IncomingRequestCard({required this.request, required this.onDispatch});

  @override
  Widget build(BuildContext context) {
    final req = request;
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => _showSceneDialog(context, req),
          borderRadius: BorderRadius.circular(16),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: req.type.color.withOpacity(0.04),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: req.priority.color.withOpacity(0.25)),
            ),
            child: Row(children: [
              // Type icon or Image
              req.videoFeedUrl != null ? ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.network(
                  req.videoFeedUrl!,
                  width: 50, height: 50,
                  fit: BoxFit.cover,
                  errorBuilder: (ctx, err, stack) => _buildFallbackIcon(req),
                ),
              ) : _buildFallbackIcon(req),
              const SizedBox(width: 12),
              // Info
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Text(req.rawType.toUpperCase(),
                        style: GoogleFonts.rajdhani(
                            color: req.type.color,
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.5)),
                    const SizedBox(width: 6),
                    _PriorityChip(priority: req.priority),
                    const Spacer(),
                    Text(req.timeAgo,
                        style: GoogleFonts.rajdhani(color: Colors.grey[600], fontSize: 11)),
                  ]),
                  const SizedBox(height: 3),
                  Text('${req.originLabel} → ${req.destLabel}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.rajdhani(
                          color: Colors.white70, fontSize: 12)),
                  const SizedBox(height: 2),
                  Text('📞 ${req.callerInfo}',
                      style: GoogleFonts.rajdhani(color: Colors.grey[600], fontSize: 11)),
                  
                  // Smart Witness Mode Summary
                  if (req.witnessReports.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.05),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: Colors.cyanAccent.withOpacity(0.3)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.visibility, size: 12, color: Colors.cyanAccent),
                              const SizedBox(width: 4),
                              Text('Witness Reports: ${req.witnessReports.length}  |  Photos: ${req.photosUploaded}', style: GoogleFonts.rajdhani(color: Colors.cyanAccent, fontSize: 11, fontWeight: FontWeight.bold)),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Wrap(
                            spacing: 4,
                            runSpacing: 4,
                            children: req.witnessReports.expand((w) => w.hazardTags).toSet().map((tag) => Container(
                              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                              decoration: BoxDecoration(color: Colors.redAccent.withOpacity(0.2), borderRadius: BorderRadius.circular(4)),
                              child: Text(tag, style: GoogleFonts.rajdhani(color: Colors.redAccent, fontSize: 9)),
                            )).toList(),
                          ),
                        ],
                      ),
                    ),
                  ],
                ]),
              ),
              const SizedBox(width: 8),
              // Dispatch arrow
              GestureDetector(
                onTap: onDispatch,
                child: Container(
                  width: 36, height: 36,
                  decoration: BoxDecoration(
                    color: req.type.color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(Icons.send, color: req.type.color, size: 16),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _buildFallbackIcon(EmergencyRequest req) {
    return Container(
      width: 50, height: 50,
      decoration: BoxDecoration(
        color: req.type.color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Icon(req.type.icon, color: req.type.color, size: 24),
    );
  }

  void _showSceneDialog(BuildContext context, EmergencyRequest req) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1A1A1A),
        title: Text('Digital Emergency Scene (ID: ${req.id})', style: GoogleFonts.rajdhani(color: Colors.white, fontWeight: FontWeight.bold)),
        content: SizedBox(
          width: 600,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Shared Dashboard Top Section
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.blueAccent.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.blueAccent.withOpacity(0.3)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.dashboard_customize, color: Colors.blueAccent, size: 18),
                          const SizedBox(width: 8),
                          Text('Shared Situation Room', style: GoogleFonts.rajdhani(color: Colors.blueAccent, fontSize: 16, fontWeight: FontWeight.bold)),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text('Emergency Incident #${req.id.split('-').last}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                      Text('Location: ${req.originLabel}', style: const TextStyle(color: Colors.white70)),
                      const SizedBox(height: 8),
                      // Mock Video feature
                      Row(
                        children: [
                          Icon(req.videoFeedUrl != null ? Icons.videocam : Icons.videocam_off, color: req.videoFeedUrl != null ? Colors.redAccent : Colors.grey, size: 16),
                          const SizedBox(width: 4),
                          Text(req.videoFeedUrl != null ? 'Database Feed: LIVE' : 'Feed: OFFLINE', style: TextStyle(color: req.videoFeedUrl != null ? Colors.redAccent : Colors.grey)),
                        ],
                      ),
                      if (req.videoFeedUrl != null) ...[
                        const SizedBox(height: 8),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: ConstrainedBox(
                            constraints: const BoxConstraints(maxHeight: 250),
                            child: Image.network(
                              req.videoFeedUrl!,
                              width: double.infinity,
                              fit: BoxFit.cover,
                              errorBuilder: (ctx, err, stack) => const Text('Image unavailable at URL', style: TextStyle(color: Colors.white54)),
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: 4),
                      Text('Ambulance ETA: ${req.ambulanceEtaMin != null ? "${req.ambulanceEtaMin} minutes" : "Calculating..."}', style: const TextStyle(color: Colors.white70)),
                      Text('Patient condition: ${req.patientCondition ?? "Unknown"}', style: const TextStyle(color: Colors.white70)),
                      Text('Hospital: ${req.assignedHospital ?? "Assigning..."}', style: const TextStyle(color: Colors.white70)),
                    ],
                  ),
                ),
                
                const SizedBox(height: 16),
                
                // Smart Witness Aggregation
                Text('Crowdsourced Incident Intelligence (${req.witnessReports.length} Reports):', style: const TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                if (req.witnessReports.isEmpty)
                  const Text('No citizen media uploaded yet.', style: TextStyle(color: Colors.white38))
                else
                  ...req.witnessReports.map((w) => Padding(
                    padding: const EdgeInsets.only(bottom: 8.0),
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(color: Colors.black45, borderRadius: BorderRadius.circular(8)),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text('Witness ${w.reporterId.substring(0,6)}', style: const TextStyle(color: Colors.white)),
                              const Spacer(),
                              if (w.hasPhoto) const Icon(Icons.camera_alt, size: 14, color: Colors.greenAccent),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text('Notes: ${w.textNotes}', style: const TextStyle(color: Colors.white70, fontSize: 12)),
                          if (w.hazardTags.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 4.0),
                              child: Text('Hazards: ${w.hazardTags.join(", ")}', style: const TextStyle(color: Colors.redAccent, fontSize: 11, fontWeight: FontWeight.bold)),
                            ),
                        ],
                      ),
                    ),
                  )),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('CANCEL', style: TextStyle(color: Colors.white54)),
          ),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.pop(ctx);
              onDispatch();
            },
            icon: const Icon(Icons.send),
            label: const Text('ASSIGN VEHICLE'),
            style: ElevatedButton.styleFrom(backgroundColor: req.type.color, foregroundColor: Colors.white),
          )
        ],
      ),
    );
  }
}

class _PriorityChip extends StatelessWidget {
  final Priority priority;
  const _PriorityChip({required this.priority});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
      decoration: BoxDecoration(
        color: priority.color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(5),
        border: Border.all(color: priority.color.withOpacity(0.4)),
      ),
      child: Text(priority.label,
          style: GoogleFonts.rajdhani(
              color: priority.color, fontSize: 9, fontWeight: FontWeight.bold, letterSpacing: 0.5)),
    );
  }
}

class _ActiveDispatchCard extends ConsumerStatefulWidget {
  final ActiveDispatch dispatch;
  final VoidCallback onEnd;
  const _ActiveDispatchCard({required this.dispatch, required this.onEnd});

  @override
  ConsumerState<_ActiveDispatchCard> createState() => _ActiveDispatchCardState();
}

class _ActiveDispatchCardState extends ConsumerState<_ActiveDispatchCard>
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
    final remaining = d.remainingMin;
    final progress = (1.0 - remaining / d.etaMin).clamp(0.0, 1.0);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      child: AnimatedBuilder(
        animation: _pulse,
        builder: (_, __) => Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: d.type.color.withOpacity(0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
                color: d.type.color.withOpacity(0.3 + 0.2 * _pulse.value)),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(
                width: 10, height: 10,
                decoration: BoxDecoration(
                  color: d.type.color,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                        color: d.type.color.withOpacity(0.5 + 0.4 * _pulse.value),
                        blurRadius: 10)
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Text(d.type.label.toUpperCase(),
                  style: GoogleFonts.rajdhani(
                      color: d.type.color,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1)),
              const SizedBox(width: 6),
              _PriorityChip(priority: d.priority),
              const Spacer(),
              Text(
                remaining <= 0.5
                    ? 'ARRIVED ✓'
                    : '${remaining.toStringAsFixed(0)} min remaining',
                style: GoogleFonts.rajdhani(
                  color: remaining <= 1 ? kSuccess : Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ]),
            const SizedBox(height: 8),
            Text('${d.origin} → ${d.destination}',
                style: GoogleFonts.rajdhani(color: kTextSecondary, fontSize: 12),
                maxLines: 1, overflow: TextOverflow.ellipsis),
            const SizedBox(height: 10),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: progress,
                backgroundColor: Colors.grey[900],
                valueColor: AlwaysStoppedAnimation(d.type.color),
                minHeight: 4,
              ),
            ),
            const SizedBox(height: 8),
            Row(children: [
              Text('Dispatched ${_formatTime(d.dispatchedAt)} · ${d.cityName}',
                  style: GoogleFonts.rajdhani(color: Colors.grey[700], fontSize: 10)),
              const Spacer(),
              GestureDetector(
                onTap: widget.onEnd,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.white12),
                  ),
                  child: Text('END',
                      style: GoogleFonts.rajdhani(
                          color: Colors.white54, fontSize: 10, fontWeight: FontWeight.bold)),
                ),
              ),
              const SizedBox(width: 6),
              GestureDetector(
                onTap: () {
                  Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => LiveTrackingScreen(
                      origin: d.origin,
                      destination: d.destination,
                      originCoord: d.originCoord,
                      destCoord: d.destCoord,
                      isDriver: false,
                    ),
                  ));
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: kAiCyan.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: kAiCyan.withOpacity(0.4)),
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.gps_fixed, color: kAiCyan, size: 12),
                    const SizedBox(width: 4),
                    Text('TRACK LIVE',
                        style: GoogleFonts.rajdhani(
                            color: kAiCyan, fontSize: 10, fontWeight: FontWeight.bold)),
                  ]),
                ),
              ),
              const SizedBox(width: 6),
              GestureDetector(
                onTap: () => _showMissionLogs(context, d.id),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.orangeAccent.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.orangeAccent.withOpacity(0.4)),
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    const Icon(Icons.receipt_long, color: Colors.orangeAccent, size: 12),
                    const SizedBox(width: 4),
                    Text('LOG',
                        style: GoogleFonts.rajdhani(
                            color: Colors.orangeAccent, fontSize: 10, fontWeight: FontWeight.bold)),
                  ]),
                ),
              ),
            ]),
          ]),
        ),
      ),
    );
  }

  String _formatTime(DateTime? dt) {
    if (dt == null) return '--:--';
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }

  void _showMissionLogs(BuildContext context, String incidentId) {
    final backend = ref.read(backendServiceProvider);
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        maxChildSize: 0.9,
        builder: (_, scrollCtrl) => _MissionLogSheet(
          incidentId: incidentId, 
          backend: backend,
          scrollController: scrollCtrl,
        ),
      ),
    );
  }
}

class _MissionLogSheet extends StatelessWidget {
  final String incidentId;
  final BackendService backend;
  final ScrollController scrollController;

  const _MissionLogSheet({
    required this.incidentId, 
    required this.backend,
    required this.scrollController,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          Container(width: 40, height: 4, decoration: BoxDecoration(color: Colors.white12, borderRadius: BorderRadius.circular(2))),
          const SizedBox(height: 20),
          Row(children: [
            const Icon(Icons.receipt_long, color: kAiCyan),
            const SizedBox(width: 12),
            Text('MISSION LOG: $incidentId', style: GoogleFonts.rajdhani(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
          ]),
          const Divider(color: Colors.white10, height: 32),
          Expanded(
            child: FutureBuilder<List<Map<String, dynamic>>>(
              future: backend.getIncidentLogs(incidentId),
              builder: (ctx, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator(color: kAiCyan));
                }
                final logs = snapshot.data ?? [];
                if (logs.isEmpty) {
                  return Center(child: Text('No events recorded yet', style: GoogleFonts.rajdhani(color: Colors.white54)));
                }
                return ListView.builder(
                  controller: scrollController,
                  itemCount: logs.length,
                  itemBuilder: (ctx, i) {
                    final log = logs[i];
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Column(children: [
                            const Icon(Icons.radio_button_checked, size: 12, color: kAiCyan),
                            if (i < logs.length - 1) Container(width: 1, height: 30, color: Colors.white10),
                          ]),
                          const SizedBox(width: 16),
                          Expanded(child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(log['message'] ?? '', style: GoogleFonts.rajdhani(color: Colors.white, fontSize: 14)),
                              Text(log['timestamp'] ?? '', style: GoogleFonts.rajdhani(color: Colors.white38, fontSize: 10)),
                            ],
                          )),
                        ],
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  String _formatTime(DateTime dt) {
    final h = dt.hour > 12 ? dt.hour - 12 : (dt.hour == 0 ? 12 : dt.hour);
    final ampm = dt.hour >= 12 ? 'PM' : 'AM';
    return '${h}:${dt.minute.toString().padLeft(2, '0')} $ampm';
  }
}

class _DialogRow extends StatelessWidget {
  final IconData icon;
  final String text;
  final Color color;
  const _DialogRow(this.icon, this.text, this.color);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        Icon(icon, color: color.withOpacity(0.6), size: 14),
        const SizedBox(width: 10),
        Expanded(
          child: Text(text,
              style: GoogleFonts.rajdhani(color: color, fontSize: 13)),
        ),
      ]),
    );
  }
}

// ── Helper Models ─────────────────────────────────────────────────────────

class SelectionResult {
  final Map<String, dynamic> vehicle;
  final Map<String, dynamic> hospital;
  SelectionResult({required this.vehicle, required this.hospital});
}

class _ResourcePickerDialog extends StatefulWidget {
  final List<Map<String, dynamic>> vehicles;
  final List<Map<String, dynamic>> hospitals;

  const _ResourcePickerDialog({
    required this.vehicles,
    required this.hospitals,
  });

  @override
  State<_ResourcePickerDialog> createState() => _ResourcePickerDialogState();
}

class _ResourcePickerDialogState extends State<_ResourcePickerDialog> {
  Map<String, dynamic>? _selectedVehicle;
  Map<String, dynamic>? _selectedHospital;

  @override
  void initState() {
    super.initState();
    if (widget.vehicles.isNotEmpty) _selectedVehicle = widget.vehicles.first;
    if (widget.hospitals.isNotEmpty) _selectedHospital = widget.hospitals.first;
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: kCardBg,
      title: Text('DISPATCH RESOURCES', style: GoogleFonts.rajdhani(color: Colors.white, fontWeight: FontWeight.bold)),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('SELECT VEHICLE', style: GoogleFonts.rajdhani(color: kAiCyan, fontSize: 13, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (widget.vehicles.isEmpty)
              const Text('No vehicles available!', style: TextStyle(color: Colors.red))
            else
              DropdownButtonFormField<Map<String, dynamic>>(
                dropdownColor: kCardBg,
                value: _selectedVehicle,
                items: widget.vehicles.map((v) => DropdownMenuItem(
                  value: v,
                  child: Text('${v['name']} (${v['id']})', style: const TextStyle(color: Colors.white)),
                )).toList(),
                onChanged: (val) => setState(() => _selectedVehicle = val),
              ),
            const SizedBox(height: 20),
            Text('SELECT HOSPITAL', style: GoogleFonts.rajdhani(color: kEmergencyOrange, fontSize: 13, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            DropdownButtonFormField<Map<String, dynamic>>(
              dropdownColor: kCardBg,
              value: _selectedHospital,
              items: widget.hospitals.map((h) => DropdownMenuItem(
                value: h,
                child: Text('${h['name']} (${h['icu_beds']} beds)', style: const TextStyle(color: Colors.white)),
              )).toList(),
              onChanged: (val) => setState(() => _selectedHospital = val),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL')),
        ElevatedButton(
          onPressed: (_selectedVehicle != null && _selectedHospital != null)
              ? () => Navigator.pop(context, SelectionResult(vehicle: _selectedVehicle!, hospital: _selectedHospital!))
              : null,
          style: ElevatedButton.styleFrom(backgroundColor: kAiCyan, foregroundColor: Colors.black),
          child: const Text('CONFIRM DISPATCH'),
        ),
      ],
    );
  }
}

