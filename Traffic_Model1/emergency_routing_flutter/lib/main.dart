import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'config/theme.dart';
import 'screens/role_selection_screen.dart';

// Replace with your actual Supabase project URL and anon key
const String _supabaseUrl = String.fromEnvironment(
  'SUPABASE_URL',
  defaultValue: 'https://your-project.supabase.co',
);
const String _supabaseAnonKey = String.fromEnvironment(
  'SUPABASE_ANON_KEY',
  defaultValue: 'your-anon-key',
);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Supabase (non-blocking — app works without valid creds)
  try {
    await Supabase.initialize(
      url: _supabaseUrl,
      anonKey: _supabaseAnonKey,
    );
  } catch (e) {
    // Continue without Supabase if creds are placeholder
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
      home: const RoleSelectionScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}
