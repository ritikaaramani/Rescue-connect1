import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'config/theme.dart';
import 'screens/main_shell.dart';

void main() {
  runApp(const ProviderScope(child: EmergencyRoutingApp()));
}

class EmergencyRoutingApp extends ConsumerWidget {
  const EmergencyRoutingApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'Emergency Routing',
      theme: buildAppTheme(),
      home: const MainShell(),
      debugShowCheckedModeBanner: false,
    );
  }
}
