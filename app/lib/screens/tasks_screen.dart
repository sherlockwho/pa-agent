import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/task.dart';
import '../providers/task_provider.dart';

class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key});

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<TaskProvider>().load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('任务'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => context.read<TaskProvider>().load(),
          ),
        ],
      ),
      body: Consumer<TaskProvider>(
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
          if (provider.tasks.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.task_alt,
                      size: 64,
                      color: Theme.of(context).colorScheme.outlineVariant),
                  const SizedBox(height: 16),
                  Text('暂无任务',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Text('在聊天中说"帮我创建任务"来添加任务',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.outline)),
                ],
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: provider.load,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.symmetric(vertical: 8),
              children: [
                if (provider.doingTasks.isNotEmpty) ...[
                  _SectionHeader(title: '进行中', count: provider.doingTasks.length),
                  ...provider.doingTasks.map((t) => _TaskTile(task: t)),
                ],
                if (provider.todoTasks.isNotEmpty) ...[
                  _SectionHeader(title: '待办', count: provider.todoTasks.length),
                  ...provider.todoTasks.map((t) => _TaskTile(task: t)),
                ],
                if (provider.doneTasks.isNotEmpty) ...[
                  _SectionHeader(title: '已完成', count: provider.doneTasks.length),
                  ...provider.doneTasks.map((t) => _TaskTile(task: t)),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  final int count;
  const _SectionHeader({required this.title, required this.count});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: Row(
        children: [
          Text(title,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: Theme.of(context).colorScheme.primary)),
          const SizedBox(width: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text('$count',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Theme.of(context).colorScheme.onPrimaryContainer)),
          ),
        ],
      ),
    );
  }
}

class _TaskTile extends StatelessWidget {
  final Task task;
  const _TaskTile({required this.task});

  @override
  Widget build(BuildContext context) {
    final isDone = task.isDone;
    final cs = Theme.of(context).colorScheme;

    return Dismissible(
      key: Key(task.id),
      direction: isDone
          ? DismissDirection.endToStart
          : DismissDirection.startToEnd,
      background: Container(
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.only(left: 20),
        color: cs.primaryContainer,
        child: Icon(Icons.check, color: cs.onPrimaryContainer),
      ),
      secondaryBackground: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        color: cs.surfaceContainerHighest,
        child: Icon(Icons.undo, color: cs.onSurfaceVariant),
      ),
      confirmDismiss: (direction) async {
        final provider = context.read<TaskProvider>();
        if (direction == DismissDirection.startToEnd && !isDone) {
          await provider.markDone(task.id);
        } else if (direction == DismissDirection.endToStart && isDone) {
          await provider.markTodo(task.id);
        }
        return false;
      },
      child: ListTile(
        leading: Checkbox(
          value: isDone,
          onChanged: (_) {
            final provider = context.read<TaskProvider>();
            isDone ? provider.markTodo(task.id) : provider.markDone(task.id);
          },
        ),
        title: Text(
          task.title,
          style: TextStyle(
            decoration: isDone ? TextDecoration.lineThrough : null,
            color: isDone ? cs.outline : null,
          ),
        ),
        subtitle: task.description.isNotEmpty
            ? Text(task.description,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: cs.outline))
            : null,
        trailing: _priorityChip(context, task.priority),
      ),
    );
  }

  Widget? _priorityChip(BuildContext context, String? priority) {
    if (priority == null || priority == 'normal') return null;
    final cs = Theme.of(context).colorScheme;
    final isHigh = priority == 'high';
    return Chip(
      label: Text(isHigh ? '高' : '低',
          style: TextStyle(
              fontSize: 11,
              color: isHigh ? cs.onErrorContainer : cs.onSurfaceVariant)),
      backgroundColor:
          isHigh ? cs.errorContainer : cs.surfaceContainerHighest,
      padding: EdgeInsets.zero,
      labelPadding: const EdgeInsets.symmetric(horizontal: 6),
      visualDensity: VisualDensity.compact,
    );
  }
}
