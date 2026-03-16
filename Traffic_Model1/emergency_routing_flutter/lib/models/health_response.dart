import 'package:freezed_annotation/freezed_annotation.dart';

part 'health_response.freezed.dart';
part 'health_response.g.dart';

@freezed
class HealthResponse with _$HealthResponse {
  factory HealthResponse({
    required String status,
    @JsonKey(name: 'model_loaded') required bool modelLoaded,
    @JsonKey(name: 'cities_available') required List<String> citiesAvailable,
    @JsonKey(name: 'uptime_seconds') required double uptimeSeconds,
  }) = _HealthResponse;

  factory HealthResponse.fromJson(Map<String, dynamic> json) =>
      _$HealthResponseFromJson(json);
}
