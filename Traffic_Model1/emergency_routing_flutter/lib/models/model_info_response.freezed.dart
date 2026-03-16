// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'model_info_response.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

ModelInfoResponse _$ModelInfoResponseFromJson(Map<String, dynamic> json) {
  return _ModelInfoResponse.fromJson(json);
}

/// @nodoc
mixin _$ModelInfoResponse {
  @JsonKey(name: 'model_name')
  String get modelName => throw _privateConstructorUsedError;
  @JsonKey(name: 'lstm_hidden_size')
  int get lstmHiddenSize => throw _privateConstructorUsedError;
  @JsonKey(name: 'gcn_hidden_dim')
  int get gcnHiddenDim => throw _privateConstructorUsedError;
  @JsonKey(name: 'num_prediction_horizons')
  int get numPredictionHorizons => throw _privateConstructorUsedError;
  @JsonKey(name: 'checkpoint_path')
  String get checkpointPath => throw _privateConstructorUsedError;
  @JsonKey(name: 'parameter_count')
  int get parameterCount => throw _privateConstructorUsedError;

  /// Serializes this ModelInfoResponse to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of ModelInfoResponse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $ModelInfoResponseCopyWith<ModelInfoResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ModelInfoResponseCopyWith<$Res> {
  factory $ModelInfoResponseCopyWith(
          ModelInfoResponse value, $Res Function(ModelInfoResponse) then) =
      _$ModelInfoResponseCopyWithImpl<$Res, ModelInfoResponse>;
  @useResult
  $Res call(
      {@JsonKey(name: 'model_name') String modelName,
      @JsonKey(name: 'lstm_hidden_size') int lstmHiddenSize,
      @JsonKey(name: 'gcn_hidden_dim') int gcnHiddenDim,
      @JsonKey(name: 'num_prediction_horizons') int numPredictionHorizons,
      @JsonKey(name: 'checkpoint_path') String checkpointPath,
      @JsonKey(name: 'parameter_count') int parameterCount});
}

/// @nodoc
class _$ModelInfoResponseCopyWithImpl<$Res, $Val extends ModelInfoResponse>
    implements $ModelInfoResponseCopyWith<$Res> {
  _$ModelInfoResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of ModelInfoResponse
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? modelName = null,
    Object? lstmHiddenSize = null,
    Object? gcnHiddenDim = null,
    Object? numPredictionHorizons = null,
    Object? checkpointPath = null,
    Object? parameterCount = null,
  }) {
    return _then(_value.copyWith(
      modelName: null == modelName
          ? _value.modelName
          : modelName // ignore: cast_nullable_to_non_nullable
              as String,
      lstmHiddenSize: null == lstmHiddenSize
          ? _value.lstmHiddenSize
          : lstmHiddenSize // ignore: cast_nullable_to_non_nullable
              as int,
      gcnHiddenDim: null == gcnHiddenDim
          ? _value.gcnHiddenDim
          : gcnHiddenDim // ignore: cast_nullable_to_non_nullable
              as int,
      numPredictionHorizons: null == numPredictionHorizons
          ? _value.numPredictionHorizons
          : numPredictionHorizons // ignore: cast_nullable_to_non_nullable
              as int,
      checkpointPath: null == checkpointPath
          ? _value.checkpointPath
          : checkpointPath // ignore: cast_nullable_to_non_nullable
              as String,
      parameterCount: null == parameterCount
          ? _value.parameterCount
          : parameterCount // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$ModelInfoResponseImplCopyWith<$Res>
    implements $ModelInfoResponseCopyWith<$Res> {
  factory _$$ModelInfoResponseImplCopyWith(_$ModelInfoResponseImpl value,
          $Res Function(_$ModelInfoResponseImpl) then) =
      __$$ModelInfoResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'model_name') String modelName,
      @JsonKey(name: 'lstm_hidden_size') int lstmHiddenSize,
      @JsonKey(name: 'gcn_hidden_dim') int gcnHiddenDim,
      @JsonKey(name: 'num_prediction_horizons') int numPredictionHorizons,
      @JsonKey(name: 'checkpoint_path') String checkpointPath,
      @JsonKey(name: 'parameter_count') int parameterCount});
}

