enum MessageRole { user, assistant }

class ChatMessage {
  final String content;
  final MessageRole role;
  final DateTime timestamp;
  bool isStreaming;

  ChatMessage({
    required this.content,
    required this.role,
    DateTime? timestamp,
    this.isStreaming = false,
  }) : timestamp = timestamp ?? DateTime.now();

  ChatMessage copyWith({String? content, bool? isStreaming}) => ChatMessage(
        content: content ?? this.content,
        role: role,
        timestamp: timestamp,
        isStreaming: isStreaming ?? this.isStreaming,
      );
}
