class Task {
  final String id;
  final String title;
  final String status; // todo | doing | done
  final String? dueDate;
  final String? priority; // high | normal | low
  final String description;
  final List<String> tags;
  final DateTime createdAt;

  const Task({
    required this.id,
    required this.title,
    required this.status,
    this.dueDate,
    this.priority,
    this.description = '',
    required this.tags,
    required this.createdAt,
  });

  factory Task.fromJson(Map<String, dynamic> json) => Task(
        id: json['id'] as String,
        title: json['title'] as String,
        status: json['status'] as String,
        dueDate: json['due_date'] as String?,
        priority: json['priority'] as String?,
        description: json['description'] as String? ?? '',
        tags: List<String>.from(json['tags'] as List? ?? []),
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  bool get isDone => status == 'done';
}
