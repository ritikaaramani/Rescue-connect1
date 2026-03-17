import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';

import 'citizen_app_screen.dart';
import 'main_shell.dart';
import 'vehicle_app_screen.dart';

class LandingScreen extends StatelessWidget {
  const LandingScreen({super.key});

  void _navigateTo(BuildContext context, Widget screen) {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => screen),
    );
  }

  Future<void> _launchURL(String urlString) async {
    final Uri url = Uri.parse(urlString);
    if (!await launchUrl(url)) {
      debugPrint('Could not launch $url');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF111827), // gray-900
      body: Stack(
        children: [
          // Background Image
          Positioned.fill(
            child: Image.asset(
              'assets/hero-rescue.png',
              fit: BoxFit.cover,
            ),
          ),
          // Gradients for readability
          Positioned.fill(
            child: Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Color(0xFF111827),
                    Color(0xCC111827),
                    Colors.transparent,
                  ],
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                  stops: [0.0, 0.5, 1.0],
                ),
              ),
            ),
          ),
          Positioned.fill(
            child: Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Color(0x80111827),
                    Colors.transparent,
                    Color(0xFF111827),
                  ],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  stops: [0.0, 0.5, 1.0],
                ),
              ),
            ),
          ),
          
          // Content
          LayoutBuilder(
            builder: (context, constraints) {
              return SingleChildScrollView(
                child: ConstrainedBox(
                  constraints: BoxConstraints(
                    minHeight: constraints.maxHeight,
                  ),
                  child: IntrinsicHeight(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Navbar
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 48, vertical: 24),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Center(
                        child: Icon(Icons.add_circle, color: Colors.red, size: 24),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      'RescueConnect',
                      style: GoogleFonts.inter(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                        letterSpacing: -0.5,
                      ),
                    ),
                  ],
                ),
              ),
              
              const Spacer(),
              
              // Hero Content
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 48),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            color: Colors.red,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'LIVE DISASTER RESPONSE',
                          style: GoogleFonts.inter(
                            color: Colors.redAccent,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 1.5,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 32),
                    Text(
                      'Every Second\nSaves Lives',
                      style: GoogleFonts.inter(
                        fontSize: 72,
                        height: 1.1,
                        fontWeight: FontWeight.w900,
                        color: Colors.white,
                        letterSpacing: -2,
                      ),
                    ),
                    const SizedBox(height: 24),
                    Text(
                      'AI-powered platform that turns social media posts into\ncoordinated rescue operations.',
                      style: GoogleFonts.inter(
                        fontSize: 20,
                        color: Colors.white70,
                        height: 1.5,
                        fontWeight: FontWeight.w300,
                      ),
                    ),
                    const SizedBox(height: 48),
                    
                    // Buttons
                    Row(
                      children: [
                        _buildLoginButton(
                          title: 'Login as Authority/Dispatcher',
                          onTap: () => _launchURL('http://localhost:5174'),
                        ),
                        const SizedBox(width: 16),
                        _buildLoginButton(
                          title: 'Login as Rescue Team',
                          onTap: () => _navigateTo(context, const MainShell()),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              
              const Spacer(),
              
              // Stats Bar
              Container(
                decoration: const BoxDecoration(
                  color: Color(0xCC111827),
                  border: Border(top: BorderSide(color: Color(0x1AFFFFFF))),
                ),
                padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 48),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _buildStat('847+', 'Lives Saved'),
                    _buildStat('<3 min', 'Avg Response'),
                    _buildStat('98%', 'AI Accuracy'),
                    _buildStat('24/7', 'Active Monitoring'),
                  ],
                ),
              ),
            ],
          ),
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildLoginButton({required String title, required VoidCallback onTap}) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(30),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 10,
              offset: const Offset(0, 5),
            ),
          ],
        ),
        child: Row(
          children: [
            Text(
              title,
              style: GoogleFonts.inter(
                color: const Color(0xFF111827),
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(width: 8),
            const Icon(
              Icons.arrow_forward,
              color: Color(0xFF111827),
              size: 20,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStat(String value, String label) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          value,
          style: GoogleFonts.inter(
            fontSize: 36,
            fontWeight: FontWeight.w900,
            color: Colors.white,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: GoogleFonts.inter(
            fontSize: 14,
            color: Colors.white54,
          ),
        ),
      ],
    );
  }
}
