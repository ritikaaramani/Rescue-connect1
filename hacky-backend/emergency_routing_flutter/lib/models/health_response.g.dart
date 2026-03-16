// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'health_response.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$HealthResponseImpl _$$HealthResponseImplFromJson(Map<String, dynamic> json) =>
    _$HealthResponseImpl(
      status: json['status'] as String,
      modelLoaded: json['model_loaded'] as bool,
      citiesAvailable: (json['cities_available'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      uptimeSeconds: (json['uptime_seconds'] as num).toDouble(),
    );

Map<String, dynamic> _$$HealthResponseImplToJson(
        _$HealthResponseImpl instance) =>
    <String, dynamic>{
      'status': instance.status,
      'model_loaded': instance.modelLoaded,
      'cities_available': instance.citiesAvailable,
      'uptime_seconds': instance.uptimeSeconds,
    };
