# Deployment checks

Run from the repository root with Python 3 and PyYAML 6.0.3 available:

```bash
python3 vinchi/tests/chatbotx-deploy-check.py
python3 vinchi/tests/chatbotx-proxy-check.py /absolute/path/to/caddy
```

The second command requires a trusted Caddy 2.10.2 executable and starts only temporary loopback servers with synthetic secrets. It checks missing/wrong secrets, bot identity, duplicate botId parameters, channel aliases, signed storage paths and realtime prefix stripping. It does not connect to Telegram or ChatbotX.

Both checks passed locally on 2026-09-28 after transferring the package into this repository. Full Docker Compose execution, image pulls, database migration, provider credentials and real messages have not been tested here. Repeat validation and acceptance tests on the actual staging server before production.
