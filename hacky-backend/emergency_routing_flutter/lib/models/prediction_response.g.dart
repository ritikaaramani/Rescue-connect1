// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'prediction_response.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$PredictionResponseImpl _$$PredictionResponseImplFromJson(
        Map<String, dynamic> json) =>
    _$PredictionResponseImpl(
      city: json['city'] as String,
      timestamp: json['timestamp'] as String,
      congestionT5: (json['congestion_t5'] as num).toDouble(),
      congestionT10: (json['congestion_t10'] as num).toDouble(),
      congestionT20: (json['congestion_t20'] as num).toDouble(),
      congestionT30: (json['congestion_t30'] as num).toDouble(),
      uncertaintyT5: (json['uncertainty_t5'] as num).toDouble(),
      uncertaintyT10: (json['uncertainty_t10'] as num).toDouble(),
      uncertaintyT20: (json['uncertainty_t20'] as num).toDouble(),
      uncertaintyT30: (json['uncertainty_t30'] as num).toDouble(),
      latencyMs: (json['latency_ms'] as num).toDouble(),
    );

Map<String, dynamic> _$$PredictionResponseImplToJson(
        _$PredictionResponseImpl instance) =>
    <String, dynamic>{
      'city': instance.city,
      'timestamp': instance.timestamp,
      'congestion_t5': instance.congestionT5,
      'congestion_t10': instance.congestionT10,
      'congestion_t20': instance.congestionT20,
      'congestion_t30': instance.congestionT30,
      'uncertainty_t5': instance.uncertaintyT5,
      'uncertainty_t10': instance.uncertaintyT10,
      'uncertainty_t20': instance.uncertaintyT20,
      'uncertainty_t30': instance.uncertaintyT30,
      'latency_ms': instance.latencyMs,
    };
