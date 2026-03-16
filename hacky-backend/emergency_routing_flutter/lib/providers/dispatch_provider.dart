import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../models/dispatch_log_entry.dart';
import '../models/prediction_response.dart';
import '../config/theme.dart';

part 'dispatch_provider.g.dart';

@riverpod
class DispatchLog extends _$DispatchLog {
  @override
  List<DispatchLogEntry> build() => [];

  void addEntry(PredictionResponse prediction) {
    final score = prediction.congestionT5;
    final String level = score < 0.3 ? 'low' : score < 0.6 ? 'moderate' : 'high';
    
    final entry = DispatchLogEntry(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      timestamp: DateTime.now().toIso8601String(),
      city: prediction.city,
      score: score,
      message: getCongestionMessage(score),
      level: level,
    );
    
    final newList = [entry, ...state];
    if (newList.length > 100) {
      state = newList.sublist(0, 100);
    } else {
      state = newList;
    }
  }

  void clear() {
    state = [];
  }
}
