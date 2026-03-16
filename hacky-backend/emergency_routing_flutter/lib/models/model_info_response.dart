import 'package:freezed_annotation/freezed_annotation.dart';

part 'model_info_response.freezed.dart';
part 'model_info_response.g.dart';

@freezed
class ModelInfoResponse with _$ModelInfoResponse {
  factory ModelInfoResponse({
    @JsonKey(name: 'model_name') required String modelName,
    @JsonKey(name: 'lstm_hidden_size') required int lstmHiddenSize,
    @JsonKey(name: 'gcn_hidden_dim') required int gcnHiddenDim,
    @JsonKey(name: 'num_prediction_horizons') required int numPredictionHorizons,
    @JsonKey(name: 'checkpoint_path') required String checkpointPath,
    @JsonKey(name: 'parameter_count') required int parameterCount,
  }) = _ModelInfoResponse;

  factory ModelInfoResponse.fromJson(Map<String, dynamic> json) =>
      _$ModelInfoResponseFromJson(json);
}
