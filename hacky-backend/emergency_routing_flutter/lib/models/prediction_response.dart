import 'package:freezed_annotation/freezed_annotation.dart';

part 'prediction_response.freezed.dart';
part 'prediction_response.g.dart';

@freezed
class PredictionResponse with _$PredictionResponse {
  factory PredictionResponse({
    required String city,
    required String timestamp,
    @JsonKey(name: 'congestion_t5') required double congestionT5,
    @JsonKey(name: 'congestion_t10') required double congestionT10,
    @JsonKey(name: 'congestion_t20') required double congestionT20,
    @JsonKey(name: 'congestion_t30') required double congestionT30,
    @JsonKey(name: 'uncertainty_t5') required double uncertaintyT5,
    @JsonKey(name: 'uncertainty_t10') required double uncertaintyT10,
    @JsonKey(name: 'uncertainty_t20') required double uncertaintyT20,
    @JsonKey(name: 'uncertainty_t30') required double uncertaintyT30,
    @JsonKey(name: 'latency_ms') required double latencyMs,
  }) = _PredictionResponse;

  factory PredictionResponse.fromJson(Map<String, dynamic> json) =>
      _$PredictionResponseFromJson(json);
}
