// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'model_info_response.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$ModelInfoResponseImpl _$$ModelInfoResponseImplFromJson(
        Map<String, dynamic> json) =>
    _$ModelInfoResponseImpl(
      modelName: json['model_name'] as String,
      lstmHiddenSize: (json['lstm_hidden_size'] as num).toInt(),
      gcnHiddenDim: (json['gcn_hidden_dim'] as num).toInt(),
      numPredictionHorizons: (json['num_prediction_horizons'] as num).toInt(),
      checkpointPath: json['checkpoint_path'] as String,
      parameterCount: (json['parameter_count'] as num).toInt(),
    );

Map<String, dynamic> _$$ModelInfoResponseImplToJson(
        _$ModelInfoResponseImpl instance) =>
    <String, dynamic>{
      'model_name': instance.modelName,
      'lstm_hidden_size': instance.lstmHiddenSize,
      'gcn_hidden_dim': instance.gcnHiddenDim,
      'num_prediction_horizons': instance.numPredictionHorizons,
      'checkpoint_path': instance.checkpointPath,
      'parameter_count': instance.parameterCount,
    };
