class CalendarEvent {
  final String id;
  final String title;
  final DateTime startTime;
  final DateTime? endTime;
  final String description;
  final String location;

  const CalendarEvent({
    required this.id,
    required this.title,
    required this.startTime,
    this.endTime,
    required this.description,
    this.location = '',
  });

  factory CalendarEvent.fromJson(Map<String, dynamic> json) => CalendarEvent(
        id: json['id'] as String,
        title: json['title'] as String,
        startTime: DateTime.parse(json['start_time'] as String),
        endTime: json['end_time'] != null
            ? DateTime.parse(json['end_time'] as String)
            : null,
        description: json['description'] as String? ?? '',
        location: json['location'] as String? ?? '',
      );
}
