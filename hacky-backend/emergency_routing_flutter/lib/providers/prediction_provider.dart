import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:intl/intl.dart';
import '../config/cities_config.dart';
import '../models/prediction_response.dart';
import 'dispatch_provider.dart';

part 'prediction_provider.g.dart';

@riverpod
class SelectedCity extends _$SelectedCity {
  @override
  CityConfig? build() => null;

  void select(CityConfig city) {
    state = city;
  }
}

@riverpod
class Predictions extends _$Predictions {
  @override
  Map<String, PredictionResponse> build() => {};

  void setPrediction(String city, PredictionResponse p) {
    state = {...state, city: p};
    ref.read(dispatchLogProvider.notifier).addEntry(p);
  }

  void setBatch(List<PredictionResponse> list) {
    for (var p in list) {
      setPrediction(p.city, p);
    }
  }

  void clear() {
    state = {};
  }
}

@riverpod
class IsLoading extends _$IsLoading {
  @override
  bool build() => false;

  void setLoading(bool val) {
    state = val;
  }
}

@riverpod
class AppError extends _$AppError {
  @override
  String? build() => null;

  void setError(String? msg) {
    state = msg;
  }
}

@riverpod
class AutoRefresh extends _$AutoRefresh {
  @override
  bool build() => false;

  void toggle() {
    state = !state;
  }
}

@riverpod
class LastUpdated extends _$LastUpdated {
  @override
  String? build() => null;

  void update() {
    state = DateFormat('HH:mm:ss').format(DateTime.now());
  }
}
