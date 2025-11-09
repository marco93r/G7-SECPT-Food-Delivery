# miFOS - Microservice Food Order System

Dieses Repository beherbergt die Microservices des miFOS-Systems. Die Architektur wird Schritt für Schritt aufgebaut: Zunächst stehen die Kernservices (Restaurant und Order) im Fokus. Zusätzliche Komponenten (Frontend, Payment, Kong Gateway) lassen sich über Docker-Compose-Profile zuschalten. Jede Domäne besitzt eine eigene Postgres-Datenbank.

## Services & Profile

| Dienst              | Zweck                                 | Compose-Profil |
|---------------------|---------------------------------------|----------------|
| `restaurant-service`| Menüs verwalten, Orders bestätigen    | _immer aktiv_  |
| `order-service`     | Saga-Orchestrator                     | _immer aktiv_  |
| `payment-service`   | Zahlungsabwicklung                    | `payment`      |
| `frontend`          | React-App für Menüs & Orders          | `ui`           |
| `api-gateway`       | Kong Gateway (intern, via WAF erreichbar) | `edge`     |
| `waf`               | ModSecurity/OWASP CRS vor dem Gateway | `edge`         |
| `restaurant-db`     | Postgres für Restaurant-Service       | _immer aktiv_  |
| `order-db`          | Postgres für Order-Service            | _immer aktiv_  |
| `payment-db`        | Postgres für Payment-Service          | `payment`      |

## Container starten

Basis-Setup (Restaurant + Order inkl. Datenbanken):
```bash
docker compose up --build
```

Zusätzliche Profile:
```bash
docker compose --profile edge up --build          # WAF (Port 8080) + Kong
docker compose --profile payment up --build       # Payment-Service (+ DB)
docker compose --profile ui up --build            # Frontend
docker compose --profile edge --profile ui --profile payment up --build  # Alles zusammen
```

Wichtige Umgebungsvariablen (z. B. in `.env`):
```bash
PAYMENT_MODE=http
PAYMENT_SERVICE_URL=http://payment-service:8083
PAYMENT_FAILURE_MODE=authorize
VITE_ORDER_API=http://localhost:8081          # oder http://localhost:8080/api/orders
VITE_RESTAURANT_API=http://localhost:8082     # oder http://localhost:8080/api/restaurants
VITE_API_TOKEN=SECPT_TEST_TOKEN               # muss zum Kong-Key passen
```

Im Edge-Profil läuft eine WAF vor dem Gateway; alle externen Aufrufe gehen über `http://localhost:8080` und benötigen den statischen Token `SECPT_TEST_TOKEN` (Header `X-API-Token`).
```bash
curl -H "X-API-Token: SECPT_TEST_TOKEN" http://localhost:8080/api/restaurants/restaurants
curl -H "X-API-Token: SECPT_TEST_TOKEN" http://localhost:8080/api/orders/healthz
```

## Tests und Qualität
- Jeder Service besitzt eigene Pytest-Suites (`services/<name>/tests`).
- Sicherheitsberichte liegen unter `security_reports/` (semgrep, detect-secrets, pip-audit).
- Für DAST-Scans kann z. B. OWASP ZAP gegen `http://localhost:8080` gefahren werden (siehe `security_reports/README.md`).

## Nächste Schritte
1. End-to-End-Flows über `docker compose --profile ui --profile payment --profile edge up --build` testen (inkl. Saga-Simulation via Checkbox im Frontend).
2. Fehlerfall FT-01 prüfen: `PAYMENT_FAILURE_MODE=authorize` oder Frontend-Checkbox aktivieren; in der Bestellübersicht muss der Status `CANCELED` samt Failure Reason erscheinen.
3. CI/CD erweitern, sodass die neuen Postgres-Container und Profile automatisiert gebaut und getestet werden.
