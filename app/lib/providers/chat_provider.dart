import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/chat_message.dart';
import '../services/settings_service.dart';

class ChatProvider extends ChangeNotifier {
  final SettingsService _settings;

  ChatProvider(this._settings);

  final List<ChatMessage> _messages = [];
  List<ChatMessage> get messages => List.unmodifiable(_messages);

  WebSocketChannel? _channel;
  bool _connected = false;
  bool get connected => _connected;

  bool _sending = false;
  bool get sending => _sending;

  String _sessionId = 'default';

  void connect() {
    _disconnect();
    try {
      final uri = Uri.parse(_settings.wsUrl).replace(
        queryParameters: _settings.authToken.isNotEmpty
            ? {'token': _settings.authToken}
            : null,
      );
      _channel = WebSocketChannel.connect(uri, protocols: null);
      _connected = true;
      notifyListeners();
      _channel!.stream.listen(
        _onData,
        onError: (_) => _handleDisconnect(),
        onDone: _handleDisconnect,
      );
    } catch (_) {
      _connected = false;
      notifyListeners();
    }
  }

  void _disconnect() {
    _channel?.sink.close();
    _channel = null;
    _connected = false;
  }

  void _handleDisconnect() {
    _connected = false;
    _sending = false;
    // Clear any in-progress streaming message
    final idx = _messages.indexWhere((m) => m.isStreaming);
    if (idx >= 0) {
      _messages[idx] = _messages[idx].copyWith(isStreaming: false);
    }
    notifyListeners();
  }

  void _onData(dynamic raw) {
    final data = jsonDecode(raw as String) as Map<String, dynamic>;
    final type = data['type'] as String?;

    if (type == 'token') {
      final content = data['content'] as String? ?? '';
      final idx = _messages.indexWhere((m) => m.isStreaming);
      if (idx >= 0) {
        _messages[idx] = _messages[idx].copyWith(
          content: _messages[idx].content + content,
          isStreaming: true,
        );
      } else {
        _messages.add(ChatMessage(
          content: content,
          role: MessageRole.assistant,
          isStreaming: true,
        ));
      }
      notifyListeners();
    } else if (type == 'done') {
      final idx = _messages.indexWhere((m) => m.isStreaming);
      if (idx >= 0) {
        _messages[idx] = _messages[idx].copyWith(isStreaming: false);
      }
      _sending = false;
      notifyListeners();
    } else if (type == 'error') {
      final msg = data['message'] as String? ?? '未知错误';
      _messages.add(ChatMessage(
        content: '⚠️ $msg',
        role: MessageRole.assistant,
      ));
      _sending = false;
      notifyListeners();
    }
  }

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty || _sending) return;

    if (!_connected) {
      connect();
      await Future.delayed(const Duration(milliseconds: 500));
    }

    _messages.add(ChatMessage(content: text.trim(), role: MessageRole.user));
    _sending = true;
    notifyListeners();

    try {
      _channel?.sink.add(jsonEncode({
        'message': text.trim(),
        'session_id': _sessionId,
      }));
    } catch (_) {
      _sending = false;
      _handleDisconnect();
    }
  }

  void clearMessages() {
    _messages.clear();
    _sessionId = DateTime.now().millisecondsSinceEpoch.toString();
    notifyListeners();
  }

  @override
  void dispose() {
    _disconnect();
    super.dispose();
  }
}
