import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/task.dart';
import '../models/calendar_event.dart';
import '../models/entity.dart';
import 'settings_service.dart';

class ApiService {
  final SettingsService _settings;
  ApiService(this._settings);

  Uri _uri(String path) => Uri.parse('${_settings.httpUrl}$path');

  // ── Tasks ─────────────────────────────────────────────────────────────
  Future<List<Task>> fetchTasks() async {
    final res = await http.get(_uri('/api/tasks/'), headers: _settings.httpHeaders);
    _check(res);
    final list = jsonDecode(res.body) as List;
    return list.map((e) => Task.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Task> createTask(String title, {String? dueDate}) async {
    final body = jsonEncode({'title': title, 'due_date': ?dueDate});
    final res = await http.post(_uri('/api/tasks/'), headers: _settings.httpHeaders, body: body);
    _check(res);
    return Task.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<Task> updateTaskStatus(String id, String status) async {
    final body = jsonEncode({'status': status});
    final res = await http.patch(_uri('/api/tasks/$id'), headers: _settings.httpHeaders, body: body);
    _check(res);
    return Task.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  // ── Calendar ──────────────────────────────────────────────────────────
  Future<List<CalendarEvent>> fetchEvents() async {
    final res = await http.get(_uri('/api/calendar/'), headers: _settings.httpHeaders);
    _check(res);
    final list = jsonDecode(res.body) as List;
    return list.map((e) => CalendarEvent.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<CalendarEvent> createEvent({
    required String title,
    required DateTime startTime,
    DateTime? endTime,
    String description = '',
  }) async {
    final body = jsonEncode({
      'title': title,
      'start_time': startTime.toIso8601String(),
      if (endTime != null) 'end_time': endTime.toIso8601String(),
      'description': description,
    });
    final res = await http.post(_uri('/api/calendar/'), headers: _settings.httpHeaders, body: body);
    _check(res);
    return CalendarEvent.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<void> deleteEvent(String id) async {
    final res = await http.delete(_uri('/api/calendar/$id'), headers: _settings.httpHeaders);
    _check(res);
  }

  // ── Entities ──────────────────────────────────────────────────────────
  Future<List<Entity>> fetchEntities(String type) async {
    final res = await http.get(_uri('/api/entities/$type'), headers: _settings.httpHeaders);
    _check(res);
    final list = jsonDecode(res.body) as List;
    return list.map((e) => Entity.fromJson(e as Map<String, dynamic>)).toList();
  }

  // ── Health ────────────────────────────────────────────────────────────
  Future<bool> checkHealth() async {
    try {
      final res = await http
          .get(_uri('/health'), headers: _settings.httpHeaders)
          .timeout(const Duration(seconds: 5));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  void _check(http.Response res) {
    if (res.statusCode >= 400) {
      throw ApiException(res.statusCode, res.body);
    }
  }
}

class ApiException implements Exception {
  final int statusCode;
  final String body;
  ApiException(this.statusCode, this.body);

  @override
  String toString() => 'ApiException($statusCode): $body';
}
