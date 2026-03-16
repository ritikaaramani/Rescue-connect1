import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../models/health_response.dart';
import '../models/model_info_response.dart';
import '../services/model1_service.dart';

part 'health_provider.g.dart';

@riverpod
Model1Service model1Service(Model1ServiceRef ref) {
  return Model1Service();
}

@riverpod
class HealthState extends _$HealthState {
  @override
  HealthResponse? build() => null;

  Future<void> fetch() async {
    try {
      state = await ref.read(model1ServiceProvider).checkHealth();
    } catch (e) {
      state = null;
    }
  }
}

@riverpod
class ModelInfoState extends _$ModelInfoState {
  @override
  ModelInfoResponse? build() => null;

  Future<void> fetch() async {
    try {
      state = await ref.read(model1ServiceProvider).getModelInfo();
    } catch (e) {
      state = null;
    }
  }
}
