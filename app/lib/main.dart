import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'services/settings_service.dart';
import 'services/api_service.dart';
import 'providers/chat_provider.dart';
import 'providers/task_provider.dart';
import 'providers/calendar_provider.dart';
import 'providers/entity_provider.dart';
import 'screens/chat_screen.dart';
import 'screens/tasks_screen.dart';
import 'screens/calendar_screen.dart';
import 'screens/entity_browser.dart';
import 'screens/settings_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('zh_CN', null);
  final settings = await SettingsService.getInstance();
  runApp(AssistantApp(settings: settings));
}

class AssistantApp extends StatelessWidget {
  final SettingsService settings;
  const AssistantApp({super.key, required this.settings});

  @override
  Widget build(BuildContext context) {
    final api = ApiService(settings);
    return MultiProvider(
      providers: [
        Provider<SettingsService>.value(value: settings),
        Provider<ApiService>.value(value: api),
        ChangeNotifierProvider(create: (_) => ChatProvider(settings)),
        ChangeNotifierProvider(create: (_) => TaskProvider(api)),
        ChangeNotifierProvider(create: (_) => CalendarProvider(api)),
        ChangeNotifierProvider(create: (_) => EntityProvider(api)),
      ],
      child: MaterialApp(
        title: 'AI 助理',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF6750A4),
            brightness: Brightness.light,
          ),
          useMaterial3: true,
        ),
        darkTheme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF6750A4),
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
        ),
        home: const _HomeShell(),
      ),
    );
  }
}

class _HomeShell extends StatefulWidget {
  const _HomeShell();

  @override
  State<_HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<_HomeShell> {
  int _index = 0;

  static const _screens = [
    ChatScreen(),
    TasksScreen(),
    CalendarScreen(),
    EntityBrowser(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: _screens,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(Icons.chat_bubble),
            label: '聊天',
          ),
          NavigationDestination(
            icon: Icon(Icons.task_outlined),
            selectedIcon: Icon(Icons.task),
            label: '任务',
          ),
          NavigationDestination(
            icon: Icon(Icons.calendar_today_outlined),
            selectedIcon: Icon(Icons.calendar_today),
            label: '日程',
          ),
          NavigationDestination(
            icon: Icon(Icons.hub_outlined),
            selectedIcon: Icon(Icons.hub),
            label: '实体',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: '设置',
          ),
        ],
      ),
    );
  }
}
