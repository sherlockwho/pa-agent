import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/calendar_event.dart';
import '../providers/calendar_provider.dart';

class CalendarScreen extends StatefulWidget {
  const CalendarScreen({super.key});

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<CalendarProvider>().load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('日程'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => context.read<CalendarProvider>().load(),
          ),
        ],
      ),
      body: Consumer<CalendarProvider>(
        builder: (_, provider,_) {
          if (provider.loading) {
            return const Center(child: CircularProgressIndicator());
          }
          if (provider.error != null) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.error_outline,
                      size: 48,
                      color: Theme.of(context).colorScheme.error),
                  const SizedBox(height: 12),
                  Text(provider.error!,
                      style: TextStyle(
                          color: Theme.of(context).colorScheme.error)),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: () => provider.load(),
                    child: const Text('重试'),
                  ),
                ],
              ),
            );
          }
          final events = provider.upcomingEvents;
          if (events.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.event_note,
                      size: 64,
                      color: Theme.of(context).colorScheme.outlineVariant),
                  const SizedBox(height: 16),
                  Text('暂无日程',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Text('在聊天中说"帮我安排会议"来添加日程',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.outline)),
                ],
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: provider.load,
            child: ListView.builder(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: events.length,
              itemBuilder: (_, i) => _EventTile(event: events[i]),
            ),
          );
        },
      ),
    );
  }
}

class _EventTile extends StatelessWidget {
  final CalendarEvent event;
  const _EventTile({required this.event});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final now = DateTime.now();
    final isToday = event.startTime.year == now.year &&
        event.startTime.month == now.month &&
        event.startTime.day == now.day;
    final isTomorrow = event.startTime.year == now.year &&
        event.startTime.month == now.month &&
        event.startTime.day == now.day + 1;

    String dayLabel;
    if (isToday) {
      dayLabel = '今天';
    } else if (isTomorrow) {
      dayLabel = '明天';
    } else {
      dayLabel = DateFormat('M月d日 E', 'zh_CN').format(event.startTime);
    }

    return Dismissible(
      key: Key(event.id),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        color: cs.errorContainer,
        child: Icon(Icons.delete_outline, color: cs.onErrorContainer),
      ),
      confirmDismiss: (_) async {
        final confirmed = await showDialog<bool>(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('删除日程'),
            content: Text('确定删除「${event.title}」？'),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('取消'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                style: FilledButton.styleFrom(
                    backgroundColor: cs.error, foregroundColor: cs.onError),
                child: const Text('删除'),
              ),
            ],
          ),
        );
        if (confirmed == true && context.mounted) {
          await context.read<CalendarProvider>().deleteEvent(event.id);
        }
        return false;
      },
      child: Card(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _DateBox(dayLabel: dayLabel, time: event.startTime, isToday: isToday),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(event.title,
                        style: Theme.of(context).textTheme.titleSmall),
                    if (event.description.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(event.description,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: cs.outline)),
                    ],
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(Icons.access_time, size: 12, color: cs.outline),
                        const SizedBox(width: 4),
                        Text(
                          _formatTimeRange(event),
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(color: cs.outline),
                        ),
                        if (event.location.isNotEmpty) ...[
                          const SizedBox(width: 8),
                          Icon(Icons.location_on_outlined,
                              size: 12, color: cs.outline),
                          const SizedBox(width: 2),
                          Flexible(
                            child: Text(event.location,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(color: cs.outline)),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatTimeRange(CalendarEvent event) {
    final start = DateFormat('HH:mm').format(event.startTime);
    if (event.endTime == null) return start;
    final end = DateFormat('HH:mm').format(event.endTime!);
    return '$start – $end';
  }
}

class _DateBox extends StatelessWidget {
  final String dayLabel;
  final DateTime time;
  final bool isToday;
  const _DateBox(
      {required this.dayLabel, required this.time, required this.isToday});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      width: 48,
      padding: const EdgeInsets.symmetric(vertical: 6),
      decoration: BoxDecoration(
        color: isToday ? cs.primaryContainer : cs.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Text(
            '${time.day}',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: isToday ? cs.onPrimaryContainer : cs.onSurface,
                fontWeight: FontWeight.bold),
          ),
          Text(
            dayLabel.length <= 2 ? dayLabel : DateFormat('E', 'zh_CN').format(time),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: isToday ? cs.onPrimaryContainer : cs.outline),
          ),
        ],
      ),
    );
  }
}
