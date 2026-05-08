import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/chat_provider.dart';
import '../services/settings_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _urlController;
  late final TextEditingController _tokenController;
  bool _tokenObscured = true;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    final s = context.read<SettingsService>();
    _urlController = TextEditingController(text: s.serverUrl);
    _tokenController = TextEditingController(text: s.authToken);
  }

  Future<void> _save() async {
    final s = context.read<SettingsService>();
    await s.setServerUrl(_urlController.text.trim());
    await s.setAuthToken(_tokenController.text.trim());
    if (mounted) {
      context.read<ChatProvider>().connect();
      setState(() => _saved = true);
      Future.delayed(const Duration(seconds: 2), () {
        if (mounted) setState(() => _saved = false);
      });
    }
  }

  @override
  void dispose() {
    _urlController.dispose();
    _tokenController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('设置')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _SectionTitle(title: '服务器配置'),
          const SizedBox(height: 8),
          TextField(
            controller: _urlController,
            keyboardType: TextInputType.url,
            autocorrect: false,
            decoration: const InputDecoration(
              labelText: '服务器地址',
              hintText: 'http://192.168.1.x:8000',
              prefixIcon: Icon(Icons.dns_outlined),
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _tokenController,
            obscureText: _tokenObscured,
            autocorrect: false,
            decoration: InputDecoration(
              labelText: 'Auth Token（可选）',
              hintText: '留空则无需验证',
              prefixIcon: const Icon(Icons.key_outlined),
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(
                icon: Icon(_tokenObscured
                    ? Icons.visibility_outlined
                    : Icons.visibility_off_outlined),
                onPressed: () =>
                    setState(() => _tokenObscured = !_tokenObscured),
              ),
            ),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: _save,
            icon: _saved
                ? const Icon(Icons.check)
                : const Icon(Icons.save_outlined),
            label: Text(_saved ? '已保存' : '保存并重新连接'),
          ),
          const SizedBox(height: 32),
          _SectionTitle(title: '连接状态'),
          const SizedBox(height: 8),
          Consumer<ChatProvider>(
            builder: (_, chat,_) => Card(
              child: ListTile(
                leading: Icon(
                  Icons.circle,
                  size: 14,
                  color: chat.connected ? Colors.green : Colors.red,
                ),
                title: Text(chat.connected ? 'WebSocket 已连接' : 'WebSocket 未连接'),
                trailing: TextButton(
                  onPressed: chat.connect,
                  child: const Text('重新连接'),
                ),
              ),
            ),
          ),
          const SizedBox(height: 32),
          _SectionTitle(title: '关于'),
          const SizedBox(height: 8),
          const Card(
            child: Column(
              children: [
                ListTile(
                  leading: Icon(Icons.info_outline),
                  title: Text('AI 工作助理'),
                  trailing: Text('v0.1.0'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;
  const _SectionTitle({required this.title});

  @override
  Widget build(BuildContext context) {
    return Text(title,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
            color: Theme.of(context).colorScheme.primary));
  }
}
