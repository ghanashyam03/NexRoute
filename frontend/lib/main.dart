import 'package:auth_firebase/firebase_options.dart';
import 'package:auth_firebase/pages/login/login.dart';
import 'package:auth_firebase/pages/map/map.dart';
import 'package:auth_firebase/pages/signup/signup.dart';
import 'package:auth_firebase/pages/speed/speed.dart';
import 'package:auth_firebase/pages/navigation/navigation_updates.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Auth Firebase App',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      initialRoute: '/login', // Set the initial route to the Login page
      routes: {
        '/login': (context) => Login(),
        '/signup': (context) => const Signup(),
        '/map': (context) => const Map(),
        '/speed': (context) => SpeedPage(),
        '/navigation': (context) => const NavigationUpdatesPage(vehicleId: ''),
      },
    );
  }
}
