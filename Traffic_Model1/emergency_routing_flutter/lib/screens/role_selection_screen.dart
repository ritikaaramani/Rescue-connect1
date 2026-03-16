import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../config/theme.dart';
import 'main_shell.dart';
import 'vehicle_app_screen.dart';
import 'citizen_app_screen.dart';

class RoleSelectionScreen extends StatelessWidget {
  const RoleSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF0A0A0A), Color(0xFF1A1A1A)],
          ),
        ),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 800),
            child: Padding(
              padding: const EdgeInsets.all(32.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.health_and_safety, size: 80, color: kEmergencyOrange),
                  const SizedBox(height: 24),
                  Text(
                    'EMERGENCY RESPONSE PLATFORM',
                    style: GoogleFonts.rajdhani(
                      color: Colors.white,
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 2,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Select your operational role to begin',
                    style: GoogleFonts.rajdhani(
                      color: Colors.white70,
                      fontSize: 18,
                    ),
                  ),
                  const SizedBox(height: 60),
                  
                  // Role Buttons
                  _buildRoleButton(
                    context,
                    title: 'DISPATCH COMMAND CENTER',
                    subtitle: '10-Tab Ops Dashboard | Map | Vehicles | Analytics',
                    icon: Icons.monitor,
                    color: kAiCyan,
                    onTap: () => _navigateTo(context, const MainShell()),
                  ),
                  const SizedBox(height: 20),
                  
                  _buildRoleButton(
                    context,
                    title: 'EMERGENCY VEHICLE APP',
                    subtitle: 'Driver Interface | Navigation | Mission Details',
                    icon: Icons.local_shipping,
                    color: Colors.greenAccent,
                    onTap: () => _navigateTo(context, const VehicleAppScreen()),
                  ),
                  const SizedBox(height: 20),
                  
                  _buildRoleButton(
                    context,
                    title: 'CITIZEN REPORTER',
                    subtitle: 'Report Incidents | Witness Media | Hazard Tags',
                    icon: Icons.person_pin,
                    color: Colors.orangeAccent,
                    onTap: () => _navigateTo(context, const CitizenAppScreen()),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRoleButton(BuildContext context, {required String title, required String subtitle, required IconData icon, required Color color, required VoidCallback onTap}) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: color.withOpacity(0.05),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: color.withOpacity(0.3), width: 2),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, color: color, size: 36),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: GoogleFonts.rajdhani(
                        color: Colors.white,
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.5,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: GoogleFonts.rajdhani(
                        color: Colors.white70,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.arrow_forward_ios, color: color.withOpacity(0.5)),
            ],
          ),
        ),
      ),
    );
  }

  void _navigateTo(BuildContext context, Widget screen) {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => screen),
    );
  }
}
