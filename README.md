# G7-SECPT-Food-Delivery

Microservice‑Prototyp einer Food‑Delivery‑Plattform mit drei unabhängigen Services (Order, Restaurant, Payment), Orchestrierung per Saga‑Muster, API‑Gateway (NGINX) und vorgeschalteter WAF (ModSecurity + OWASP CRS). Jeder Service hat eine eigene Datenhaltung (SQLite). Die gesamte Lösung ist per Docker Compose containerisiert.

## Architektur
- WAF: ModSecurity mit OWASP CRS, HTTPS‑Termination (Self‑Signed), filtert eingehenden Traffic und leitet an das API‑Gateway weiter
- API‑Gateway: NGINX‑Routing zu den Services, prüft API‑Key
- Order‑Service: Orchestrator des Bestellprozesses (Saga, Kompensation)
- Restaurant‑Service: Menüs und Reservierung/Storno
- Payment‑Service: Autorisierung, Capture, Refund; Failure‑Toggle für Tests
- Datenbanken: je Service eine SQLite‑DB unter `/data` (Volumes)

Eintrittspunkte lokal:
- `https://localhost:8443` (WAF, inkl. Frontend, TLS via Self‑Signed)
- `http://localhost:8080` (WAF HTTP – leitet automatisch auf HTTPS um)
- `http://localhost:8081` (direkt zum API‑Gateway, ohne WAF, für Diagnose)

Auth: Einfache API‑Key‑Prüfung über Header `X-API-Key` (Default: `changeme`). Der API‑Key wird am API‑Gateway validiert; Services prüfen zusätzlich (Defense in Depth).

## Schnellstart
Voraussetzungen: Docker, Docker Compose.

1) Standard‑Start (ohne Fehler‑Simulation)

```
docker compose up --build
```

- Health‑Check: `https://localhost:8443/healthz` (Self‑Signed; Browser/`curl -k` akzeptieren)

2) Fault‑Tolerance‑Profil (FT‑01: Autorisierung schlägt fehl)

```
docker compose -f docker-compose.yml -f docker-compose.ft.yml up --build
```

Dieses Profil setzt `PAYMENT_FAIL_AUTHORIZE=true` im Payment‑Service.

Optional: Eigenen API‑Key setzen

- `set API_KEY=mein-key` (PowerShell: `$env:API_KEY="mein-key"`) vor `docker compose up`
- Bei allen Requests Header `X-API-Key: mein-key` mitschicken

## Frontend
Das Frontend (statische SPA) wird über die WAF ausgeliefert:
- Hauptseite: `https://localhost:8443/`
- Checks/Diagnose: `https://localhost:8443/checks.html`

Hauptseite:
- API‑Key setzen (in `localStorage` gespeichert)
- Menüs laden, Warenkorb füllen, Bestellung auslösen, Bestellstatus prüfen

Checks‑Seite:
- Health‑Checks: WAF `/healthz`, Services via Gateway `/api/*/healthz`
- API‑Checks: Menüs abrufen und Demo‑Bestellung absetzen

## Endpunkte (Gateway → Services)
- `GET /api/restaurants/menus` → Restaurant: Menüs abrufen
- `POST /api/orders/orders` → Order: Bestellung anlegen und Saga ausführen
- `GET /api/orders/orders/{id}` → Order: Bestellstatus abfragen

Healthchecks:
- `GET /healthz` (WAF; HTTP/80 leitet sonst auf HTTPS um)
- `GET /api/orders/healthz`, `GET /api/restaurants/healthz`, `GET /api/payments/healthz` (direkt via Gateway)

Header immer setzen: `X-API-Key: <API_KEY>`

## Beispiel‑Requests
1) Menüs abrufen

```
curl -k -H "X-API-Key: changeme" https://localhost:8443/api/restaurants/menus
```

2) Bestellung anlegen (Erfolgsfall ohne FT‑Profil)

```
curl -k -X POST https://localhost:8443/api/orders/orders \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
    "customer_id": "c-123",
    "items": [
      {"name": "Pizza Margherita", "price": 10.5, "quantity": 1},
      {"name": "Caesar Salad", "price": 8.5, "quantity": 1}
    ]
  }'
```

3) Status abfragen

```
curl -k -H "X-API-Key: changeme" https://localhost:8443/api/orders/orders/<order_id>
```

## Fault‑Tolerance‑Test FT‑01
Ziel: Zahlungsauthorisierung schlägt fehl, Kompensation greift (Storno im Restaurant) und Bestellung wird `CANCELED`.

1. Start mit FT‑Compose‑Datei (siehe oben)
2. Bestellung anlegen (wie oben). Der Payment‑Service liefert `status: FAILED` bei `/authorize`.
3. Erwartet: Order‑Service kompensiert – Restaurant‑Storno, Bestellung `CANCELED`.
4. Status prüfen:

```
curl -k -H "X-API-Key: changeme" https://localhost:8443/api/orders/orders/<order_id>
```

## Projektstruktur
- `services/order-service`: FastAPI + SQLite, Orchestrierung/Saga
- `services/restaurant-service`: FastAPI + SQLite, Menüs + Reservierungen
- `services/payment-service`: FastAPI + SQLite, Zahlung (Authorize/Capture/Refund), Toggle `PAYMENT_FAIL_AUTHORIZE`
- `api-gateway`: NGINX Config und Image (API‑Key‑Prüfung)
- `waf`: NGINX mit ModSecurity + OWASP CRS, TLS‑Termination
- `docker-compose.yml`: Basis‑Setup inkl. WAF/Gateway/Services
- `docker-compose.ft.yml`: FT‑Profil (Authorize‑Fehler aktiv)

## Sicherheit
- WAF filtert eingehende Requests (SQLi, XSS etc.) und terminiert TLS.
- API‑Gateway bündelt externe Zugriffe und prüft den API‑Key.
- Services verlangen API‑Key zusätzlich (Defense in Depth).
- Saga implementiert Kompensation für Payment‑Authorize‑Fehler (FT‑01) sowie nachgelagert für Capture‑Fehler.

## Hinweise
- SQLite ist für den Prototyp gewählt. In Produktion je Service eine dedizierte DB‑Instanz (z. B. Postgres) verwenden.
