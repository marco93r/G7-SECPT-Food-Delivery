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
VITE_RESTAURANT_API=http://localhost:8082
VITE_ORDER_API=http://localhost:8081
VITE_API_TOKEN=SECPT_TEST_TOKEN
```
`VITE_API_TOKEN` wird automatisch als Header `X-API-Token` an jede API-Request angefügt, damit das Kong-Gateway / die WAF nur authentifizierte Aufrufe durchlässt.

## Build & Preview
```bash
npm run build
npm run preview
```

## Docker
```bash
docker build -t mifos/frontend:dev services/frontend
docker run --rm -p 4173:80 mifos/frontend:dev
```
Dabei können Build-Args gesetzt werden, um die API-Ziele anzupassen:
```bash
docker build \
  --build-arg VITE_ORDER_API=http://order-service:8081 \
  --build-arg VITE_RESTAURANT_API=http://restaurant-service:8082 \
  --build-arg VITE_API_TOKEN=SECPT_TEST_TOKEN \
  -t mifos/frontend:dev services/frontend
```

## Compose
Der Frontend-Container ist dem Compose-Profil `ui` zugeordnet:
```bash
docker compose --profile ui up --build
```
