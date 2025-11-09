# Frontend (React + Vite)

Modern Single-Page-App für das miFOS-System. Sie bedient direkt die REST-APIs von Restaurant- und Order-Service und bietet komfortable Funktionen zum Zusammenstellen einer Bestellung sowie zum Monitoring des Saga-Status.

## Features
- Restaurant-Auswahl mit Live-Menü
- Warenkorb inkl. Mengensteuerung und Kundenreferenz
- Bestellung auslösen (Order-Service) & Statusanzeige
- Checkbox zur Simulation eines Zahlungsfehlers (Saga-Kompensation testen)
- Bestellübersicht mit allen jüngsten Orders inkl. Failure Reason
- Moderne UI mit React 18 + Vite + CSS Gradients

## Lokales Setup
```bash
cd services/frontend
npm install
npm run dev -- --open
```

Standard-Umgebungsvariablen (können über `.env` oder CLI gesetzt werden):
```
VITE_RESTAURANT_API=https://localhost:8080
VITE_ORDER_API=https://localhost:8080
VITE_API_TOKEN=SECPT_TEST_TOKEN
```
`VITE_API_TOKEN` wird automatisch als Header `X-API-Token` an jede API-Request angefügt, damit das Kong-Gateway / die WAF nur authentifizierte Aufrufe durchlässt. Da das Frontend standardmäßig den via WAF exponierten HTTPS-Endpunkt (`https://localhost:8080`) nutzt, muss im Browser das selbstsignierte Zertifikat (`deploy/waf/certs/dev.crt`) vertraut oder die Warnung bestätigt werden.

## Build & Preview
```bash
npm run build
npm run preview
```

## Docker
```bash
docker build -f services/frontend/Dockerfile -t mifos/frontend:dev .
docker run --rm -p 4173:443 mifos/frontend:dev
```
Der Container liefert die Assets ausschließlich per HTTPS aus (`https://localhost:4173`) und nutzt dasselbe selbstsignierte Zertifikat wie das WAF (`deploy/waf/certs/dev.crt`).

Dabei können Build-Args gesetzt werden, um die API-Ziele anzupassen:
```bash
docker build \
  -f services/frontend/Dockerfile \
  --build-arg VITE_ORDER_API=http://order-service:8081 \
  --build-arg VITE_RESTAURANT_API=http://restaurant-service:8082 \
  --build-arg VITE_API_TOKEN=SECPT_TEST_TOKEN \
  -t mifos/frontend:dev .
```

## Compose
Der Frontend-Container ist dem Compose-Profil `ui` zugeordnet:
```bash
docker compose --profile ui up --build
```
