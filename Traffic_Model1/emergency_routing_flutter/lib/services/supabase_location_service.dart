import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// Represents a location update received from the authority dashboard.
/// Contains the full incident details extracted by the ML model.
class IncidentLocationUpdate {
  final String postId;
  final String locationLabel;
  final LatLng incidentCoord;
  final LatLng? hospitalCoord;
  final String? hospitalName;
  final String disasterType;
  final String severity;
  final DateTime receivedAt;

  IncidentLocationUpdate({
    required this.postId,
    required this.locationLabel,
    required this.incidentCoord,
    this.hospitalCoord,
    this.hospitalName,
    required this.disasterType,
    required this.severity,
    required this.receivedAt,
  });

  @override
  String toString() =>
      'IncidentLocationUpdate(id: $postId, type: $disasterType, coord: $incidentCoord)';
}

/// Service that subscribes to Supabase Realtime for ML-extracted location updates
/// coming from the authority dashboard. Exposes a stream of [IncidentLocationUpdate].
class SupabaseLocationService {
  final SupabaseClient _supabase = Supabase.instance.client;

  RealtimeChannel? _channel;
  final _locationController = StreamController<IncidentLocationUpdate>.broadcast();

  // Latest received update for quick access
  IncidentLocationUpdate? latestUpdate;

  Stream<IncidentLocationUpdate> get locationUpdates => _locationController.stream;

  /// Start listening to the `posts` table for new or updated records
  /// that have been processed by the ML model (ai_processed = true).
  void startListening() {
    _channel = _supabase
        .channel('authority-location-updates')
        .onPostgresChanges(
          event: PostgresChangeEvent.update,
          schema: 'public',
          table: 'posts',
          filter: PostgresChangeFilter(
            type: PostgresChangeFilterType.eq,
            column: 'ai_processed',
            value: true,
          ),
          callback: (payload) => _handlePostUpdate(payload.newRecord),
        )
        .onPostgresChanges(
          event: PostgresChangeEvent.insert,
          schema: 'public',
          table: 'posts',
          callback: (payload) {
            final record = payload.newRecord;
            if (record['ai_processed'] == true) {
              _handlePostUpdate(record);
            }
          },
        )
        .subscribe((status, [error]) {
          if (status == RealtimeSubscribeStatus.subscribed) {
            print('✅ Supabase Realtime: Listening for ML location updates');
          } else if (error != null) {
            print('❌ Supabase Realtime error: $error');
          }
        });
  }

  void _handlePostUpdate(Map<String, dynamic> record) {
    // Only process records with ML-extracted coordinates
    final inferredLat = _toDouble(record['inferred_latitude']);
    final inferredLon = _toDouble(record['inferred_longitude']);

    if (inferredLat == null || inferredLon == null) {
      // No coordinates yet — ignore this update
      return;
    }

    // Build location label from extracted_locations or fallback
    String locationLabel = 'Detected Location';
    final extractedLocs = record['extracted_locations'];
    if (extractedLocs is List && extractedLocs.isNotEmpty) {
      locationLabel = extractedLocs[0].toString();
    } else if (record['location'] is String &&
        (record['location'] as String).isNotEmpty) {
      locationLabel = record['location'];
    }

    final update = IncidentLocationUpdate(
      postId: record['id'].toString(),
      locationLabel: locationLabel,
      incidentCoord: LatLng(inferredLat, inferredLon),
      disasterType: record['disaster_type']?.toString() ?? 'Emergency',
      severity: record['severity']?.toString() ?? 'unknown',
      receivedAt: DateTime.now(),
    );

    latestUpdate = update;
    _locationController.add(update);

    print('📍 New ML location received: ${update.locationLabel} '
        '(${inferredLat.toStringAsFixed(5)}, ${inferredLon.toStringAsFixed(5)})');
  }

  double? _toDouble(dynamic value) {
    if (value == null) return null;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }

  /// Fetch recent unresolved incidents with ML coordinates via REST (on-demand).
  Future<List<IncidentLocationUpdate>> fetchRecentIncidents({int limit = 20}) async {
    try {
      // Join hospital to get destination coordinates too
      final response = await _supabase
          .from('posts')
          .select('*, destination_hospital:hospitals!destination_hospital_id(id,name,latitude,longitude)')
          .eq('ai_processed', true)
          .neq('dispatch_status', 'resolved')
          .inFilter('status', ['urgent', 'verified'])
          .not('inferred_latitude', 'is', null)
          .not('inferred_longitude', 'is', null)
          .order('created_at', ascending: false)
          .limit(limit);

      return (response as List).map((record) {
        final lat = _toDouble(record['inferred_latitude']) ?? 22.7196;
        final lon = _toDouble(record['inferred_longitude']) ?? 75.8577;

        // Hospital destination
        LatLng? hospitalCoord;
        String? hospitalName;
        final hospital = record['destination_hospital'];
        if (hospital is Map) {
          final hLat = _toDouble(hospital['latitude']);
          final hLon = _toDouble(hospital['longitude']);
          if (hLat != null && hLon != null) {
            hospitalCoord = LatLng(hLat, hLon);
          }
          hospitalName = hospital['name']?.toString();
        }

        String locationLabel = 'Detected Location';
        final extractedLocs = record['extracted_locations'];
        if (extractedLocs is List && extractedLocs.isNotEmpty) {
          locationLabel = extractedLocs[0].toString();
        } else if (record['location'] is String) {
          locationLabel = record['location'];
        }

        return IncidentLocationUpdate(
          postId: record['id'].toString(),
          locationLabel: locationLabel,
          incidentCoord: LatLng(lat, lon),
          hospitalCoord: hospitalCoord,
          hospitalName: hospitalName,
          disasterType: record['disaster_type']?.toString() ?? 'Emergency',
          severity: record['severity']?.toString() ?? 'unknown',
          receivedAt: DateTime.tryParse(record['created_at']?.toString() ?? '') ?? DateTime.now(),
        );
      }).toList();
    } catch (e) {
      print('❌ Error fetching recent incidents: $e');
      return [];
    }
  }

  void stopListening() {
    _channel?.unsubscribe();
    _channel = null;
  }

  void dispose() {
    stopListening();
    _locationController.close();
  }
}

// ── Providers ────────────────────────────────────────────────────────────────

final supabaseLocationServiceProvider = Provider<SupabaseLocationService>((ref) {
  final service = SupabaseLocationService();
  service.startListening();
  ref.onDispose(() => service.dispose());
  return service;
});

/// Stream provider that emits [IncidentLocationUpdate] whenever the authority
/// dashboard's ML model extracts a new location from an uploaded image.
final locationUpdateStreamProvider = StreamProvider<IncidentLocationUpdate>((ref) {
  final service = ref.watch(supabaseLocationServiceProvider);
  return service.locationUpdates;
});

class _LatestIncidentLocationNotifier extends StateNotifier<IncidentLocationUpdate?> {
  _LatestIncidentLocationNotifier(Ref ref) : super(null) {
    ref.listen<AsyncValue<IncidentLocationUpdate>>(locationUpdateStreamProvider, (_, next) {
      next.whenData((update) {
        state = update;
      });
    });
  }
}

/// Provider for the most recent incident location from any source.
/// Starts null, fills in when the first update arrives.
final latestIncidentLocationProvider =
    StateNotifierProvider<_LatestIncidentLocationNotifier, IncidentLocationUpdate?>(
  (ref) => _LatestIncidentLocationNotifier(ref),
);
