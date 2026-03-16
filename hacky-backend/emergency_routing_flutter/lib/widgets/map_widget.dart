import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../config/theme.dart';

class MapWidget extends StatelessWidget {
  final double cityLat;
  final double cityLng;
  final double congestionScore;
  final String cityName;
  final bool isPulsing;

  const MapWidget({
    super.key,
    required this.cityLat,
    required this.cityLng,
    required this.congestionScore,
    required this.cityName,
    required this.isPulsing,
  });

  @override
  Widget build(BuildContext context) {
    final color = getCongestionColor(congestionScore);
    
    // Matrix to invert OpenStreetMap layers for dark mode
    final List<double> darkModeMatrix = [
      -1,  0,  0, 0, 255,
       0, -1,  0, 0, 255,
       0,  0, -1, 0, 255,
       0,  0,  0, 1,   0,
    ];

    Widget markerChild = Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.emergency, color: color, size: 32),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(4)),
          child: Text(cityName, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 10)),
        )
      ],
    );

    if (isPulsing) {
      markerChild = markerChild.animate(onPlay: (c) => c.repeat())
        .scale(begin: const Offset(1, 1), end: const Offset(1.3, 1.3), duration: 1000.ms)
        .then()
        .scale(begin: const Offset(1.3, 1.3), end: const Offset(1, 1), duration: 1000.ms);
    }

    return Container(
      height: 280,
      clipBehavior: Clip.hardEdge,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kCardBorder),
      ),
      child: FlutterMap(
        options: MapOptions(
          initialCenter: LatLng(cityLat, cityLng),
          initialZoom: 12,
          interactionOptions: const InteractionOptions(flags: InteractiveFlag.all),
        ),
        children: [
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'com.emergencyrouting.app',
            tileBuilder: (BuildContext context, Widget tileWidget, TileImage tile) {
              return ColorFiltered(
                colorFilter: ColorFilter.matrix(darkModeMatrix),
                child: tileWidget,
              );
            },
          ),
          CircleLayer(
            circles: [
              CircleMarker(
                point: LatLng(cityLat, cityLng),
                radius: 3000,
                useRadiusInMeter: true,
                color: color.withOpacity(0.35),
                borderColor: color.withOpacity(0.8),
                borderStrokeWidth: 2,
              )
            ],
          ),
          MarkerLayer(
            markers: [
              Marker(
                point: LatLng(cityLat, cityLng),
                width: 80,
                height: 80,
                child: markerChild,
              )
            ],
          )
        ],
      ),
    );
  }
}
