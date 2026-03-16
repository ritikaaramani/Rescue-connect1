import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../config/theme.dart';
import '../services/backend_service.dart';

class VehiclesScreen extends ConsumerStatefulWidget {
  const VehiclesScreen({super.key});

  @override
  ConsumerState<VehiclesScreen> createState() => _VehiclesScreenState();
}

class _VehiclesScreenState extends ConsumerState<VehiclesScreen> {
  List<Map<String, dynamic>> _vehicles = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchVehicles();
  }

  Future<void> _fetchVehicles() async {
    final backend = ref.read(backendServiceProvider);
    final data = await backend.getAllVehicles();
    if (mounted) {
      setState(() {
        _vehicles = data;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final available = _vehicles.where((v) => v['status'] == 'AVAILABLE').length;
    final onMission = _vehicles.where((v) => v['status'] != 'AVAILABLE' && v['status'] != 'OFFLINE').length;

    return Scaffold(
      backgroundColor: kBackground,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('VEHICLE MANAGEMENT', style: GoogleFonts.rajdhani(fontWeight: FontWeight.bold, letterSpacing: 1.5)),
        actions: [
          IconButton(icon: const Icon(Icons.refresh, color: kAiCyan), onPressed: _fetchVehicles)
        ],
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator(color: kAiCyan))
        : ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _buildStatRow(_vehicles.length.toString(), available.toString(), onMission.toString()),
              const SizedBox(height: 20),
              _buildAIRecommendBanner(),
              const SizedBox(height: 20),
              ..._vehicles.map((v) => _buildVehicleCard(
                v['id'], 
                'Rescuer ${v['id'].split('-').last}', 
                v['status'], 
                v['status'] == 'AVAILABLE' ? Colors.green : Colors.orange, 
                v['status'] == 'AVAILABLE' ? 'Stationary at base' : 'Mission in progress • ${v['speed'] ?? 0} km/h'
              )),
              if (_vehicles.isEmpty)
                const Center(child: Text('No vehicles found in registry', style: TextStyle(color: Colors.white54))),
            ],
          ),
    );
  }

  Widget _buildStatRow(String total, String avail, String mission) {
    return Row(
      children: [
        _buildStatBox(total, 'Total Fleet', kAiCyan),
        const SizedBox(width: 12),
        _buildStatBox(avail, 'Available', Colors.green),
        const SizedBox(width: 12),
        _buildStatBox(mission, 'On Mission', Colors.orange),
      ],
    );
  }

  Widget _buildStatBox(String count, String label, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(12), border: Border.all(color: color.withOpacity(0.3))),
        child: Column(
          children: [
            Text(count, style: GoogleFonts.rajdhani(fontSize: 24, fontWeight: FontWeight.bold, color: color)),
            Text(label, style: GoogleFonts.rajdhani(fontSize: 12, color: Colors.white70)),
          ],
        ),
      ),
    );
  }

  Widget _buildAIRecommendBanner() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(gradient: LinearGradient(colors: [kAiCyan.withOpacity(0.2), Colors.transparent]), borderRadius: BorderRadius.circular(12), border: Border.all(color: kAiCyan)),
      child: Row(
        children: [
          const Icon(Icons.psychology, color: kAiCyan, size: 30),
          const SizedBox(width: 12),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('AI PREDICTIVE POSITIONING', style: GoogleFonts.rajdhani(color: kAiCyan, fontWeight: FontWeight.bold)),
              Text('Suggest moving 2 units to Palasia Square due to projected 18:00 rush hour accidents.', style: GoogleFonts.rajdhani(color: Colors.white70, fontSize: 12)),
            ],
          )),
          ElevatedButton(onPressed: () {}, style: ElevatedButton.styleFrom(backgroundColor: kAiCyan, foregroundColor: Colors.black), child: const Text('DEPLOY'))
        ],
      ),
    );
  }

  Widget _buildVehicleCard(String id, String driver, String status, Color statusColor, String details) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: kCardBg, borderRadius: BorderRadius.circular(12), border: Border.all(color: kCardBorder)),
      child: Row(
        children: [
          Container(padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: Colors.white10, borderRadius: BorderRadius.circular(8)), child: const Icon(Icons.local_shipping, color: Colors.white70)),
          const SizedBox(width: 16),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(id, style: GoogleFonts.rajdhani(fontWeight: FontWeight.bold, fontSize: 18, color: Colors.white)),
                  const SizedBox(width: 8),
                  Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2), decoration: BoxDecoration(color: statusColor.withOpacity(0.2), borderRadius: BorderRadius.circular(4)), child: Text(status, style: TextStyle(color: statusColor, fontSize: 10, fontWeight: FontWeight.bold))),
                ],
              ),
              const SizedBox(height: 4),
              Text('Driver: $driver', style: GoogleFonts.rajdhani(color: Colors.white70, fontSize: 13)),
              Text(details, style: GoogleFonts.rajdhani(color: Colors.grey, fontSize: 12)),
            ],
          )),
          IconButton(icon: const Icon(Icons.location_on, color: kAiCyan), onPressed: () {}),
          IconButton(icon: const Icon(Icons.more_vert, color: Colors.white70), onPressed: () {}),
        ],
      ),
    );
  }
}