/// @nodoc
class __$$ModelInfoResponseImplCopyWithImpl<$Res>
    extends _$ModelInfoResponseCopyWithImpl<$Res, _$ModelInfoResponseImpl>
    implements _$$ModelInfoResponseImplCopyWith<$Res> {
  __$$ModelInfoResponseImplCopyWithImpl(_$ModelInfoResponseImpl _value,
      $Res Function(_$ModelInfoResponseImpl) _then)
      : super(_value, _then);

  /// Create a copy of ModelInfoResponse
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? modelName = null,
    Object? lstmHiddenSize = null,
    Object? gcnHiddenDim = null,
    Object? numPredictionHorizons = null,
    Object? checkpointPath = null,
    Object? parameterCount = null,
  }) {
    return _then(_$ModelInfoResponseImpl(
      modelName: null == modelName
          ? _value.modelName
          : modelName // ignore: cast_nullable_to_non_nullable
              as String,
      lstmHiddenSize: null == lstmHiddenSize
          ? _value.lstmHiddenSize
          : lstmHiddenSize // ignore: cast_nullable_to_non_nullable
              as int,
      gcnHiddenDim: null == gcnHiddenDim
          ? _value.gcnHiddenDim
          : gcnHiddenDim // ignore: cast_nullable_to_non_nullable
              as int,
      numPredictionHorizons: null == numPredictionHorizons
          ? _value.numPredictionHorizons
          : numPredictionHorizons // ignore: cast_nullable_to_non_nullable
              as int,
      checkpointPath: null == checkpointPath
          ? _value.checkpointPath
          : checkpointPath // ignore: cast_nullable_to_non_nullable
              as String,
      parameterCount: null == parameterCount
          ? _value.parameterCount
          : parameterCount // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$ModelInfoResponseImpl implements _ModelInfoResponse {
  _$ModelInfoResponseImpl(
      {@JsonKey(name: 'model_name') required this.modelName,
      @JsonKey(name: 'lstm_hidden_size') required this.lstmHiddenSize,
      @JsonKey(name: 'gcn_hidden_dim') required this.gcnHiddenDim,
      @JsonKey(name: 'num_prediction_horizons')
      required this.numPredictionHorizons,
      @JsonKey(name: 'checkpoint_path') required this.checkpointPath,
      @JsonKey(name: 'parameter_count') required this.parameterCount});

  factory _$ModelInfoResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$ModelInfoResponseImplFromJson(json);

  @override
  @JsonKey(name: 'model_name')
  final String modelName;
  @override
  @JsonKey(name: 'lstm_hidden_size')
  final int lstmHiddenSize;
  @override
  @JsonKey(name: 'gcn_hidden_dim')
  final int gcnHiddenDim;
  @override
  @JsonKey(name: 'num_prediction_horizons')
  final int numPredictionHorizons;
  @override
  @JsonKey(name: 'checkpoint_path')
  final String checkpointPath;
  @override
  @JsonKey(name: 'parameter_count')
  final int parameterCount;

  @override
  String toString() {
    return 'ModelInfoResponse(modelName: $modelName, lstmHiddenSize: $lstmHiddenSize, gcnHiddenDim: $gcnHiddenDim, numPredictionHorizons: $numPredictionHorizons, checkpointPath: $checkpointPath, parameterCount: $parameterCount)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ModelInfoResponseImpl &&
            (identical(other.modelName, modelName) ||
                other.modelName == modelName) &&
            (identical(other.lstmHiddenSize, lstmHiddenSize) ||
                other.lstmHiddenSize == lstmHiddenSize) &&
            (identical(other.gcnHiddenDim, gcnHiddenDim) ||
                other.gcnHiddenDim == gcnHiddenDim) &&
            (identical(other.numPredictionHorizons, numPredictionHorizons) ||
                other.numPredictionHorizons == numPredictionHorizons) &&
            (identical(other.checkpointPath, checkpointPath) ||
                other.checkpointPath == checkpointPath) &&
            (identical(other.parameterCount, parameterCount) ||
                other.parameterCount == parameterCount));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, modelName, lstmHiddenSize,
      gcnHiddenDim, numPredictionHorizons, checkpointPath, parameterCount);

  /// Create a copy of ModelInfoResponse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$ModelInfoResponseImplCopyWith<_$ModelInfoResponseImpl> get copyWith =>
      __$$ModelInfoResponseImplCopyWithImpl<_$ModelInfoResponseImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ModelInfoResponseImplToJson(
      this,
    );
  }
}

abstract class _ModelInfoResponse implements ModelInfoResponse {
  factory _ModelInfoResponse(
      {@JsonKey(name: 'model_name') required final String modelName,
      @JsonKey(name: 'lstm_hidden_size') required final int lstmHiddenSize,
      @JsonKey(name: 'gcn_hidden_dim') required final int gcnHiddenDim,
      @JsonKey(name: 'num_prediction_horizons')
      required final int numPredictionHorizons,
      @JsonKey(name: 'checkpoint_path') required final String checkpointPath,
      @JsonKey(name: 'parameter_count')
      required final int parameterCount}) = _$ModelInfoResponseImpl;

  factory _ModelInfoResponse.fromJson(Map<String, dynamic> json) =
      _$ModelInfoResponseImpl.fromJson;

  @override
  @JsonKey(name: 'model_name')
  String get modelName;
  @override
  @JsonKey(name: 'lstm_hidden_size')
  int get lstmHiddenSize;
  @override
  @JsonKey(name: 'gcn_hidden_dim')
  int get gcnHiddenDim;
  @override
  @JsonKey(name: 'num_prediction_horizons')
  int get numPredictionHorizons;
  @override
  @JsonKey(name: 'checkpoint_path')
  String get checkpointPath;
  @override
  @JsonKey(name: 'parameter_count')
  int get parameterCount;

  /// Create a copy of ModelInfoResponse
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$ModelInfoResponseImplCopyWith<_$ModelInfoResponseImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
