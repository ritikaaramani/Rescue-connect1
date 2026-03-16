import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import '../config/theme.dart';
import '../providers/health_provider.dart';
import 'home_screen.dart';
import 'dispatch_screen.dart';
import 'dashboard_screen.dart';
import 'settings_screen.dart';

class MainShell extends ConsumerStatefulWidget {
  const MainShell({super.key});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  int _idx = 0;

  static const _screens = [
    HomeScreen(),
    DispatchScreen(),
    DashboardScreen(),
    SettingsScreen(),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(healthStateProvider.notifier).fetch();
      ref.read(modelInfoStateProvider.notifier).fetch();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBackground,
      body: IndexedStack(index: _idx, children: _screens),
      bottomNavigationBar: _BottomNav(
        selected: _idx,
        onTap: (i) => setState(() => _idx = i),
      ),
    );
  }
}

// ── Bottom nav bar ─────────────────────────────────────────────────────────

class _BottomNav extends StatelessWidget {
  final int selected;
  final ValueChanged<int> onTap;

  const _BottomNav({required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF080808),
        border: Border(top: BorderSide(color: kCardBorder)),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withOpacity(0.8), blurRadius: 20)
        ],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 62,
          child: Row(
            children: [
              _NavItem(
                icon: Icons.map_outlined,
                activeIcon: Icons.map,
                label: 'RESPOND',
                selected: selected == 0,
                onTap: () => onTap(0),
                activeColor: kEmergencyOrange,
              ),
              _NavItem(
                icon: Icons.local_shipping_outlined,
                activeIcon: Icons.local_shipping,
                label: 'DISPATCH',
                selected: selected == 1,
                onTap: () => onTap(1),
                activeColor: kDanger,
              ),
              _NavItem(
                icon: Icons.bar_chart_outlined,
                activeIcon: Icons.bar_chart,
                label: 'FORECAST',
                selected: selected == 2,
                onTap: () => onTap(2),
                activeColor: kAiCyan,
              ),
              _NavItem(
                icon: Icons.settings_outlined,
                activeIcon: Icons.settings,
                label: 'SYSTEM',
                selected: selected == 3,
                onTap: () => onTap(3),
                activeColor: kAccent,
              ),
            ],
          ),
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
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Indicator dot
              AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                width: selected ? 28 : 0,
                height: selected ? 3 : 0,
                margin: const EdgeInsets.only(bottom: 4),
                decoration: BoxDecoration(
                  color: activeColor,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              Icon(
                selected ? activeIcon : icon,
                color: selected ? activeColor : kTextSecondary,
                size: 22,
              ),
              const SizedBox(height: 3),
              Text(
                label,
                style: GoogleFonts.rajdhani(
                  color: selected ? activeColor : kTextSecondary,
                  fontSize: 9,
                  fontWeight:
                      selected ? FontWeight.bold : FontWeight.w500,
                  letterSpacing: 0.8,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
