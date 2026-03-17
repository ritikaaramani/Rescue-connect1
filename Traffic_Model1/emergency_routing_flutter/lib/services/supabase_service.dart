import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

/// Model representing a citizen disaster post from Supabase
class CitizenPost {
  final String id;
  final String caption;
  final int severity;
  final double lat;
  final double lon;
  final String dispatchStatus;
  final String createdAt;
  final String disasterType;

  const CitizenPost({
    required this.id,
    required this.caption,
    required this.severity,
    required this.lat,
    required this.lon,
    required this.dispatchStatus,
    required this.createdAt,
    required this.disasterType,
  });

  factory CitizenPost.fromJson(Map<String, dynamic> json) {
    final location = json['location'];
    double lat = 22.7533;
    double lon = 75.8937;
    if (location is Map) {
      lat = (location['lat'] ?? location['latitude'] ?? 22.7533).toDouble();
      lon = (location['lon'] ?? location['longitude'] ?? 75.8937).toDouble();
    }
    final ai = json['ai_analysis'];
    final disasterType = (ai is Map ? ai['disaster_type'] : null) ?? 'disaster';
    return CitizenPost(
      id: json['id']?.toString() ?? '',
      caption: json['caption']?.toString() ?? '',
      severity: (json['severity'] ?? 0) as int,
      lat: lat,
      lon: lon,
      dispatchStatus: json['dispatch_status']?.toString() ?? 'pending',
      createdAt: json['created_at']?.toString() ?? '',
      disasterType: disasterType.toString(),
    );
  }

  String get severityLabel {
    if (severity >= 8) return 'CRITICAL';
    if (severity >= 6) return 'HIGH';
    if (severity >= 4) return 'MEDIUM';
    return 'LOW';
  }

  bool get isPending => dispatchStatus == 'pending';
}

/// Service that fetches citizen disaster posts via the backend proxy
/// (which in turn reads from Supabase)
class SupabaseService {
  final String _backendUrl;

  SupabaseService({String backendUrl = 'http://127.0.0.1:9000'})
      : _backendUrl = backendUrl;

  /// Fetch recent citizen posts (proxied through routing backend)
  Future<List<CitizenPost>> getCitizenPosts({
    int severityMin = 1,
    int limit = 20,
  }) async {
    try {
      final uri = Uri.parse('$_backendUrl/citizen/posts').replace(
        queryParameters: {
          'severity_min': severityMin.toString(),
          'limit': limit.toString(),
        },
      );
      final response = await http.get(uri).timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final posts = (data['posts'] as List? ?? [])
            .map((p) => CitizenPost.fromJson(p as Map<String, dynamic>))
            .toList();
        return posts;
      }
      return [];
    } catch (e) {
      debugPrint('SupabaseService.getCitizenPosts error: $e');
      return [];
    }
  }

  /// Mark a citizen post as dispatched (called after emergency dispatch)
  Future<bool> markPostDispatched(String postId) async {
    try {
      final response = await http
          .post(
            Uri.parse('$_backendUrl/supabase/post/$postId/dispatch'),
          )
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('SupabaseService.markPostDispatched error: $e');
      return false;
    }
  }

  /// Fetch only high-severity pending posts (severity >= 6)
  Future<List<CitizenPost>> getHighSeverityPosts() =>
      getCitizenPosts(severityMin: 6);
}

// -- Riverpod Providers ------------------------------------------------------

final supabaseServiceProvider = Provider<SupabaseService>((ref) {
  return SupabaseService();
});

/// Auto-refreshing stream of citizen posts (polls every 15 seconds)
final citizenPostsProvider =
    StreamProvider<List<CitizenPost>>((ref) async* {
  final service = ref.watch(supabaseServiceProvider);
  while (true) {
    yield await service.getHighSeverityPosts();
    await Future.delayed(const Duration(seconds: 15));
  }
});
