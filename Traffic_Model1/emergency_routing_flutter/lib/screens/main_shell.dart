import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import '../config/theme.dart';
import '../providers/health_provider.dart';
import '../providers/emergency_requests_provider.dart'; // Add this line
import 'home_screen.dart';
import 'dispatch_screen.dart';

import 'settings_screen.dart';
import 'vehicles_screen.dart';
import 'traffic_control_screen.dart';
import 'hospitals_screen.dart';
import 'analytics_screen.dart';
import 'mission_logs_screen.dart';

class MainShell extends ConsumerStatefulWidget {
  const MainShell({super.key});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(healthStateProvider.notifier).fetch();
      ref.read(modelInfoStateProvider.notifier).fetch();
    });
  }

  // The 10 requested tabs mapping
  // 1. Incoming Requests -> DispatchScreen (tab 0)
  // 2. Live Map -> HomeScreen
  // 3. Active Missions -> DispatchScreen (tab 1)
  // 4. Vehicles -> VehiclesScreen
  // 5. Traffic Control -> TrafficControlScreen
  // 6. Communication -> DispatchScreen (tab 2)
  // 7. Hospitals -> HospitalsScreen
  // 8. Analytics -> AnalyticsScreen
  // 9. Mission Logs -> MissionLogsScreen
  // 10. Settings -> SettingsScreen

  Widget _buildContent(int idx) {
    switch (idx) {
      case 0: return const DispatchScreen(initialTab: 0); // Incoming
      case 1: return const HomeScreen(); // Live Map
      case 2: return const DispatchScreen(initialTab: 1); // Active Missions
      case 3: return const VehiclesScreen();
      case 4: return const TrafficControlScreen();
      case 5: return const DispatchScreen(initialTab: 2); // Comms
      case 6: return const HospitalsScreen();
      case 7: return const AnalyticsScreen();
      case 8: return const MissionLogsScreen();
      case 9: return const SettingsScreen();
      default: return const SizedBox.shrink();
    }
  }

  @override
  Widget build(BuildContext context) {
    final idx = ref.watch(mainAppTabProvider);
    return Scaffold(
      backgroundColor: kBackground,
      body: Row(
        children: [
          _SideNav(
            selected: idx,
            onTap: (i) => ref.read(mainAppTabProvider.notifier).state = i,
          ),
          Expanded(child: _buildContent(idx)),
        ],
      ),
    );
  }
}

// ── Side Navigation Rail ───────────────────────────────────────────────────

class _SideNav extends StatelessWidget {
  final int selected;
  final ValueChanged<int> onTap;

  const _SideNav({required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 90,
      decoration: BoxDecoration(
        color: const Color(0xFF080808),
        border: Border(right: BorderSide(color: kCardBorder)),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withOpacity(0.8), blurRadius: 20)
        ],
      ),
      child: SafeArea(
        right: false,
        child: Column(
          children: [
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.88),
                shape: BoxShape.circle,
                border: Border.all(color: kEmergencyOrange.withOpacity(0.5)),
              ),
              child: const Icon(Icons.emergency_share, color: kEmergencyOrange, size: 24),
            ),
            const SizedBox(height: 24),
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  _NavItem(
                    icon: Icons.notifications_active_outlined,
                    activeIcon: Icons.notifications_active,
                    label: 'INCOMING',
                    selected: selected == 0,
                    onTap: () => onTap(0),
                    activeColor: kDanger,
                  ),
                  _NavItem(
                    icon: Icons.map_outlined,
                    activeIcon: Icons.map,
                    label: 'LIVE MAP',
                    selected: selected == 1,
                    onTap: () => onTap(1),
                    activeColor: kAiCyan,
                  ),
                  _NavItem(
                    icon: Icons.rocket_launch_outlined,
                    activeIcon: Icons.rocket_launch,
                    label: 'MISSIONS',
                    selected: selected == 2,
                    onTap: () => onTap(2),
                    activeColor: kEmergencyOrange,
                  ),
                  _NavItem(
                    icon: Icons.local_shipping_outlined,
                    activeIcon: Icons.local_shipping,
                    label: 'VEHICLES',
                    selected: selected == 3,
                    onTap: () => onTap(3),
                    activeColor: Colors.blueAccent,
                  ),
                  _NavItem(
                    icon: Icons.traffic_outlined,
                    activeIcon: Icons.traffic,
                    label: 'TRAFFIC',
                    selected: selected == 4,
                    onTap: () => onTap(4),
                    activeColor: Colors.amberAccent,
                  ),
                  _NavItem(
                    icon: Icons.chat_bubble_outline,
                    activeIcon: Icons.chat_bubble,
                    label: 'COMMS',
                    selected: selected == 5,
                    onTap: () => onTap(5),
                    activeColor: Colors.purpleAccent,
                  ),
                  _NavItem(
                    icon: Icons.local_hospital_outlined,
                    activeIcon: Icons.local_hospital,
                    label: 'HOSPITALS',
                    selected: selected == 6,
                    onTap: () => onTap(6),
                    activeColor: Colors.tealAccent,
                  ),
                  _NavItem(
                    icon: Icons.bar_chart_outlined,
                    activeIcon: Icons.bar_chart,
                    label: 'ANALYTICS',
                    selected: selected == 7,
                    onTap: () => onTap(7),
                    activeColor: Colors.pinkAccent,
                  ),
                  _NavItem(
                    icon: Icons.history_outlined,
                    activeIcon: Icons.history,
                    label: 'LOGS',
                    selected: selected == 8,
                    onTap: () => onTap(8),
                    activeColor: Colors.grey,
                  ),
                ],
              ),
            ),
            const Divider(color: Colors.white12),
            _NavItem(
              icon: Icons.settings_outlined,
              activeIcon: Icons.settings,
              label: 'SETTINGS',
              selected: selected == 9,
              onTap: () => onTap(9),
              activeColor: kAccent,
            ),
            const SizedBox(height: 12),
          ],
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final IconData activeIcon;
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final Color activeColor;

  const _NavItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
    required this.selected,
    required this.onTap,
    required this.activeColor,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: selected ? Colors.white.withOpacity(0.04) : Colors.transparent,
          border: Border(
            left: BorderSide(
              color: selected ? activeColor : Colors.transparent,
              width: 3,
            ),
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              selected ? activeIcon : icon,
              color: selected ? activeColor : kTextSecondary,
              size: 22,
            ),
            const SizedBox(height: 6),
            Text(
              label,
              style: GoogleFonts.rajdhani(
                color: selected ? activeColor : kTextSecondary,
                fontSize: 9,
                fontWeight: selected ? FontWeight.bold : FontWeight.w500,
                letterSpacing: 0.8,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
