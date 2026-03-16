// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'prediction_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$selectedCityHash() => r'02fec0a0cf2d854cb922bd4b526a240d44ae3671';

/// See also [SelectedCity].
@ProviderFor(SelectedCity)
final selectedCityProvider =
    AutoDisposeNotifierProvider<SelectedCity, CityConfig?>.internal(
  SelectedCity.new,
  name: r'selectedCityProvider',
  debugGetCreateSourceHash:
      const bool.fromEnvironment('dart.vm.product') ? null : _$selectedCityHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$SelectedCity = AutoDisposeNotifier<CityConfig?>;
String _$predictionsHash() => r'1b9240840ebc44f2e4bafddcd24c0e652d843233';

/// See also [Predictions].
@ProviderFor(Predictions)
final predictionsProvider = AutoDisposeNotifierProvider<Predictions,
    Map<String, PredictionResponse>>.internal(
  Predictions.new,
  name: r'predictionsProvider',
  debugGetCreateSourceHash:
      const bool.fromEnvironment('dart.vm.product') ? null : _$predictionsHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$Predictions = AutoDisposeNotifier<Map<String, PredictionResponse>>;
String _$isLoadingHash() => r'0e78936b426252269db489fb130c467a4a737bf6';

/// See also [IsLoading].
@ProviderFor(IsLoading)
final isLoadingProvider = AutoDisposeNotifierProvider<IsLoading, bool>.internal(
  IsLoading.new,
  name: r'isLoadingProvider',
  debugGetCreateSourceHash:
      const bool.fromEnvironment('dart.vm.product') ? null : _$isLoadingHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$IsLoading = AutoDisposeNotifier<bool>;
String _$appErrorHash() => r'37973a1931955fe7cd33523b296b3f47af749093';

/// See also [AppError].
@ProviderFor(AppError)
final appErrorProvider =
    AutoDisposeNotifierProvider<AppError, String?>.internal(
  AppError.new,
  name: r'appErrorProvider',
  debugGetCreateSourceHash:
      const bool.fromEnvironment('dart.vm.product') ? null : _$appErrorHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$AppError = AutoDisposeNotifier<String?>;
String _$autoRefreshHash() => r'c1dfe1062e07157fa3b2d6c1880646c74ba28782';

/// See also [AutoRefresh].
@ProviderFor(AutoRefresh)
final autoRefreshProvider =
    AutoDisposeNotifierProvider<AutoRefresh, bool>.internal(
  AutoRefresh.new,
  name: r'autoRefreshProvider',
  debugGetCreateSourceHash:
      const bool.fromEnvironment('dart.vm.product') ? null : _$autoRefreshHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$AutoRefresh = AutoDisposeNotifier<bool>;
String _$lastUpdatedHash() => r'8810cacf2d44e47514634db310caf0693e7b6105';

/// See also [LastUpdated].
@ProviderFor(LastUpdated)
final lastUpdatedProvider =
    AutoDisposeNotifierProvider<LastUpdated, String?>.internal(
  LastUpdated.new,
  name: r'lastUpdatedProvider',
  debugGetCreateSourceHash:
      const bool.fromEnvironment('dart.vm.product') ? null : _$lastUpdatedHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$LastUpdated = AutoDisposeNotifier<String?>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
