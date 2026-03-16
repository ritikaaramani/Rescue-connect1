/// Pan-India city registry for emergency routing.
///
/// [hasCityModel] = true  → uses POST /predict  (trained LSTM+GCN model)
/// [hasCityModel] = false → uses POST /predict/area (bbox-based inference)
///
/// bbox values: {north, south, east, west} for the urban extent.

class CityConfig {
  final String name;
  final String state;
  final double lat;
  final double lng;
  final Map<String, double> bbox;
  final bool hasCityModel; // trained model exists for this city

  const CityConfig({
    required this.name,
    required this.state,
    required this.lat,
    required this.lng,
    required this.bbox,
    this.hasCityModel = false,
  });
}

const List<CityConfig> kCities = [
  // ── TRAINED CITIES (full LSTM+GCN model) ─────────────────────────────────
  CityConfig(
    name: 'Delhi',
    state: 'Delhi',
    lat: 28.6139,
    lng: 77.2090,
    bbox: {
      'north': 28.88,
      'south': 28.40,
      'east': 77.35,
      'west': 76.84
    },
    hasCityModel: true,
  ),
  CityConfig(
    name: 'Mumbai',
    state: 'Maharashtra',
    lat: 19.0760,
    lng: 72.8777,
    bbox: {
      'north': 19.27,
      'south': 18.89,
      'east': 72.99,
      'west': 72.77
    },
    hasCityModel: true,
  ),
  CityConfig(
    name: 'Bengaluru',
    state: 'Karnataka',
    lat: 12.9716,
    lng: 77.5946,
    bbox: {
      'north': 13.14,
      'south': 12.83,
      'east': 77.78,
      'west': 77.46
    },
    hasCityModel: true,
  ),
  CityConfig(
    name: 'Chennai',
    state: 'Tamil Nadu',
    lat: 13.0827,
    lng: 80.2707,
    bbox: {
      'north': 13.23,
      'south': 12.91,
      'east': 80.31,
      'west': 80.17
    },
    hasCityModel: true,
  ),
  CityConfig(
    name: 'Patna',
    state: 'Bihar',
    lat: 25.5941,
    lng: 85.1376,
    bbox: {
      'north': 25.65,
      'south': 25.55,
      'east': 85.22,
      'west': 85.08
    },
    hasCityModel: true,
  ),

  // ── PAN-INDIA CITIES (area prediction via bbox) ───────────────────────────
  CityConfig(
    name: 'Hyderabad',
    state: 'Telangana',
    lat: 17.3850,
    lng: 78.4867,
    bbox: {
      'north': 17.60,
      'south': 17.20,
      'east': 78.70,
      'west': 78.30
    },
  ),
  CityConfig(
    name: 'Kolkata',
    state: 'West Bengal',
    lat: 22.5726,
    lng: 88.3639,
    bbox: {
      'north': 22.75,
      'south': 22.40,
      'east': 88.55,
      'west': 88.20
    },
  ),
  CityConfig(
    name: 'Pune',
    state: 'Maharashtra',
    lat: 18.5204,
    lng: 73.8567,
    bbox: {
      'north': 18.70,
      'south': 18.35,
      'east': 74.00,
      'west': 73.70
    },
  ),
  CityConfig(
    name: 'Ahmedabad',
    state: 'Gujarat',
    lat: 23.0225,
    lng: 72.5714,
    bbox: {
      'north': 23.15,
      'south': 22.90,
      'east': 72.70,
      'west': 72.45
    },
  ),
  CityConfig(
    name: 'Jaipur',
    state: 'Rajasthan',
    lat: 26.9124,
    lng: 75.7873,
    bbox: {
      'north': 27.05,
      'south': 26.80,
      'east': 75.95,
      'west': 75.65
    },
  ),
  CityConfig(
    name: 'Lucknow',
    state: 'Uttar Pradesh',
    lat: 26.8467,
    lng: 80.9462,
    bbox: {
      'north': 26.95,
      'south': 26.75,
      'east': 81.05,
      'west': 80.85
    },
  ),
  CityConfig(
    name: 'Kanpur',
    state: 'Uttar Pradesh',
    lat: 26.4499,
    lng: 80.3319,
    bbox: {
      'north': 26.55,
      'south': 26.35,
      'east': 80.45,
      'west': 80.22
    },
  ),
  CityConfig(
    name: 'Nagpur',
    state: 'Maharashtra',
    lat: 21.1458,
    lng: 79.0882,
    bbox: {
      'north': 21.25,
      'south': 21.05,
      'east': 79.20,
      'west': 78.98
    },
  ),
  CityConfig(
    name: 'Indore',
    state: 'Madhya Pradesh',
    lat: 22.7196,
    lng: 75.8577,
    bbox: {
      'north': 22.82,
      'south': 22.62,
      'east': 75.97,
      'west': 75.75
    },
  ),
  CityConfig(
    name: 'Bhopal',
    state: 'Madhya Pradesh',
    lat: 23.2599,
    lng: 77.4126,
    bbox: {
      'north': 23.36,
      'south': 23.16,
      'east': 77.53,
      'west': 77.30
    },
  ),
  CityConfig(
    name: 'Surat',
    state: 'Gujarat',
    lat: 21.1702,
    lng: 72.8311,
    bbox: {
      'north': 21.28,
      'south': 21.07,
      'east': 72.95,
      'west': 72.72
    },
  ),
  CityConfig(
    name: 'Vadodara',
    state: 'Gujarat',
    lat: 22.3072,
    lng: 73.1812,
    bbox: {
      'north': 22.40,
      'south': 22.22,
      'east': 73.28,
      'west': 73.09
    },
  ),
  CityConfig(
    name: 'Visakhapatnam',
    state: 'Andhra Pradesh',
    lat: 17.6868,
    lng: 83.2185,
    bbox: {
      'north': 17.80,
      'south': 17.60,
      'east': 83.35,
      'west': 83.10
    },
  ),
  CityConfig(
    name: 'Coimbatore',
    state: 'Tamil Nadu',
    lat: 11.0168,
    lng: 76.9558,
    bbox: {
      'north': 11.10,
      'south': 10.93,
      'east': 77.06,
      'west': 76.86
    },
  ),
  CityConfig(
    name: 'Kochi',
    state: 'Kerala',
    lat: 9.9312,
    lng: 76.2673,
    bbox: {
      'north': 10.05,
      'south': 9.82,
      'east': 76.40,
      'west': 76.15
    },
  ),
  CityConfig(
    name: 'Chandigarh',
    state: 'Punjab/Haryana',
    lat: 30.7333,
    lng: 76.7794,
    bbox: {
      'north': 30.80,
      'south': 30.68,
      'east': 76.85,
      'west': 76.70
    },
  ),
  CityConfig(
    name: 'Bhubaneswar',
    state: 'Odisha',
    lat: 20.2961,
    lng: 85.8245,
    bbox: {
      'north': 20.38,
      'south': 20.22,
      'east': 85.92,
      'west': 85.74
    },
  ),
  CityConfig(
    name: 'Guwahati',
    state: 'Assam',
    lat: 26.1445,
    lng: 91.7362,
    bbox: {
      'north': 26.22,
      'south': 26.07,
      'east': 91.85,
      'west': 91.65
    },
  ),
  CityConfig(
    name: 'Ranchi',
    state: 'Jharkhand',
    lat: 23.3441,
    lng: 85.3096,
    bbox: {
      'north': 23.43,
      'south': 23.26,
      'east': 85.40,
      'west': 85.22
    },
  ),
  CityConfig(
    name: 'Raipur',
    state: 'Chhattisgarh',
    lat: 21.2514,
    lng: 81.6296,
    bbox: {
      'north': 21.34,
      'south': 21.17,
      'east': 81.72,
      'west': 81.54
    },
  ),
  CityConfig(
    name: 'Amritsar',
    state: 'Punjab',
    lat: 31.6340,
    lng: 74.8723,
    bbox: {
      'north': 31.70,
      'south': 31.57,
      'east': 74.96,
      'west': 74.79
    },
  ),
  CityConfig(
    name: 'Agra',
    state: 'Uttar Pradesh',
    lat: 27.1767,
    lng: 78.0081,
    bbox: {
      'north': 27.25,
      'south': 27.10,
      'east': 78.10,
      'west': 77.91
    },
  ),
  CityConfig(
    name: 'Thiruvananthapuram',
    state: 'Kerala',
    lat: 8.5241,
    lng: 76.9366,
    bbox: {
      'north': 8.60,
      'south': 8.45,
      'east': 77.03,
      'west': 76.85
    },
  ),
  CityConfig(
    name: 'Varanasi',
    state: 'Uttar Pradesh',
    lat: 25.3176,
    lng: 82.9739,
    bbox: {
      'north': 25.40,
      'south': 25.24,
      'east': 83.07,
      'west': 82.89
    },
  ),
  CityConfig(
    name: 'Jodhpur',
    state: 'Rajasthan',
    lat: 26.2389,
    lng: 73.0243,
    bbox: {
      'north': 26.32,
      'south': 26.16,
      'east': 73.12,
      'west': 72.93
    },
  ),
  CityConfig(
    name: 'Mysuru',
    state: 'Karnataka',
    lat: 12.2958,
    lng: 76.6394,
    bbox: {
      'north': 12.38,
      'south': 12.22,
      'east': 76.73,
      'west': 76.55
    },
  ),
];

/// Cities with a trained LSTM+GCN model — use POST /predict
final kTrainedCities = kCities.where((c) => c.hasCityModel).toList();

/// All city names for validation
final kCityNames = kCities.map((c) => c.name).toList();
