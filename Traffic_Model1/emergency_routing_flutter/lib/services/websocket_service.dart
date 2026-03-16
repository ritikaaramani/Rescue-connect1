import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';

/// WebSocket Service for real-time communication with backend
/// Handles all WebSocket connections for dispatch, vehicle, and citizen apps

class WebSocketService extends ChangeNotifier {
  static const String BASE_URL = "ws://localhost:8000";
  
  late WebSocketChannel _channel;
  final String _role; // 'dispatch', 'vehicle', 'citizen'
  final String? _vehicleId; // Only for vehicle role
  
  // Message stream controllers
  final _incidentUpdateController = StreamController<Map<String, dynamic>>.broadcast();
  final _vehicleUpdateController = StreamController<Map<String, dynamic>>.broadcast();
  final _rerouteController = StreamController<Map<String, dynamic>>.broadcast();
  final _witnessReportController = StreamController<Map<String, dynamic>>.broadcast();
  final _dispatchMessageController = StreamController<Map<String, dynamic>>.broadcast();
  
  bool _isConnected = false;
  
  get isConnected => _isConnected;
  get incidentUpdates => _incidentUpdateController.stream;
  get vehicleUpdates => _vehicleUpdateController.stream;
  get reroutes => _rerouteController.stream;
  get witnessReports => _witnessReportController.stream;
  get dispatchMessages => _dispatchMessageController.stream;

  /// Constructor
  WebSocketService({
    required String role,
    String? vehicleId,
  }) : _role = role, _vehicleId = vehicleId;

  /// Connect to WebSocket server
  Future<void> connect() async {
    try {
      String url;
      
      switch (_role) {
        case 'dispatch':
          url = '$BASE_URL/ws/dispatch';
          break;
        case 'vehicle':
          if (_vehicleId == null) throw Exception('Vehicle ID required for vehicle role');
          url = '$BASE_URL/ws/vehicle/$_vehicleId';
          break;
        case 'citizen':
          url = '$BASE_URL/ws/citizen';
          break;
        default:
          throw Exception('Invalid role: $_role');
      }
      
      _channel = WebSocketChannel.connect(Uri.parse(url));
      _isConnected = true;
      notifyListeners();
      
      print('✅ WebSocket connected: $_role');
      
      // Listen to messages
      _channel.stream.listen(
        (message) => _handleMessage(message),
        onError: (error) => _handleError(error),
        onDone: () => _handleDisconnect(),
      );
    } catch (e) {
      print('❌ WebSocket connection error: $e');
      _isConnected = false;
      notifyListeners();
      rethrow;
    }
  }

  /// Handle incoming messages
  void _handleMessage(dynamic message) {
    try {
      final Map<String, dynamic> data = jsonDecode(message);
      final String type = data['type'] ?? '';
      
      switch (type) {
        case 'INCIDENT_UPDATE':
          _incidentUpdateController.add(data['incident'] ?? {});
          break;
        case 'VEHICLE_UPDATE':
          _vehicleUpdateController.add(data['vehicle'] ?? {});
          break;
        case 'REROUTE':
          _rerouteController.add(data);
          break;
        case 'WITNESS_REPORT':
          _witnessReportController.add(data['report'] ?? {});
          break;
        case 'DISPATCH_MESSAGE':
          _dispatchMessageController.add(data);
          break;
        default:
          print('⚠️ Unknown message type: $type');
      }
    } catch (e) {
      print('❌ Error handling WebSocket message: $e');
    }
  }

  void _handleError(error) {
    print('❌ WebSocket error: $error');
  }

  void _handleDisconnect() {
    print('⚠️ WebSocket disconnected: $_role');
    _isConnected = false;
    notifyListeners();
  }

  /// Send message to server
  void sendMessage(Map<String, dynamic> message) {
    if (!_isConnected) {
      print('❌ WebSocket not connected');
      return;
    }
    try {
      _channel.sink.add(jsonEncode(message));
    } catch (e) {
      print('❌ Error sending WebSocket message: $e');
    }
  }

  /// Disconnect from WebSocket server
  Future<void> disconnect() async {
    try {
      await _channel.sink.close();
      _isConnected = false;
      notifyListeners();
      print('✅ WebSocket disconnected: $_role');
    } catch (e) {
      print('❌ Error disconnecting WebSocket: $e');
    }
  }

  @override
  void dispose() {
    disconnect();
    _incidentUpdateController.close();
    _vehicleUpdateController.close();
    _rerouteController.close();
    _witnessReportController.close();
    _dispatchMessageController.close();
    super.dispose();
  }
}
