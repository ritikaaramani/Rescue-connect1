import 'package:freezed_annotation/freezed_annotation.dart';

part 'model_info_response.freezed.dart';
part 'model_info_response.g.dart';

@freezed
class ModelInfoResponse with _$ModelInfoResponse {
  factory ModelInfoResponse({
    required String modelName,
    required int lstmHiddenSize,
    required int gcnHiddenDim,
    required int numPredictionHorizons,
    required String checkpointPath,
    required int parameterCount,
  }) = _ModelInfoResponse;

  factory ModelInfoResponse.fromJson(Map<String, dynamic> json) =>
      _$ModelInfoResponseFromJson(json);
}
