// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'health_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$model1ServiceHash() => r'9004e1d60f6a2cec9513386ce168dbfe357f4e2c';

/// See also [model1Service].
@ProviderFor(model1Service)
final model1ServiceProvider = AutoDisposeProvider<Model1Service>.internal(
  model1Service,
  name: r'model1ServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$model1ServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef Model1ServiceRef = AutoDisposeProviderRef<Model1Service>;
String _$healthStateHash() => r'03ba37f65dc7f940fdc4d51144aa3fee63d94475';

/// See also [HealthState].
@ProviderFor(HealthState)
final healthStateProvider =
    AutoDisposeNotifierProvider<HealthState, HealthResponse?>.internal(
  HealthState.new,
  name: r'healthStateProvider',
  debugGetCreateSourceHash:
      const bool.fromEnvironment('dart.vm.product') ? null : _$healthStateHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$HealthState = AutoDisposeNotifier<HealthResponse?>;
String _$modelInfoStateHash() => r'fa399adaec260145d300bf6cf17fcac9e9069ef4';

/// See also [ModelInfoState].
@ProviderFor(ModelInfoState)
final modelInfoStateProvider =
    AutoDisposeNotifierProvider<ModelInfoState, ModelInfoResponse?>.internal(
  ModelInfoState.new,
  name: r'modelInfoStateProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$modelInfoStateHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$ModelInfoState = AutoDisposeNotifier<ModelInfoResponse?>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
