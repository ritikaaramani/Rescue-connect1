import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../config/theme.dart';
import '../models/route_model.dart';
import '../services/backend_service.dart';
import 'live_tracking_screen.dart';

class VehicleAppScreen extends ConsumerStatefulWidget {
  final String vehicleId; // Can be passed in or default to hardcoded
  const VehicleAppScreen({super.key, this.vehicleId = 'UP-14-342'});

  @override
  ConsumerState<VehicleAppScreen> createState() => _VehicleAppScreenState();
}

class _VehicleAppScreenState extends ConsumerState<VehicleAppScreen> {
  int _idx = 0;
  VehicleState _status = VehicleState.AVAILABLE;
  bool _hasMission = false;
  
  // Real-time vehicle data from backend
  double _currentLat = 22.7533;
  double _currentLon = 75.8937;
  double _currentSpeed = 0.0;
  double _etaMin = 8.0;
  String _missionOrigin = 'Waiting for mission...';
  String _missionDest = '';
  
  late StreamSubscription _vehicleUpdatesSub;
  late StreamSubscription _rerouteAlertsSub;

  @override
  void initState() {
    super.initState();
    
    // Start polling for position updates
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final backend = ref.read(backendServiceProvider);
      await backend.startVehiclePolling(widget.vehicleId);
      
      // Listen to vehicle updates
      _vehicleUpdatesSub = backend.vehicleUpdates.listen((data) {
        if (!mounted) return;
        setState(() {
          _currentLat = (data['lat'] ?? _currentLat).toDouble();
          _currentLon = (data['lon'] ?? _currentLon).toDouble();
          _currentSpeed = (data['speed_kmh'] ?? _currentSpeed).toDouble();
          _etaMin = (data['eta_minutes'] ?? _etaMin).toDouble();
          
          // Auto-accept mission on first update
          if (!_hasMission && data['eta_minutes'] != null) {
            _acceptMission();
          }
        });
      });
      
      // Listen to reroute alerts
      _rerouteAlertsSub = backend.rerouteAlerts.listen((data) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '🔄 REROUTE: ${data['reason'] ?? "Dynamic optimization"}',
              style: GoogleFonts.rajdhani(color: Colors.white, fontWeight: FontWeight.bold),
            ),
            backgroundColor: Colors.orange,
            duration: const Duration(seconds: 5),
          ),
        );
      });
    });
  }

  @override
  void dispose() {
    _vehicleUpdatesSub.cancel();
    _rerouteAlertsSub.cancel();
    super.dispose();
  }
  
  void _acceptMission() {
    setState(() {
      _hasMission = true;
      _status = VehicleState.EN_ROUTE;
      _missionOrigin = 'Bhawarkuan Square';
      _missionDest = 'Apollo Hospital';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: Text(widget.vehicleId, style: GoogleFonts.rajdhani(fontWeight: FontWeight.bold, letterSpacing: 1.5)),
        backgroundColor: Colors.transparent,
        actions: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            margin: const EdgeInsets.only(right: 16, top: 12, bottom: 12),
            decoration: BoxDecoration(
              color: _status == VehicleState.AVAILABLE ? Colors.green.withOpacity(0.2) : kAiCyan.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12)
            ),
            child: Center(
              child: Text(
                _status.name.toUpperCase().replaceAll('_', ' '),
                style: TextStyle(
                  color: _status == VehicleState.AVAILABLE ? Colors.green : kAiCyan,
                  fontWeight: FontWeight.bold,
                  fontSize: 12
                )
              )
            ),
          ),
        ],
      ),
      body: _idx == 0 ? _buildNavigationTab() : _buildSceneTab(),
      bottomNavigationBar: BottomNavigationBar(
        backgroundColor: kCardBg,
        selectedItemColor: kAiCyan,
        unselectedItemColor: Colors.white54,
        currentIndex: _idx,
        onTap: (i) => setState(() => _idx = i),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.navigation), label: 'Navigation'),
          BottomNavigationBarItem(icon: Icon(Icons.assignment), label: 'Scene Status'),
        ],
      ),
    );
  }

  Widget _buildNavigationTab() {
    if (!_hasMission) {
      return const Center(
        child: Text('📡 Waiting for mission from dispatch...', 
          style: TextStyle(color: Colors.white54, fontSize: 16)),
      );
    }
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Full-screen live map button
          GestureDetector(
            onTap: () {
              Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => LiveTrackingScreen(
                  origin: _missionOrigin,
                  destination: _missionDest,
                  originCoord: LatLng(_currentLat, _currentLon),
                  destCoord: const LatLng(22.7533, 75.8937), // Hospital
                  isDriver: true,
                ),
              ));
            },
            child: Container(
              height: 300,
              decoration: BoxDecoration(
                color: Colors.grey[900],
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: kAiCyan.withOpacity(0.4)),
              ),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.map, color: kAiCyan, size: 56),
                    const SizedBox(height: 12),
                    Text('TAP FOR LIVE NAVIGATION',
                        style: GoogleFonts.rajdhani(
                            color: kAiCyan,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1)),
                    const SizedBox(height: 4),
                    Text('Real-time AI-powered routing',
                        style: GoogleFonts.rajdhani(
                            color: Colors.white54, fontSize: 12)),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              _buildMetric('ETA', '${_etaMin.toStringAsFixed(0)}m', Icons.timer),
              const SizedBox(width: 12),
              _buildMetric('Speed', '${_currentSpeed.toStringAsFixed(0)} km/h', Icons.speed),
            ],
          ),
          const Spacer(),
          if (_status == VehicleState.EN_ROUTE)
            ElevatedButton.icon(
              onPressed: () => setState(() => _status = VehicleState.AT_SCENE),
              icon: const Icon(Icons.location_on),
              label: const Text('ARRIVED ON SCENE', style: TextStyle(fontWeight: FontWeight.bold)),
              style: ElevatedButton.styleFrom(backgroundColor: kSuccess, foregroundColor: Colors.white, padding: const EdgeInsets.all(16)),
            )
          else if (_status == VehicleState.AT_SCENE)
            ElevatedButton.icon(
              onPressed: () => setState(() => _status = VehicleState.TRANSPORTING),
              icon: const Icon(Icons.local_hospital),
              label: const Text('PATIENT LOADED → HOSPITAL', style: TextStyle(fontWeight: FontWeight.bold)),
              style: ElevatedButton.styleFrom(backgroundColor: kEmergencyOrange, foregroundColor: Colors.white, padding: const EdgeInsets.all(16)),
            )
          else if (_status == VehicleState.TRANSPORTING)
            ElevatedButton.icon(
              onPressed: () => setState(() {
                _hasMission = false;
                _status = VehicleState.AVAILABLE;
              }),
              icon: const Icon(Icons.check_circle),
              label: const Text('MISSION COMPLETE', style: TextStyle(fontWeight: FontWeight.bold)),
              style: ElevatedButton.styleFrom(backgroundColor: kSuccess, foregroundColor: Colors.white, padding: const EdgeInsets.all(16)),
            ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }

  Widget _buildSceneTab() {
    if (!_hasMission) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.inbox, size: 64, color: Colors.white24),
              const SizedBox(height: 16),
              Text('No Active Mission', style: GoogleFonts.rajdhani(fontSize: 24, color: Colors.white54)),
              Text('Waiting for dispatch assignment...', style: GoogleFonts.rajdhani(color: Colors.white38)),
            ],
          ),
        ),
      );
    }
    
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: kCardBg, borderRadius: BorderRadius.circular(12), border: Border.all(color: kAiCyan)),
            child: Row(
              children: [
                const Icon(Icons.medical_services, color: kAiCyan, size: 32),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('SHARED DIGITAL SCENE', style: GoogleFonts.rajdhani(color: kAiCyan, fontWeight: FontWeight.bold)),
                      const Text('Dispatch · Vehicles · Citizens sync', style: TextStyle(color: Colors.white54, fontSize: 12)),
                    ],
                  ),
                )
              ],
            ),
          ),
          const SizedBox(height: 16),
          // Digital Dashboard
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
                const Text('Location: Bhawarkuan Square', style: TextStyle(color: Colors.white70)),
                const SizedBox(height: 4),
                Row(
                  children: [
                    const Icon(Icons.videocam, color: Colors.redAccent, size: 16),
                    const SizedBox(width: 4),
                    const Text('Caller video feed: LIVE', style: TextStyle(color: Colors.redAccent)),
                  ],
                ),
                const SizedBox(height: 4),
                const Text('Ambulance ETA: 8 minutes', style: TextStyle(color: Colors.white70)),
                const Text('Patient condition: Unknown', style: TextStyle(color: Colors.white70)),
                const Text('Hospital: City Trauma Center', style: TextStyle(color: Colors.white70)),
              ],
            ),
          ),
          
          const Divider(color: Colors.white24, height: 32),
          
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Witness Intelligence', style: TextStyle(color: Colors.white54, fontSize: 14)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: kEmergencyOrange.withOpacity(0.2), borderRadius: BorderRadius.circular(4)),
                child: const Text('2 Reports', style: TextStyle(color: kEmergencyOrange, fontSize: 10)),
              )
            ],
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Colors.black45, borderRadius: BorderRadius.circular(8)),
            child: const Row(
              children: [
                Icon(Icons.image, color: Colors.white24),
                SizedBox(width: 12),
                Expanded(child: Text('Witness photo uploaded 1m ago. Hazards identified: Fuel Leak.', style: TextStyle(color: Colors.white70, fontSize: 12))),
              ],
            ),
          ),
          
          const Spacer(),
          if (_status == VehicleState.EN_ROUTE)
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () => setState(() => _status = VehicleState.AT_SCENE),
                icon: const Icon(Icons.location_on),
                label: const Text('ARRIVED ON SCENE', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                style: ElevatedButton.styleFrom(backgroundColor: kSuccess, foregroundColor: Colors.white, padding: const EdgeInsets.all(20)),
              ),
            )
        ],
      ),
    );
  }

  Widget _buildMetric(String label, String value, IconData icon) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: kCardBg, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.white12)),
        child: Column(
          children: [
            Icon(icon, color: kAiCyan),
            const SizedBox(height: 8),
            Text(value, style: GoogleFonts.rajdhani(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
            Text(label, style: GoogleFonts.rajdhani(fontSize: 12, color: Colors.white54)),
          ],
        ),
      ),
    );
  }
}
