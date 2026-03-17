import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

class AuthorityLandingRedirectScreen extends StatefulWidget {
  const AuthorityLandingRedirectScreen({super.key});

  @override
  State<AuthorityLandingRedirectScreen> createState() =>
      _AuthorityLandingRedirectScreenState();
}

class _AuthorityLandingRedirectScreenState
    extends State<AuthorityLandingRedirectScreen> {
  String? _targetUrl;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _redirectToAuthority();
  }

  Future<void> _redirectToAuthority() async {
    const authorityFromEnv = String.fromEnvironment(
      'AUTHORITY_WEB_URL',
      defaultValue: '',
    );
    final authorityUrl =
        authorityFromEnv.isNotEmpty ? authorityFromEnv : 'http://localhost:5174';

    setState(() {
      _targetUrl = authorityUrl;
      _errorMessage = null;
    });

    try {
      final launched = await launchUrl(
        Uri.parse(authorityUrl),
        webOnlyWindowName: '_self',
      );

      if (!launched) {
        setState(() {
          _errorMessage = 'Could not launch authority landing page.';
        });
      }
    } catch (_) {
      setState(() {
        _errorMessage = 'Unable to open authority landing page.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_errorMessage != null) {
      return Scaffold(
        backgroundColor: const Color(0xFF111827),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error_outline, color: Colors.redAccent, size: 56),
                const SizedBox(height: 16),
                Text(
                  _errorMessage!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white, fontSize: 18),
                ),
                const SizedBox(height: 8),
                Text(
                  _targetUrl ?? 'http://localhost:5174',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white70),
                ),
                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: _redirectToAuthority,
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFF111827),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            const Text(
              'Redirecting to authority command center...',
              style: TextStyle(color: Colors.white, fontSize: 16),
            ),
            const SizedBox(height: 8),
            Text(
              _targetUrl ?? 'http://localhost:5174',
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }
}
