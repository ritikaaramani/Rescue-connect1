import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// Core background
const Color kBackground = Color(0xFF0A0A0A);
const Color kCardBg = Color(0xFF111111);
const Color kCardBorder = Color(0xFF1E1E1E);
const Color kTextPrimary = Color(0xFFFFFFFF);
const Color kTextSecondary = Color(0xFF888888);

// Emergency / accent colors (Rapido-inspired)
const Color kAccent = Color(0xFF4A9EFF);
const Color kAccentDim = Color(0xFF1A3A5C);
const Color kEmergencyOrange = Color(0xFFFF6B35);  // primary CTA - like Rapido
const Color kAiCyan = Color(0xFF00D4FF);            // AI model indicators

// Route / congestion colors
const Color kSuccess = Color(0xFF00E676);
const Color kWarning = Color(0xFFFFD600);
const Color kDanger = Color(0xFFFF1744);

Color getCongestionColor(double score) {
  if (score < 0.3) return kSuccess;
  if (score < 0.6) return kWarning;
  return kDanger;
}

String getCongestionLabel(double score) {
  if (score < 0.3) return 'Clear';
  if (score < 0.6) return 'Moderate Traffic';
  return 'Heavy Congestion';
}

String getCongestionMessage(double score) {
  if (score < 0.3) return 'Route is clear. Safe to proceed.';
  if (score < 0.6) return 'Moderate traffic ahead. Caution advised.';
  return 'Heavy congestion detected. Consider alternate route.';
}

String formatLatency(double ms) {
  if (ms < 1000) return '${ms.toStringAsFixed(0)}ms';
  return '${(ms / 1000).toStringAsFixed(1)}s';
}

String formatUptime(double seconds) {
  final h = (seconds / 3600).floor();
  final m = ((seconds % 3600) / 60).floor();
  final s = (seconds % 60).floor();
  return '${h}h ${m}m ${s}s';
}

ThemeData buildAppTheme() {
  return ThemeData(
    scaffoldBackgroundColor: kBackground,
    colorScheme: const ColorScheme.dark(
      primary: kEmergencyOrange,
      secondary: kAiCyan,
      surface: kCardBg,
    ),
    fontFamily: GoogleFonts.rajdhani().fontFamily,
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.transparent,
      elevation: 0,
      foregroundColor: kTextPrimary,
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: kCardBg,
      indicatorColor: kEmergencyOrange.withOpacity(0.2),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) return const TextStyle(color: kEmergencyOrange, fontSize: 11, fontWeight: FontWeight.bold);
        return const TextStyle(color: kTextSecondary, fontSize: 11);
      }),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) return const IconThemeData(color: kEmergencyOrange);
        return const IconThemeData(color: kTextSecondary);
      }),
    ),
    cardTheme: const CardThemeData(
      color: kCardBg,
      elevation: 0,
      shape: RoundedRectangleBorder(
        side: BorderSide(color: kCardBorder),
        borderRadius: BorderRadius.all(Radius.circular(16)),
      ),
    ),
    textTheme: const TextTheme(
      bodyLarge: TextStyle(color: kTextPrimary),
      bodyMedium: TextStyle(color: kTextPrimary),
    ),
  );
}
