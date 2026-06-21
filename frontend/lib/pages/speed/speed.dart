import 'package:flutter/material.dart';
import 'package:auth_firebase/api_service.dart';
import 'package:auth_firebase/pages/navigation/navigation_updates.dart';
import 'dart:async';
import 'dart:math' as math;
import 'dart:ui';

class SpeedPage extends StatefulWidget {
  const SpeedPage({super.key});

  @override
  _SpeedPageState createState() => _SpeedPageState();
}

class _SpeedPageState extends State<SpeedPage>
    with SingleTickerProviderStateMixin {
  final TextEditingController _initialLocationController =
      TextEditingController();
  final TextEditingController _destinationController = TextEditingController();
  bool _isLoading = false;
  String _responseMessage = '';

  // Animation controller for car movement
  late AnimationController _animationController;
  late Animation<double> _carAnimation;
  final double _animationSpeed = 1.0; // Default animation speed

  // Create a key to access the CustomPainter
  final GlobalKey _customPaintKey = GlobalKey();

  @override
  void initState() {
    super.initState();

    // Initialize animation controller
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 5), // Base duration
    );

    // Create animation for car movement
    _carAnimation = Tween<double>(
      begin: -0.1, // Start above the visible area
      end: 1.1, // End below the visible area
    ).animate(_animationController);

    // Start animation and loop it
    _animationController.repeat();
  }

  @override
  void dispose() {
    _animationController.dispose();
    _initialLocationController.dispose();
    _destinationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final screenHeight = MediaQuery.of(context).size.height;
    final screenWidth = MediaQuery.of(context).size.width;

    return Scaffold(
      backgroundColor: const Color(0xFFE0F2E9), // Light pastel green background
      appBar: AppBar(
        title: const Text('Route Planner'),
        backgroundColor: const Color(0xFF97D8B2), // Matching app bar color
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const Text(
                'Enter your route:',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              // Initial Location TextField
              TextField(
                controller: _initialLocationController,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  labelText: 'Initial Location',
                  hintText: 'Enter starting point',
                  prefixIcon: Icon(Icons.location_on),
                ),
              ),
              const SizedBox(height: 16),
              // Destination TextField
              TextField(
                controller: _destinationController,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  labelText: 'Destination',
                  hintText: 'Enter destination',
                  prefixIcon: Icon(Icons.location_searching),
                ),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: _isLoading ? null : _submitRoute,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF5AB77C),
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
                ),
                child: _isLoading
                    ? const CircularProgressIndicator(color: Colors.white)
                    : const Text(
                        'Find Route',
                        style: TextStyle(fontSize: 16),
                      ),
              ),
              const SizedBox(height: 10),

              // Curved road and car animation
              Container(
                height: screenHeight * 0.65,
                width: screenWidth,
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.transparent),
                ),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    return Stack(
                      children: [
                        // Curved road background
                        CustomPaint(
                          key: _customPaintKey,
                          size:
                              Size(constraints.maxWidth, constraints.maxHeight),
                          painter: CurvedRoadPainter(),
                        ),

                        // Moving car on the curved path
                        AnimatedBuilder(
                          animation: _carAnimation,
                          builder: (context, child) {
                            try {
                              final size = Size(
                                  constraints.maxWidth, constraints.maxHeight);
                              final roadPath =
                                  createRoadPath(size.width, size.height);

                              final PathMetric pathMetric =
                                  roadPath.computeMetrics().first;
                              final double pathLength = pathMetric.length;
                              final double distanceAlongPath =
                                  pathLength * _carAnimation.value;

                              final Tangent? tangent = pathMetric
                                  .getTangentForOffset(distanceAlongPath);

                              if (tangent == null) return const SizedBox();

                              final Offset position = tangent.position;
                              final double angle = tangent.angle;

                              return Positioned(
                                left: position.dx - 20,
                                top: position.dy - 20,
                                child: Transform.rotate(
                                  angle: angle - math.pi / 2,
                                  child: const Icon(
                                    Icons.directions_car,
                                    color: Colors.red,
                                    size: 40,
                                  ),
                                ),
                              );
                            } catch (e) {
                              print("Error in animation: $e");
                              return const SizedBox();
                            }
                          },
                        ),
                      ],
                    );
                  },
                ),
              ),

              if (_responseMessage.isNotEmpty)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(top: 10),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.8),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF97D8B2)),
                  ),
                  child: Text(
                    _responseMessage,
                    style: const TextStyle(fontSize: 16),
                  ),
                ),

              if (_responseMessage.contains('Route found!'))
                Padding(
                  padding: const EdgeInsets.only(top: 16.0),
                  child: ElevatedButton(
                    onPressed: () {
                      // Extract vehicle ID from the response
                      final vehicleId = _responseMessage.split('\n')
                          .firstWhere((line) => line.contains('Status:'))
                          .split(': ')[1];
                      
                      // Navigate to the updates page
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => NavigationUpdatesPage(vehicleId: vehicleId),
                        ),
                      );
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF5AB77C),
                      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
                    ),
                    child: const Text(
                      'Start Navigation',
                      style: TextStyle(fontSize: 16),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Path createRoadPath(double width, double height) {
    Path path = Path();
    path.moveTo(width * 0.5, 0);

    path.cubicTo(width * 0.8, height * 0.2, width * 0.2, height * 0.4,
        width * 0.5, height * 0.6);

    path.cubicTo(
        width * 0.8, height * 0.8, width * 0.2, height, width * 0.5, height);

    return path;
  }

  Future<void> _submitRoute() async {
    final initialLocation = _initialLocationController.text;
    final destination = _destinationController.text;

    if (initialLocation.isEmpty || destination.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter both locations'),
          backgroundColor: Color(0xFF5AB77C),
        ),
      );
      return;
    }

    setState(() {
      _isLoading = true;
      _responseMessage = '';
    });

    try {
      // Send the route data to the Python API
      final response =
          await ApiService().sendRouteData(initialLocation, destination);

      setState(() {
        _isLoading = false;
        if (response['status'] == 'success') {
          _responseMessage = 'Route found!\n'
              'From: ${response['data']['from']}\n'
              'To: ${response['data']['to']}\n'
              'Status: ${response['data']['status']}';
        } else {
          _responseMessage = 'Error: ${response['message']}';
        }
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _responseMessage = 'Error: $e';
      });
    }
  }
}

class CurvedRoadPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final width = size.width;
    final height = size.height;

    Path roadPath = _createRoadPath(width, height);

    final roadPaint = Paint()
      ..color = Colors.grey[800]!
      ..style = PaintingStyle.stroke
      ..strokeWidth = 20
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(roadPath, roadPaint);

    final linePaint = Paint()
      ..color = Colors.yellow
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round
      ..blendMode = BlendMode.srcOver;

    double dashWidth = 10;
    double dashSpace = 10;
    double distance = 0;
    final path = Path();

    for (final metric in roadPath.computeMetrics()) {
      while (distance < metric.length) {
        final start = distance;
        final end = distance + dashWidth;
        if (end <= metric.length) {
          final extractPath = metric.extractPath(start, end);
          path.addPath(extractPath, Offset.zero);
        }
        distance = end + dashSpace;
      }
    }

    canvas.drawPath(path, linePaint);
  }

  Path _createRoadPath(double width, double height) {
    Path path = Path();
    path.moveTo(width * 0.5, 0);

    path.cubicTo(width * 0.8, height * 0.2, width * 0.2, height * 0.4,
        width * 0.5, height * 0.6);

    path.cubicTo(
        width * 0.8, height * 0.8, width * 0.2, height, width * 0.5, height);

    return path;
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
