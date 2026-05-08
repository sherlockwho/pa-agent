import 'package:flutter/foundation.dart';
import '../models/entity.dart';
import '../services/api_service.dart';

class EntityProvider extends ChangeNotifier {
  final ApiService _api;
  EntityProvider(this._api);

  final Map<String, List<Entity>> _entities = {
    'person': [],
    'company': [],
    'project': [],
    'product': [],
  };

  List<Entity> entitiesOf(String type) => _entities[type] ?? [];

  bool _loading = false;
  bool get loading => _loading;
  String? _error;
  String? get error => _error;

  Future<void> loadAll() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      await Future.wait([
        for (final type in ['person', 'company', 'project', 'product'])
          _api.fetchEntities(type).then((list) => _entities[type] = list),
      ]);
    } catch (e) {
      _error = e.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }
}
