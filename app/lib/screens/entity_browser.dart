import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/entity.dart';
import '../providers/entity_provider.dart';

class EntityBrowser extends StatefulWidget {
  const EntityBrowser({super.key});

  @override
  State<EntityBrowser> createState() => _EntityBrowserState();
}

class _EntityBrowserState extends State<EntityBrowser>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;

  static const _types = ['person', 'company', 'project', 'product'];
  static const _labels = ['人员', '公司', '项目', '产品'];
  static const _icons = [
    Icons.person_outline,
    Icons.business_outlined,
    Icons.folder_outlined,
    Icons.inventory_2_outlined,
  ];

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: _types.length, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<EntityProvider>().loadAll();
    });
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('实体'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => context.read<EntityProvider>().loadAll(),
          ),
        ],
        bottom: TabBar(
          controller: _tabs,
          tabs: List.generate(
            _types.length,
            (i) => Tab(icon: Icon(_icons[i]), text: _labels[i]),
          ),
        ),
      ),
      body: Consumer<EntityProvider>(
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
                    onPressed: () => provider.loadAll(),
                    child: const Text('重试'),
                  ),
                ],
              ),
            );
          }
          return TabBarView(
            controller: _tabs,
            children: List.generate(
              _types.length,
              (i) => RefreshIndicator(
                onRefresh: provider.loadAll,
                child: _EntityList(
                  entities: provider.entitiesOf(_types[i]),
                  emptyLabel: _labels[i],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _EntityList extends StatelessWidget {
  final List<Entity> entities;
  final String emptyLabel;
  const _EntityList({required this.entities, required this.emptyLabel});

  @override
  Widget build(BuildContext context) {
    if (entities.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.search_off,
                size: 48,
                color: Theme.of(context).colorScheme.outlineVariant),
            const SizedBox(height: 12),
            Text('暂无$emptyLabel',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(color: Theme.of(context).colorScheme.outline)),
          ],
        ),
      );
    }
    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemCount: entities.length,
      separatorBuilder: (_, _) => const Divider(indent: 16, endIndent: 16),
      itemBuilder: (_, i) => _EntityTile(entity: entities[i]),
    );
  }
}

class _EntityTile extends StatelessWidget {
  final Entity entity;
  const _EntityTile({required this.entity});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final attrs = entity.attributes;
    final subtitle = attrs.entries
        .where((e) => e.key != 'name' && e.value.toString().isNotEmpty)
        .take(3)
        .map((e) => '${e.key}: ${e.value}')
        .join(' · ');

    return ListTile(
      leading: CircleAvatar(
        backgroundColor: cs.secondaryContainer,
        child: Text(
          entity.name.isNotEmpty ? entity.name[0].toUpperCase() : '?',
          style: TextStyle(
              color: cs.onSecondaryContainer, fontWeight: FontWeight.bold),
        ),
      ),
      title: Text(entity.name),
      subtitle: subtitle.isNotEmpty
          ? Text(subtitle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(color: cs.outline, fontSize: 12))
          : null,
      onTap: () => _showDetail(context),
    );
  }

  void _showDetail(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.5,
        maxChildSize: 0.85,
        builder: (_, controller) => _EntityDetailSheet(
            entity: entity, scrollController: controller),
      ),
    );
  }
}

class _EntityDetailSheet extends StatelessWidget {
  final Entity entity;
  final ScrollController scrollController;
  const _EntityDetailSheet(
      {required this.entity, required this.scrollController});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final attrs = entity.attributes.entries.toList();

    return Column(
      children: [
        Container(
          margin: const EdgeInsets.only(top: 8, bottom: 4),
          width: 36,
          height: 4,
          decoration: BoxDecoration(
            color: cs.outlineVariant,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              CircleAvatar(
                radius: 24,
                backgroundColor: cs.secondaryContainer,
                child: Text(
                  entity.name.isNotEmpty ? entity.name[0].toUpperCase() : '?',
                  style: TextStyle(
                      color: cs.onSecondaryContainer,
                      fontWeight: FontWeight.bold,
                      fontSize: 20),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(entity.name,
                        style: Theme.of(context).textTheme.titleLarge),
                    Text(entity.type,
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: cs.outline)),
                  ],
                ),
              ),
            ],
          ),
        ),
        const Divider(),
        Expanded(
          child: ListView.separated(
            controller: scrollController,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            itemCount: attrs.length,
            separatorBuilder: (_,_) => const SizedBox(height: 8),
            itemBuilder: (_, i) {
              final e = attrs[i];
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 80,
                    child: Text(e.key,
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: cs.outline)),
                  ),
                  Expanded(
                    child: Text(e.value.toString(),
                        style: Theme.of(context).textTheme.bodyMedium),
                  ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}
