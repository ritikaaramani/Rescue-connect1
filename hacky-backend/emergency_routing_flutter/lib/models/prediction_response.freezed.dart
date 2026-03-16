// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'prediction_response.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

PredictionResponse _$PredictionResponseFromJson(Map<String, dynamic> json) {
  return _PredictionResponse.fromJson(json);
}

/// @nodoc
mixin _$PredictionResponse {
  String get city => throw _privateConstructorUsedError;
  String get timestamp => throw _privateConstructorUsedError;
  @JsonKey(name: 'congestion_t5')
  double get congestionT5 => throw _privateConstructorUsedError;
  @JsonKey(name: 'congestion_t10')
  double get congestionT10 => throw _privateConstructorUsedError;
  @JsonKey(name: 'congestion_t20')
  double get congestionT20 => throw _privateConstructorUsedError;
  @JsonKey(name: 'congestion_t30')
  double get congestionT30 => throw _privateConstructorUsedError;
  @JsonKey(name: 'uncertainty_t5')
  double get uncertaintyT5 => throw _privateConstructorUsedError;
  @JsonKey(name: 'uncertainty_t10')
  double get uncertaintyT10 => throw _privateConstructorUsedError;
  @JsonKey(name: 'uncertainty_t20')
  double get uncertaintyT20 => throw _privateConstructorUsedError;
  @JsonKey(name: 'uncertainty_t30')
  double get uncertaintyT30 => throw _privateConstructorUsedError;
  @JsonKey(name: 'latency_ms')
  double get latencyMs => throw _privateConstructorUsedError;

  /// Serializes this PredictionResponse to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of PredictionResponse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $PredictionResponseCopyWith<PredictionResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PredictionResponseCopyWith<$Res> {
  factory $PredictionResponseCopyWith(
          PredictionResponse value, $Res Function(PredictionResponse) then) =
      _$PredictionResponseCopyWithImpl<$Res, PredictionResponse>;
  @useResult
  $Res call(
      {String city,
      String timestamp,
      @JsonKey(name: 'congestion_t5') double congestionT5,
      @JsonKey(name: 'congestion_t10') double congestionT10,
      @JsonKey(name: 'congestion_t20') double congestionT20,
      @JsonKey(name: 'congestion_t30') double congestionT30,
      @JsonKey(name: 'uncertainty_t5') double uncertaintyT5,
      @JsonKey(name: 'uncertainty_t10') double uncertaintyT10,
      @JsonKey(name: 'uncertainty_t20') double uncertaintyT20,
      @JsonKey(name: 'uncertainty_t30') double uncertaintyT30,
      @JsonKey(name: 'latency_ms') double latencyMs});
}

