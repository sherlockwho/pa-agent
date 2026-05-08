class Entity {
  final String id;
  final String type; // person | company | project | product
  final String name;
  final List<String> aliases;
  final List<String> tags;
  final Map<String, dynamic> attributes;
  final int mentionCount;
  final String? lastUpdated;

  const Entity({
    required this.id,
    required this.type,
    required this.name,
    required this.aliases,
    required this.tags,
    required this.attributes,
    required this.mentionCount,
    this.lastUpdated,
  });

  factory Entity.fromJson(Map<String, dynamic> json) => Entity(
        id: json['id'] as String,
        type: json['type'] as String,
        name: json['name'] as String,
        aliases: List<String>.from(json['aliases'] as List? ?? []),
        tags: List<String>.from(json['tags'] as List? ?? []),
        attributes:
            Map<String, dynamic>.from(json['attributes'] as Map? ?? {}),
        mentionCount: json['mention_count'] as int? ?? 1,
        lastUpdated: json['last_updated'] as String?,
      );
}
