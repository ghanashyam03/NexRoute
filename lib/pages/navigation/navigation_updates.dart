import 'package:flutter/material.dart';
import 'package:auth_firebase/api_service.dart';
import 'dart:async';

class NavigationUpdatesPage extends StatefulWidget {
  final String vehicleId;

  const NavigationUpdatesPage({Key? key, required this.vehicleId}) : super(key: key);

  @override
  _NavigationUpdatesPageState createState() => _NavigationUpdatesPageState();
}

class _NavigationUpdatesPageState extends State<NavigationUpdatesPage> {
  List<String> updates = [];
  String latestUpdate = '';
  Timer? _updateTimer;
  bool isSimulationRunning = false;

  @override
  void initState() {
    super.initState();
    _startSimulation();
  }

  Future<void> _startSimulation() async {
    try {
      final response = await ApiService().startSimulation();
      if (response['status'] == 'success') {
        setState(() {
          isSimulationRunning = true;
        });
        // Start polling for updates
        _startUpdatesPolling();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to start simulation: ${response['message']}')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  void _startUpdatesPolling() {
    _updateTimer = Timer.periodic(const Duration(seconds: 1), (timer) async {
      try {
        final response = await ApiService().getVehicleUpdates(widget.vehicleId);
        if (response['status'] == 'success') {
          setState(() {
            if (response['driver_updates'] != null) {
              // Get new updates
              List<String> newUpdates = List<String>.from(response['driver_updates']);
              
              // Process each new update
              for (String update in newUpdates) {
                // Clean up the update text
                String cleanUpdate = update.trim();
                if (cleanUpdate.isNotEmpty && !updates.contains(cleanUpdate)) {
                  // Add new unique updates at the beginning
                  updates.insert(0, cleanUpdate);
                  
                  // Update the latest update
                  latestUpdate = cleanUpdate;
                }
              }
            }

            // Check vehicle state
            var vehicleState = response['vehicle_state'];
            bool isArrived = vehicleState['is_arrived'] ?? false;
            isSimulationRunning = !isArrived;
            
            // Handle journey completion only when vehicle has actually arrived
            if (isArrived) {
              _updateTimer?.cancel();
              
              // Add completion message if not already present
              const completionMessage = 'Journey completed!';
              if (!updates.contains(completionMessage)) {
                updates.insert(0, completionMessage);
                latestUpdate = completionMessage;
                
                // Show completion snackbar
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Journey completed successfully!'),
                    backgroundColor: Color(0xFF5AB77C),
                    duration: Duration(seconds: 3),
                  ),
                );
              }
            }
          });
        }
      } catch (e) {
        print('Error getting updates: $e');
      }
    });
  }

  @override
  void dispose() {
    _updateTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Navigation Updates'),
        backgroundColor: const Color(0xFF97D8B2),
      ),
      body: Container(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            // Status Container with completion animation
            AnimatedContainer(
              duration: const Duration(milliseconds: 500),
              padding: const EdgeInsets.all(16.0),
              decoration: BoxDecoration(
                color: !isSimulationRunning 
                    ? const Color(0xFF5AB77C)  // Green for completion
                    : const Color(0xFFE0F2E9),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    isSimulationRunning ? Icons.directions_car : Icons.done_all,
                    color: !isSimulationRunning ? Colors.white : const Color(0xFF5AB77C),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    isSimulationRunning ? 'Journey in Progress' : 'Journey Complete',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: !isSimulationRunning ? Colors.white : Colors.black87,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Latest Update Container
            if (latestUpdate.isNotEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16.0),
                margin: const EdgeInsets.only(bottom: 20),
                decoration: BoxDecoration(
                  color: const Color(0xFF5AB77C),
                  borderRadius: BorderRadius.circular(10),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.grey.withOpacity(0.3),
                      spreadRadius: 2,
                      blurRadius: 5,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Latest Update',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      latestUpdate,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),

            // Updates List
            Expanded(
              child: updates.isEmpty
                  ? const Center(
                      child: Text(
                        'Waiting for updates...',
                        style: TextStyle(fontSize: 16, color: Colors.grey),
                      ),
                    )
                  : ListView.builder(
                      itemCount: updates.length,
                      itemBuilder: (context, index) {
                        final update = updates[index];
                        return Card(
                          margin: const EdgeInsets.symmetric(vertical: 5),
                          child: ListTile(
                            leading: Icon(
                              _getUpdateIcon(update),
                              color: const Color(0xFF5AB77C),
                            ),
                            title: Text(
                              update,
                              style: TextStyle(
                                fontSize: 16,
                                color: index == 0 ? Colors.black87 : Colors.black54,
                              ),
                            ),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getUpdateIcon(String update) {
    if (update.toLowerCase().contains('turn right')) return Icons.turn_right;
    if (update.toLowerCase().contains('turn left')) return Icons.turn_left;
    if (update.toLowerCase().contains('u-turn')) return Icons.u_turn_left;
    if (update.toLowerCase().contains('speed')) return Icons.speed;
    if (update.toLowerCase().contains('maintain')) return Icons.straight;
    if (update.toLowerCase().contains('completed')) return Icons.done_all;
    return Icons.info;
  }
} 