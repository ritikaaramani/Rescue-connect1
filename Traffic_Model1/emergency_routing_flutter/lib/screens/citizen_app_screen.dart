import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import '../services/backend_service.dart';
import '../config/theme.dart';

class CitizenAppScreen extends ConsumerStatefulWidget {
  const CitizenAppScreen({super.key});

  @override
  ConsumerState<CitizenAppScreen> createState() => _CitizenAppScreenState();
}

class _CitizenAppScreenState extends ConsumerState<CitizenAppScreen> {
  String _selectedType = 'Accident';
  bool _isSmartWitnessMode = false;
  bool _locationInferred = false;
  bool _isReported = false;
  bool _isInferring = false;
  bool _isReporting = false;
  String _inferredAddress = '';
  // Default is a fallback only — we prefer device GPS.
  List<double> _currentLocation = [12.9716, 77.5946]; // Default Bengaluru
  bool _hasGpsFix = false;

  final List<String> _types = ['Accident', 'Fire', 'Medical', 'Hazard', 'Protest'];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initGps();
    });
  }

  Future<void> _initGps() async {
    try {
      final enabled = await Geolocator.isLocationServiceEnabled();
      if (!enabled) return;

      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
        return;
      }

      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 8),
      );
      if (!mounted) return;
      setState(() {
        _currentLocation = [pos.latitude, pos.longitude];
        _hasGpsFix = true;
      });
    } catch (_) {
      // Keep fallback location
    }
  }

  Future<void> _inferLocation() async {
    setState(() => _isInferring = true);
    final backend = ref.read(backendServiceProvider);
    
    // In a real app, we'd pick an image. Here we simulate with the API.
    final result = await backend.inferLocationFromPhoto(
      fallbackLat: _currentLocation[0],
      fallbackLon: _currentLocation[1],
    );

    if (mounted) {
      setState(() {
        _isInferring = false;
        if (result['inferred_location'] != null) {
          _locationInferred = true;
          _inferredAddress = result['address'] ?? 'Detected Location';
          _currentLocation = List<double>.from(result['inferred_location']);
        }
      });
    }
  }

  Future<void> _reportEmergency() async {
    setState(() => _isReporting = true);
    final backend = ref.read(backendServiceProvider);
    
    final result = await backend.reportIncident(
      incidentId: 'incident_${DateTime.now().millisecondsSinceEpoch}',
      reporterId: 'citizen_user_1',
      location: _currentLocation,
      type: _selectedType.toLowerCase(),
      severity: 8, // High by default
      description: 'Emergency reported by citizen witness',
    );

    if (mounted) {
      setState(() {
        _isReporting = false;
        _isReported = true;
      });
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Reported: ${result['message'] ?? 'Success'}')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: Text(_isReported ? 'INCIDENT #284 LIVE' : 'CITIZEN RESCUE', style: GoogleFonts.rajdhani(letterSpacing: 2, fontWeight: FontWeight.bold)),
        backgroundColor: kCardBg,
        elevation: 0,
        actions: [
          if (!_isReported)
            IconButton(
              icon: Icon(_isSmartWitnessMode ? Icons.remove_red_eye : Icons.add_circle, color: kEmergencyOrange),
              onPressed: () {
                setState(() {
                  _isSmartWitnessMode = !_isSmartWitnessMode;
                });
              },
              tooltip: 'Toggle Smart Witness Mode',
            )
        ],
      ),
      body: _isReported ? _buildPostReportDashboard() : _buildReportingForm(),
    );
  }

  Widget _buildReportingForm() {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Mock Map View
          Container(
            height: 250,
            width: double.infinity,
            color: Colors.grey[900],
            child: Stack(
              alignment: Alignment.center,
              children: [
                const Text('Live Location Map', style: TextStyle(color: Colors.white24)),
                Icon(Icons.person_pin_circle, size: 48, color: _isSmartWitnessMode ? kAiCyan : kEmergencyOrange),
                Positioned(
                  bottom: 14,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: kCardBg.withOpacity(0.9),
                      borderRadius: BorderRadius.circular(999),
                      border: Border.all(color: _hasGpsFix ? kSuccess : kWarning),
                    ),
                    child: Text(
                      _hasGpsFix
                          ? 'GPS: ${_currentLocation[0].toStringAsFixed(4)}, ${_currentLocation[1].toStringAsFixed(4)}'
                          : 'GPS not available — using fallback',
                      style: GoogleFonts.rajdhani(
                        color: _hasGpsFix ? kSuccess : kWarning,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),
                if (_isSmartWitnessMode)
                  Positioned(
                    top: 16,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(color: kCardBg.withOpacity(0.9), borderRadius: BorderRadius.circular(20), border: Border.all(color: kAiCyan)),
                      child: Row(
                        children: [
                          const Icon(Icons.warning_amber, size: 16, color: kAiCyan),
                          const SizedBox(width: 8),
                          Text('INCIDENT NEARBY', style: GoogleFonts.rajdhani(color: kAiCyan, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                  )
              ],
            ),
          ),
          
          Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (!_isSmartWitnessMode) ...[
                  // AI Location Fallback feature
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.blueAccent.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.blueAccent.withOpacity(0.3)),
                    ),
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.auto_awesome, color: Colors.blueAccent, size: 18),
                            const SizedBox(width: 8),
                            Text('GPS Weak? Use AI Location', style: GoogleFonts.rajdhani(color: Colors.blueAccent, fontWeight: FontWeight.bold, fontSize: 16)),
                          ],
                        ),
                        const SizedBox(height: 12),
                        if (!_locationInferred)
                          _isInferring 
                            ? const CircularProgressIndicator(color: Colors.blueAccent)
                            : ElevatedButton.icon(
                                onPressed: _inferLocation,
                                icon: const Icon(Icons.camera_alt),
                                label: const Text('Snap Landmarks to Infer Location'),
                                style: ElevatedButton.styleFrom(backgroundColor: Colors.blueAccent.withOpacity(0.2), foregroundColor: Colors.blueAccent, elevation: 0),
                              )
                        else ...[
                          const Icon(Icons.check_circle, color: Colors.greenAccent, size: 32),
                          const SizedBox(height: 8),
                          const Text('Possible location detected:', style: TextStyle(color: Colors.white70, fontSize: 12)),
                          Text(_inferredAddress, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                          const SizedBox(height: 4),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(color: Colors.green.withOpacity(0.2), borderRadius: BorderRadius.circular(4)),
                            child: const Text('Accuracy: 85%', style: TextStyle(color: Colors.greenAccent, fontSize: 11, fontWeight: FontWeight.bold)),
                          ),
                          const SizedBox(height: 12),
                          TextButton(
                            onPressed: () => setState(() => _locationInferred = false),
                            child: const Text('RETAKE PHOTO', style: TextStyle(color: Colors.white38)),
                          )
                        ]
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                
                  Text('Type of Emergency', style: GoogleFonts.rajdhani(color: Colors.white54, fontSize: 16)),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _types.map((t) => ChoiceChip(
                      label: Text(t, style: GoogleFonts.rajdhani(fontWeight: FontWeight.bold)),
                      selected: _selectedType == t,
                      onSelected: (val) => setState(() => _selectedType = t),
                      backgroundColor: kBackground,
                      selectedColor: kEmergencyOrange.withOpacity(0.2),
                      labelStyle: TextStyle(color: _selectedType == t ? kEmergencyOrange : Colors.white),
                      side: BorderSide(color: _selectedType == t ? kEmergencyOrange : Colors.white24),
                    )).toList(),
                  ),
                  const SizedBox(height: 24),
                ],

                if (_isSmartWitnessMode) ...[
                  Text('SMART WITNESS MODE', style: GoogleFonts.rajdhani(color: kAiCyan, fontSize: 20, fontWeight: FontWeight.bold, letterSpacing: 1)),
                  Text('You are within 200m of an active incident. Please help responders with live context.', style: TextStyle(color: Colors.white70, fontSize: 14)),
                  const SizedBox(height: 24),
                ],

                Text('Context & Media', style: GoogleFonts.rajdhani(color: Colors.white54, fontSize: 16)),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _buildMediaButton(Icons.camera_alt, 'Take Photo', kAiCyan),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _buildMediaButton(Icons.videocam, 'Record Video', kAiCyan),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                TextField(
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: _isSmartWitnessMode ? 'Add hazard tags or notes...' : 'Additional details...',
                    hintStyle: const TextStyle(color: Colors.white38),
                    filled: true,
                    fillColor: kCardBg,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  ),
                  maxLines: 3,
                ),
                const SizedBox(height: 32),

                SizedBox(
                    width: double.infinity,
                    height: 56,
                    child: ElevatedButton(
                      onPressed: _isReporting ? null : _reportEmergency,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _isSmartWitnessMode ? kAiCyan : kDanger,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: _isReporting 
                        ? const CircularProgressIndicator(color: Colors.white)
                        : Text(
                            _isSmartWitnessMode ? 'SUBMIT WITNESS REPORT' : 'REPORT EMERGENCY',
                            style: GoogleFonts.rajdhani(fontSize: 20, fontWeight: FontWeight.bold, letterSpacing: 2),
                          ),
                    ),
                  )
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPostReportDashboard() {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Status Banner
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.redAccent.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.redAccent.withOpacity(0.3)),
            ),
            child: Row(
              children: [
                const SizedBox(
                  width: 24, height: 24,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.redAccent),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('RESCUE IN PROGRESS', style: GoogleFonts.rajdhani(color: Colors.redAccent, fontWeight: FontWeight.bold, letterSpacing: 1)),
                      const Text('Dispatch is assigning a vehicle...', style: TextStyle(color: Colors.white70, fontSize: 12)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 24),
          
          // Shared Situation Room
          Text('SHARED SITUATION ROOM', style: GoogleFonts.rajdhani(color: Colors.blueAccent, fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: kCardBg,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.blueAccent.withOpacity(0.2)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.videocam, color: Colors.redAccent, size: 18),
                    const SizedBox(width: 8),
                    const Text('Live Video Feed: ACTIVE', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold)),
                  ],
                ),
                const SizedBox(height: 16),
                _buildDashboardRow(Icons.timer, 'Ambulance ETA', '4 minutes'),
                _buildDashboardRow(Icons.health_and_safety, 'Patient Condition', 'Awaiting Update'),
                _buildDashboardRow(Icons.local_hospital, 'Assigned Hospital', 'City Trauma Center'),
              ],
            ),
          ),
          
          const SizedBox(height: 24),
          
          // Smart Witness Contributions
          Text('YOUR CONTRIBUTIONS', style: GoogleFonts.rajdhani(color: kAiCyan, fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Colors.white.withOpacity(0.05), borderRadius: BorderRadius.circular(12)),
            child: Row(
              children: [
                const Icon(Icons.check_circle, color: kAiCyan, size: 20),
                const SizedBox(width: 12),
                const Expanded(child: Text('Your photo and hazard tags have been shared with responders.', style: TextStyle(color: Colors.white70, fontSize: 12))),
              ],
            ),
          ),
          
          const Spacer(),
          
          SizedBox(
            width: double.infinity,
            child: TextButton.icon(
              onPressed: () => setState(() => _isReported = false),
              icon: const Icon(Icons.cancel, color: Colors.white38),
              label: const Text('CANCEL EMERGENCY', style: TextStyle(color: Colors.white38)),
            ),
          )
        ],
      ),
    );
  }

  Widget _buildDashboardRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12.0),
      child: Row(
        children: [
          Icon(icon, color: Colors.white38, size: 16),
          const SizedBox(width: 12),
          Text('$label:', style: const TextStyle(color: Colors.white54, fontSize: 13)),
          const SizedBox(width: 8),
          Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
        ],
      ),
    );
  }

  Widget _buildMediaButton(IconData icon, String label, Color color) {
    return Container(
      height: 80,
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 32),
          const SizedBox(height: 8),
          Text(label, style: GoogleFonts.rajdhani(color: Colors.white, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
