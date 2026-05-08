import 'package:flutter/foundation.dart';
import '../models/task.dart';
import '../services/api_service.dart';

class TaskProvider extends ChangeNotifier {
  final ApiService _api;
  TaskProvider(this._api);

  List<Task> _tasks = [];
  List<Task> get tasks => _tasks;

  List<Task> get todoTasks => _tasks.where((t) => t.status == 'todo').toList();
  List<Task> get doingTasks => _tasks.where((t) => t.status == 'doing').toList();
  List<Task> get doneTasks => _tasks.where((t) => t.status == 'done').toList();

  bool _loading = false;
  bool get loading => _loading;

  String? _error;
  String? get error => _error;

  Future<void> load() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _tasks = await _api.fetchTasks();
    } catch (e) {
      _error = e.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> markDone(String id) async {
    await _api.updateTaskStatus(id, 'done');
    await load();
  }

  Future<void> markTodo(String id) async {
    await _api.updateTaskStatus(id, 'todo');
    await load();
  }
}
