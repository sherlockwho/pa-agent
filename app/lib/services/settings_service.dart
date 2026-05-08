import 'package:shared_preferences/shared_preferences.dart';

class SettingsService {
  static const _keyServerUrl = 'server_url';
  static const _keyAuthToken = 'auth_token';
  static const _defaultUrl = 'https://api.cleverboy.fun:8443';

  static SettingsService? _instance;
  late SharedPreferences _prefs;

  SettingsService._();

  static Future<SettingsService> getInstance() async {
    if (_instance == null) {
      _instance = SettingsService._();
      _instance!._prefs = await SharedPreferences.getInstance();
    }
    return _instance!;
  }

  String get serverUrl => _prefs.getString(_keyServerUrl) ?? _defaultUrl;
  String get authToken => _prefs.getString(_keyAuthToken) ?? '';

  String get wsUrl {
    final base = serverUrl.replaceFirst(RegExp(r'^http'), 'ws');
    return '$base/ws/chat';
  }

  String get httpUrl => serverUrl;

  Future<void> setServerUrl(String url) =>
      _prefs.setString(_keyServerUrl, url.trimRight().replaceAll(RegExp(r'/$'), ''));

  Future<void> setAuthToken(String token) =>
      _prefs.setString(_keyAuthToken, token.trim());

  Map<String, String> get httpHeaders => {
        'Content-Type': 'application/json',
        if (authToken.isNotEmpty) 'Authorization': 'Bearer $authToken',
      };
}