/// @nodoc
class _$PredictionResponseCopyWithImpl<$Res, $Val extends PredictionResponse>
    implements $PredictionResponseCopyWith<$Res> {
  _$PredictionResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of PredictionResponse
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? city = null,
    Object? timestamp = null,
    Object? congestionT5 = null,
    Object? congestionT10 = null,
    Object? congestionT20 = null,
    Object? congestionT30 = null,
    Object? uncertaintyT5 = null,
    Object? uncertaintyT10 = null,
    Object? uncertaintyT20 = null,
    Object? uncertaintyT30 = null,
    Object? latencyMs = null,
  }) {
    return _then(_value.copyWith(
      city: null == city
          ? _value.city
          : city // ignore: cast_nullable_to_non_nullable
              as String,
      timestamp: null == timestamp
          ? _value.timestamp
          : timestamp // ignore: cast_nullable_to_non_nullable
              as String,
      congestionT5: null == congestionT5
          ? _value.congestionT5
          : congestionT5 // ignore: cast_nullable_to_non_nullable
              as double,
      congestionT10: null == congestionT10
          ? _value.congestionT10
          : congestionT10 // ignore: cast_nullable_to_non_nullable
              as double,
      congestionT20: null == congestionT20
          ? _value.congestionT20
          : congestionT20 // ignore: cast_nullable_to_non_nullable
              as double,
      congestionT30: null == congestionT30
          ? _value.congestionT30
          : congestionT30 // ignore: cast_nullable_to_non_nullable
              as double,
      uncertaintyT5: null == uncertaintyT5
          ? _value.uncertaintyT5
          : uncertaintyT5 // ignore: cast_nullable_to_non_nullable
              as double,
      uncertaintyT10: null == uncertaintyT10
          ? _value.uncertaintyT10
          : uncertaintyT10 // ignore: cast_nullable_to_non_nullable
              as double,
      uncertaintyT20: null == uncertaintyT20
          ? _value.uncertaintyT20
          : uncertaintyT20 // ignore: cast_nullable_to_non_nullable
              as double,
      uncertaintyT30: null == uncertaintyT30
          ? _value.uncertaintyT30
          : uncertaintyT30 // ignore: cast_nullable_to_non_nullable
              as double,
      latencyMs: null == latencyMs
          ? _value.latencyMs
          : latencyMs // ignore: cast_nullable_to_non_nullable
              as double,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$PredictionResponseImplCopyWith<$Res>
    implements $PredictionResponseCopyWith<$Res> {
  factory _$$PredictionResponseImplCopyWith(_$PredictionResponseImpl value,
          $Res Function(_$PredictionResponseImpl) then) =
      __$$PredictionResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String city,
      String timestamp,
      @JsonKey(name: 'congestion_t5') double congestionT5,
      @JsonKey(name: 'congestion_t10') double congestionT10,
      @JsonKey(name: 'congestion_t20') double congestionT20,
      @JsonKey(name: 'congestion_t30') double congestionT30,
      @JsonKey(name: 'uncertainty_t5') double uncertaintyT5,
      @JsonKey(name: 'uncertainty_t10') double uncertaintyT10,
      @JsonKey(name: 'uncertainty_t20') double uncertaintyT20,
      @JsonKey(name: 'uncertainty_t30') double uncertaintyT30,
      @JsonKey(name: 'latency_ms') double latencyMs});
}

/// @nodoc
class __$$PredictionResponseImplCopyWithImpl<$Res>
    extends _$PredictionResponseCopyWithImpl<$Res, _$PredictionResponseImpl>
    implements _$$PredictionResponseImplCopyWith<$Res> {
  __$$PredictionResponseImplCopyWithImpl(_$PredictionResponseImpl _value,
      $Res Function(_$PredictionResponseImpl) _then)
      : super(_value, _then);

  /// Create a copy of PredictionResponse
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? city = null,
    Object? timestamp = null,
    Object? congestionT5 = null,
    Object? congestionT10 = null,
    Object? congestionT20 = null,
    Object? congestionT30 = null,
    Object? uncertaintyT5 = null,
    Object? uncertaintyT10 = null,
    Object? uncertaintyT20 = null,
    Object? uncertaintyT30 = null,
    Object? latencyMs = null,
  }) {
    return _then(_$PredictionResponseImpl(
      city: null == city
          ? _value.city
          : city // ignore: cast_nullable_to_non_nullable
              as String,
      timestamp: null == timestamp
          ? _value.timestamp
          : timestamp // ignore: cast_nullable_to_non_nullable
              as String,
      congestionT5: null == congestionT5
          ? _value.congestionT5
          : congestionT5 // ignore: cast_nullable_to_non_nullable
              as double,
      congestionT10: null == congestionT10
          ? _value.congestionT10
          : congestionT10 // ignore: cast_nullable_to_non_nullable
              as double,
      congestionT20: null == congestionT20
          ? _value.congestionT20
          : congestionT20 // ignore: cast_nullable_to_non_nullable
              as double,
      congestionT30: null == congestionT30
          ? _value.congestionT30
          : congestionT30 // ignore: cast_nullable_to_non_nullable
              as double,
      uncertaintyT5: null == uncertaintyT5
          ? _value.uncertaintyT5
          : uncertaintyT5 // ignore: cast_nullable_to_non_nullable
              as double,
      uncertaintyT10: null == uncertaintyT10
          ? _value.uncertaintyT10
          : uncertaintyT10 // ignore: cast_nullable_to_non_nullable
              as double,
      uncertaintyT20: null == uncertaintyT20
          ? _value.uncertaintyT20
          : uncertaintyT20 // ignore: cast_nullable_to_non_nullable
              as double,
      uncertaintyT30: null == uncertaintyT30
          ? _value.uncertaintyT30
          : uncertaintyT30 // ignore: cast_nullable_to_non_nullable
              as double,
      latencyMs: null == latencyMs
          ? _value.latencyMs
          : latencyMs // ignore: cast_nullable_to_non_nullable
              as double,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$PredictionResponseImpl implements _PredictionResponse {
  _$PredictionResponseImpl(
      {required this.city,
      required this.timestamp,
      @JsonKey(name: 'congestion_t5') required this.congestionT5,
      @JsonKey(name: 'congestion_t10') required this.congestionT10,
      @JsonKey(name: 'congestion_t20') required this.congestionT20,
      @JsonKey(name: 'congestion_t30') required this.congestionT30,
      @JsonKey(name: 'uncertainty_t5') required this.uncertaintyT5,
      @JsonKey(name: 'uncertainty_t10') required this.uncertaintyT10,
      @JsonKey(name: 'uncertainty_t20') required this.uncertaintyT20,
      @JsonKey(name: 'uncertainty_t30') required this.uncertaintyT30,
      @JsonKey(name: 'latency_ms') required this.latencyMs});

  factory _$PredictionResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$PredictionResponseImplFromJson(json);

  @override
  final String city;
  @override
  final String timestamp;
  @override
  @JsonKey(name: 'congestion_t5')
  final double congestionT5;
  @override
  @JsonKey(name: 'congestion_t10')
  final double congestionT10;
  @override
  @JsonKey(name: 'congestion_t20')
  final double congestionT20;
  @override
  @JsonKey(name: 'congestion_t30')
  final double congestionT30;
  @override
  @JsonKey(name: 'uncertainty_t5')
  final double uncertaintyT5;
  @override
  @JsonKey(name: 'uncertainty_t10')
  final double uncertaintyT10;
  @override
  @JsonKey(name: 'uncertainty_t20')
  final double uncertaintyT20;
  @override
  @JsonKey(name: 'uncertainty_t30')
  final double uncertaintyT30;
  @override
  @JsonKey(name: 'latency_ms')
  final double latencyMs;

  @override
  String toString() {
    return 'PredictionResponse(city: $city, timestamp: $timestamp, congestionT5: $congestionT5, congestionT10: $congestionT10, congestionT20: $congestionT20, congestionT30: $congestionT30, uncertaintyT5: $uncertaintyT5, uncertaintyT10: $uncertaintyT10, uncertaintyT20: $uncertaintyT20, uncertaintyT30: $uncertaintyT30, latencyMs: $latencyMs)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PredictionResponseImpl &&
            (identical(other.city, city) || other.city == city) &&
            (identical(other.timestamp, timestamp) ||
                other.timestamp == timestamp) &&
            (identical(other.congestionT5, congestionT5) ||
                other.congestionT5 == congestionT5) &&
            (identical(other.congestionT10, congestionT10) ||
                other.congestionT10 == congestionT10) &&
            (identical(other.congestionT20, congestionT20) ||
                other.congestionT20 == congestionT20) &&
            (identical(other.congestionT30, congestionT30) ||
                other.congestionT30 == congestionT30) &&
            (identical(other.uncertaintyT5, uncertaintyT5) ||
                other.uncertaintyT5 == uncertaintyT5) &&
            (identical(other.uncertaintyT10, uncertaintyT10) ||
                other.uncertaintyT10 == uncertaintyT10) &&
            (identical(other.uncertaintyT20, uncertaintyT20) ||
                other.uncertaintyT20 == uncertaintyT20) &&
            (identical(other.uncertaintyT30, uncertaintyT30) ||
                other.uncertaintyT30 == uncertaintyT30) &&
            (identical(other.latencyMs, latencyMs) ||
                other.latencyMs == latencyMs));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      city,
      timestamp,
      congestionT5,
      congestionT10,
      congestionT20,
      congestionT30,
      uncertaintyT5,
      uncertaintyT10,
      uncertaintyT20,
      uncertaintyT30,
      latencyMs);

  /// Create a copy of PredictionResponse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$PredictionResponseImplCopyWith<_$PredictionResponseImpl> get copyWith =>
      __$$PredictionResponseImplCopyWithImpl<_$PredictionResponseImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$PredictionResponseImplToJson(
      this,
    );
  }
}

abstract class _PredictionResponse implements PredictionResponse {
  factory _PredictionResponse(
      {required final String city,
      required final String timestamp,
      @JsonKey(name: 'congestion_t5') required final double congestionT5,
      @JsonKey(name: 'congestion_t10') required final double congestionT10,
      @JsonKey(name: 'congestion_t20') required final double congestionT20,
      @JsonKey(name: 'congestion_t30') required final double congestionT30,
      @JsonKey(name: 'uncertainty_t5') required final double uncertaintyT5,
      @JsonKey(name: 'uncertainty_t10') required final double uncertaintyT10,
      @JsonKey(name: 'uncertainty_t20') required final double uncertaintyT20,
      @JsonKey(name: 'uncertainty_t30') required final double uncertaintyT30,
      @JsonKey(name: 'latency_ms')
      required final double latencyMs}) = _$PredictionResponseImpl;

  factory _PredictionResponse.fromJson(Map<String, dynamic> json) =
      _$PredictionResponseImpl.fromJson;

  @override
  String get city;
  @override
  String get timestamp;
  @override
  @JsonKey(name: 'congestion_t5')
  double get congestionT5;
  @override
  @JsonKey(name: 'congestion_t10')
  double get congestionT10;
  @override
  @JsonKey(name: 'congestion_t20')
  double get congestionT20;
  @override
  @JsonKey(name: 'congestion_t30')
  double get congestionT30;
  @override
  @JsonKey(name: 'uncertainty_t5')
  double get uncertaintyT5;
  @override
  @JsonKey(name: 'uncertainty_t10')
  double get uncertaintyT10;
  @override
  @JsonKey(name: 'uncertainty_t20')
  double get uncertaintyT20;
  @override
  @JsonKey(name: 'uncertainty_t30')
  double get uncertaintyT30;
  @override
  @JsonKey(name: 'latency_ms')
  double get latencyMs;

  /// Create a copy of PredictionResponse
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$PredictionResponseImplCopyWith<_$PredictionResponseImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
