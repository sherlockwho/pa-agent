import 'package:flutter/foundation.dart';
import '../models/calendar_event.dart';
import '../services/api_service.dart';

class CalendarProvider extends ChangeNotifier {
  final ApiService _api;
  CalendarProvider(this._api);

  List<CalendarEvent> _events = [];
  List<CalendarEvent> get events => _events;

  List<CalendarEvent> get upcomingEvents {
    final now = DateTime.now();
    return _events
        .where((e) => e.startTime.isAfter(now.subtract(const Duration(hours: 1))))
        .toList()
      ..sort((a, b) => a.startTime.compareTo(b.startTime));
  }

  bool _loading = false;
  bool get loading => _loading;
  String? _error;
  String? get error => _error;

  Future<void> load() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _events = await _api.fetchEvents();
    } catch (e) {
      _error = e.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> deleteEvent(String id) async {
    await _api.deleteEvent(id);
    await load();
  }
}
