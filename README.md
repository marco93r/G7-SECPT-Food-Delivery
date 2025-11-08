# miFOS - Microservice Food Order System

Dieses Repository beherbergt die Microservices des miFOS-Systems. Die Architektur wird Schritt für Schritt aufgebaut: Zunächst stehen die Kernservices (Restaurant und Order) im Fokus. Edge-Komponenten wie API-Gateway und WAF sowie das Frontend sind über Compose-Profile zuschaltbar. Jede Domäne besitzt eine eigene Postgres-Datenbank, die ebenfalls per Compose bereitgestellt wird.

## Services & Profile

| Dienst              | Zweck                                 | Compose-Profil |
|---------------------|---------------------------------------|----------------|
| `restaurant-service`| Menüs verwalten, Orders bestätigen    | _immer aktiv_  |
| `order-service`     | Saga-Orchestrator                     | _immer aktiv_  |
| `payment-service`   | Zahlungsabwicklung                    | `payment`      |
| `frontend`          | React-App für Menüs & Orders          | `ui`           |
| `api-gateway`       | zentraler Einstiegspunkt (NGINX)      | `edge`         |
| `waf`               | ModSecurity + OWASP CRS vor dem Gateway | `edge`       |
| `restaurant-db`     | Postgres für Restaurant-Service       | _immer aktiv_  |
| `order-db`          | Postgres für Order-Service            | _immer aktiv_  |
| `payment-db`        | Postgres für Payment-Service          | `payment`      |

## Container starten

Basis-Setup (Restaurant + Order inkl. ihrer Datenbanken):
```bash
docker compose up --build
```

Zusätzliche Profile:
```bash
docker compose --profile edge up --build          # Gateway + WAF
docker compose --profile payment up --build       # Payment-Service (+ DB)
docker compose --profile ui up --build            # Frontend
docker compose --profile edge --profile ui --profile payment up --build  # Alles zusammen
```

Wichtige Umgebungsvariablen kannst du über `.env` setzen. Beispiele:
```bash
PAYMENT_MODE=http
PAYMENT_SERVICE_URL=http://payment-service:8083
PAYMENT_FAILURE_MODE=authorize   # simulate FT-01
VITE_ORDER_API=http://localhost:8081
VITE_RESTAURANT_API=http://localhost:8082
```

## Tests und Qualität
- Jeder Service besitzt eigene Pytest-Suites (`services/<name>/tests`).
- Sicherheitsberichte liegen unter `security_reports/` (semgrep, detect-secrets, pip-audit).
- Die WAF (ModSecurity + OWASP CRS) schützt das API-Gateway; verdächtige Requests auf Port 8080 werden geblockt.

## Nächste Schritte
1. End-to-End-Flows über `docker compose --profile ui --profile payment --profile edge up --build` testen (inkl. Saga-Simulationen via Checkbox im Frontend).
2. Fehlerfall FT-01 überprüfen: `Payment-Service` mit `PAYMENT_FAILURE_MODE=authorize` oder Frontend-Checkbox; in der Bestellübersicht sollte der Status `CANCELED` inkl. Failure Reason erscheinen.
3. CI/CD anpassen, sodass die neuen Postgres-Container und Profile automatisiert gebaut und getestet werden.
