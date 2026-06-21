import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart' as latLng;

class Map extends StatefulWidget {
  const Map({super.key});

  @override
  State<Map> createState() => _MapState();
}

class _MapState extends State<Map> {
  final TextEditingController _searchController = TextEditingController();
  late MapController _mapController;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
  }

  /// Function to search and move the map to a specific location
  void _searchLocation() {
    final searchText = _searchController.text;

    if (searchText.isNotEmpty) {
      // Replace this dummy logic with real geocoding to find coordinates
      if (searchText.toLowerCase() == 'bangalore') {
        _mapController.move(const latLng.LatLng(12.9716, 77.5946), 12.0);
      } else if (searchText.toLowerCase() == 'delhi') {
        _mapController.move(const latLng.LatLng(28.6139, 77.2090), 12.0);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Location not found')),
        );
      }
    }
  }

  /// Function to navigate to the Speed Page
  void _navigateToSpeedPage(BuildContext context) {
    Navigator.pushNamed(context, '/speed');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _searchController,
          decoration: const InputDecoration(
            hintText: 'Search for a location',
            border: InputBorder.none,
            contentPadding: EdgeInsets.all(8.0),
          ),
          onSubmitted: (value) => _searchLocation(),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.speed),
            onPressed: () => _navigateToSpeedPage(context),
          ),
        ],
      ),
      body: FlutterMap(
        mapController: _mapController,
        options: const MapOptions(
          initialCenter: latLng.LatLng(10.0430, 76.3243), // Initial map center
          initialZoom: 9.2, // Initial zoom level
        ),
        children: [
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'com.example.app',
          ),
          const RichAttributionWidget(
            attributions: [],
          ),
        ],
      ),
    );
  }
}
