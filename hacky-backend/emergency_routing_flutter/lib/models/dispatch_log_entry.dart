import 'package:freezed_annotation/freezed_annotation.dart';

part 'dispatch_log_entry.freezed.dart';

@freezed
class DispatchLogEntry with _$DispatchLogEntry {
  factory DispatchLogEntry({
    required String id,
    required String timestamp,
    required String city,
    required double score,
    required String message,
    required String level,
  }) = _DispatchLogEntry;
}
