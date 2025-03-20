import 'dart:convert';
import 'package:http/http.dart' as http;
import 'dart:io';
import 'package:flutter/foundation.dart';

class ApiService {
  String get baseUrl {
    // Check if running on Android emulator
    if (!kIsWeb && Platform.isAndroid) {
      return 'http://10.0.2.2:5000'; // Android emulator localhost
    }
    // Check if running on web
    if (kIsWeb) {
      return 'http://localhost:5000'; // Web localhost
    }
    // For iOS simulator or physical devices
    return 'http://127.0.0.1:5000'; // Default localhost
  }

  Future<Map<String, dynamic>> sendRouteData(
      String initialLocation, String destination) async {
    final url = Uri.parse('$baseUrl/process');
    try {
      print('Sending request to: $url');
      final response = await http.post(
        url,
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
        body: jsonEncode(
            {"initial_location": initialLocation, "destination": destination}),
      );

      print('Response status: ${response.statusCode}');
      print('Response body: ${response.body}');

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        return {
          "status": "error",
          "message": "Server error: ${response.statusCode}\n${response.body}"
        };
      }
    } on SocketException catch (e) {
      print('Socket Exception: $e');
      return {
        "status": "error",
        "message":
            "Cannot connect to server. Please make sure the server is running."
      };
    } on HttpException catch (e) {
      print('HTTP Exception: $e');
      return {"status": "error", "message": "HTTP error occurred: $e"};
    } on FormatException catch (e) {
      print('Format Exception: $e');
      return {"status": "error", "message": "Invalid response format: $e"};
    } catch (e) {
      print('Unknown error: $e');
      return {"status": "error", "message": "An unexpected error occurred: $e"};
    }
  }

  Future<Map<String, dynamic>> startSimulation() async {
    final url = Uri.parse('$baseUrl/start');
    try {
      final response = await http.post(
        url,
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        return {
          "status": "error",
          "message": "Server error: ${response.statusCode}\n${response.body}"
        };
      }
    } catch (e) {
      return {"status": "error", "message": "An error occurred: $e"};
    }
  }

  Future<Map<String, dynamic>> getVehicleUpdates(String vehicleId) async {
    final url = Uri.parse('$baseUrl/updates/$vehicleId');
    try {
      final response = await http.get(
        url,
        headers: {
          "Accept": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        return {
          "status": "error",
          "message": "Server error: ${response.statusCode}\n${response.body}"
        };
      }
    } catch (e) {
      return {"status": "error", "message": "An error occurred: $e"};
    }
  }
}
