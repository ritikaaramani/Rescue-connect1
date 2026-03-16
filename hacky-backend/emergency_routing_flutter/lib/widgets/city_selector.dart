import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../config/cities_config.dart';
import '../config/theme.dart';
import '../providers/prediction_provider.dart';

class CitySelector extends ConsumerWidget {
  final void Function(CityConfig) onCitySelect;

  const CitySelector({super.key, required this.onCitySelect});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedCity = ref.watch(selectedCityProvider);
    final predictions = ref.watch(predictionsProvider);

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: Row(
        children: kCities.map((city) {
          final isSelected = selectedCity?.name == city.name;
          final hasPrediction = predictions.containsKey(city.name);
          final predScore = predictions[city.name]?.congestionT5;

          Color bgColor = Colors.transparent;
          if (isSelected) bgColor = hasPrediction ? getCongestionColor(predScore!) : kAccent;

          return GestureDetector(
            onTap: () => onCitySelect(city),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              height: 40,
              margin: const EdgeInsets.only(right: 8),
              padding: const EdgeInsets.symmetric(horizontal: 16),
              decoration: BoxDecoration(
                color: bgColor,
                borderRadius: BorderRadius.circular(999),
                border: !isSelected ? Border.all(color: const Color(0xFF333333)) : null,
              ),
              child: Row(
                children: [
                  if (hasPrediction && !isSelected) ...[
                    Container(width: 6, height: 6, decoration: BoxDecoration(shape: BoxShape.circle, color: getCongestionColor(predScore!))),
                    const SizedBox(width: 6),
                  ],
                  Text(
                    city.name,
                    style: TextStyle(
                      color: isSelected ? Colors.white : kTextSecondary,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
