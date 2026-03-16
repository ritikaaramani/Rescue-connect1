// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'dispatch_log_entry.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

/// @nodoc
mixin _$DispatchLogEntry {
  String get id => throw _privateConstructorUsedError;
  String get timestamp => throw _privateConstructorUsedError;
  String get city => throw _privateConstructorUsedError;
  double get score => throw _privateConstructorUsedError;
  String get message => throw _privateConstructorUsedError;
  String get level => throw _privateConstructorUsedError;

  /// Create a copy of DispatchLogEntry
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $DispatchLogEntryCopyWith<DispatchLogEntry> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $DispatchLogEntryCopyWith<$Res> {
  factory $DispatchLogEntryCopyWith(
          DispatchLogEntry value, $Res Function(DispatchLogEntry) then) =
      _$DispatchLogEntryCopyWithImpl<$Res, DispatchLogEntry>;
  @useResult
  $Res call(
      {String id,
      String timestamp,
      String city,
      double score,
      String message,
      String level});
}

/// @nodoc
class _$DispatchLogEntryCopyWithImpl<$Res, $Val extends DispatchLogEntry>
    implements $DispatchLogEntryCopyWith<$Res> {
  _$DispatchLogEntryCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of DispatchLogEntry
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? timestamp = null,
    Object? city = null,
    Object? score = null,
    Object? message = null,
    Object? level = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      timestamp: null == timestamp
          ? _value.timestamp
          : timestamp // ignore: cast_nullable_to_non_nullable
              as String,
      city: null == city
          ? _value.city
          : city // ignore: cast_nullable_to_non_nullable
              as String,
      score: null == score
          ? _value.score
          : score // ignore: cast_nullable_to_non_nullable
              as double,
      message: null == message
          ? _value.message
          : message // ignore: cast_nullable_to_non_nullable
              as String,
      level: null == level
          ? _value.level
          : level // ignore: cast_nullable_to_non_nullable
              as String,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$DispatchLogEntryImplCopyWith<$Res>
    implements $DispatchLogEntryCopyWith<$Res> {
  factory _$$DispatchLogEntryImplCopyWith(_$DispatchLogEntryImpl value,
          $Res Function(_$DispatchLogEntryImpl) then) =
      __$$DispatchLogEntryImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String timestamp,
      String city,
      double score,
      String message,
      String level});
}

/// @nodoc
class __$$DispatchLogEntryImplCopyWithImpl<$Res>
    extends _$DispatchLogEntryCopyWithImpl<$Res, _$DispatchLogEntryImpl>
    implements _$$DispatchLogEntryImplCopyWith<$Res> {
  __$$DispatchLogEntryImplCopyWithImpl(_$DispatchLogEntryImpl _value,
      $Res Function(_$DispatchLogEntryImpl) _then)
      : super(_value, _then);

  /// Create a copy of DispatchLogEntry
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? timestamp = null,
    Object? city = null,
    Object? score = null,
    Object? message = null,
    Object? level = null,
  }) {
    return _then(_$DispatchLogEntryImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      timestamp: null == timestamp
          ? _value.timestamp
          : timestamp // ignore: cast_nullable_to_non_nullable
              as String,
      city: null == city
          ? _value.city
          : city // ignore: cast_nullable_to_non_nullable
              as String,
      score: null == score
          ? _value.score
          : score // ignore: cast_nullable_to_non_nullable
              as double,
      message: null == message
          ? _value.message
          : message // ignore: cast_nullable_to_non_nullable
              as String,
      level: null == level
          ? _value.level
          : level // ignore: cast_nullable_to_non_nullable
              as String,
    ));
  }
}

/// @nodoc

class _$DispatchLogEntryImpl implements _DispatchLogEntry {
  _$DispatchLogEntryImpl(
      {required this.id,
      required this.timestamp,
      required this.city,
      required this.score,
      required this.message,
      required this.level});

  @override
  final String id;
  @override
  final String timestamp;
  @override
  final String city;
  @override
  final double score;
  @override
  final String message;
  @override
  final String level;

  @override
  String toString() {
    return 'DispatchLogEntry(id: $id, timestamp: $timestamp, city: $city, score: $score, message: $message, level: $level)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DispatchLogEntryImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.timestamp, timestamp) ||
                other.timestamp == timestamp) &&
            (identical(other.city, city) || other.city == city) &&
            (identical(other.score, score) || other.score == score) &&
            (identical(other.message, message) || other.message == message) &&
            (identical(other.level, level) || other.level == level));
  }

  @override
  int get hashCode =>
      Object.hash(runtimeType, id, timestamp, city, score, message, level);

  /// Create a copy of DispatchLogEntry
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$DispatchLogEntryImplCopyWith<_$DispatchLogEntryImpl> get copyWith =>
      __$$DispatchLogEntryImplCopyWithImpl<_$DispatchLogEntryImpl>(
          this, _$identity);
}

abstract class _DispatchLogEntry implements DispatchLogEntry {
  factory _DispatchLogEntry(
      {required final String id,
      required final String timestamp,
      required final String city,
      required final double score,
      required final String message,
      required final String level}) = _$DispatchLogEntryImpl;

  @override
  String get id;
  @override
  String get timestamp;
  @override
  String get city;
  @override
  double get score;
  @override
  String get message;
  @override
  String get level;

  /// Create a copy of DispatchLogEntry
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$DispatchLogEntryImplCopyWith<_$DispatchLogEntryImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
