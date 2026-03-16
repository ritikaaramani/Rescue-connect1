import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'config/theme.dart';
import 'screens/landing_screen.dart'; // import the new landing screen

const String _supabaseUrl = String.fromEnvironment(
  'SUPABASE_URL',
  defaultValue: 'https://uhlnwyrikuiprkuubloh.supabase.co',
);
const String _supabaseAnonKey = String.fromEnvironment(
  'SUPABASE_ANON_KEY',
  defaultValue: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVobG53eXJpa3VpcHJrdXVibG9oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg2ODI0MzEsImV4cCI6MjA4NDI1ODQzMX0.bNm32saAekzSO8WsWYPW3U_xxWvz5jy-ifW4CVajlrc',
);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Supabase
  try {
    await Supabase.initialize(
      url: _supabaseUrl,
      anonKey: _supabaseAnonKey,
    );
  } catch (e) {
    debugPrint('Supabase init skipped: $e');
  }

  runApp(const ProviderScope(child: EmergencyRoutingApp()));
}

class EmergencyRoutingApp extends ConsumerWidget {
  const EmergencyRoutingApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'Emergency Routing',
      theme: buildAppTheme(),
      home: const LandingScreen(), // Use LandingScreen
      debugShowCheckedModeBanner: false,
    );
  }
}
