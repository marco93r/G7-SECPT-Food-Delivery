# Order Service

Der Order-Service ist das Orchestrierungs-Herzstück des miFOS-Systems. Er nimmt Kundenbestellungen entgegen, stößt die Bestätigung beim Restaurant-Service an und kümmert sich um die Zahlungsabwicklung (via Payment-Service bzw. Mock). Fehlerfälle werden über das Saga-Muster behandelt.

## Features
- `POST /orders` – legt eine neue Bestellung an, führt Restaurant- und Zahlungsaufrufe durch
- `GET /orders/{order_id}` – liefert den aktuellen Status einer Bestellung
- `POST /orders/{order_id}/cancel` – initiiert eine Kompensationsaktion
- `GET /orders?limit=50` – Bestellübersicht zur Überwachung von Sagas
- `GET /healthz` – einfacher Healthcheck
- Simulationen über `simulation_mode` (`payment_failure`, `restaurant_failure`) ermöglichen gezielte Saga-Tests

## Lokales Setup
```bash
cd services/order-service
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
DATABASE_URL=postgresql://mifos:mifos@localhost:5432/order_service \
RESTAURANT_SERVICE_URL=http://localhost:8082 \
uvicorn main:app --reload --port 8081
```

Wichtige Umgebungsvariablen:
- `DATABASE_URL` – Postgres-Verbindung (Compose stellt `postgresql://mifos:mifos@order-db:5432/order_service` bereit)
- `RESTAURANT_SERVICE_URL` – Endpoint des Restaurant-Services
- `PAYMENT_SERVICE_URL` – Endpoint des Payment-Services (nur bei `PAYMENT_MODE=http` erforderlich)
- `PAYMENT_MODE` – `mock` (default) oder `http`

## Docker
```bash
docker build -t mifos/order-service:dev services/order-service
docker run --rm -p 8081:8081 \
  -e DATABASE_URL=postgresql://mifos:mifos@order-db:5432/order_service \
  -e RESTAURANT_SERVICE_URL=http://restaurant-service:8082 \
  mifos/order-service:dev
```

### Zusammenspiel mit Payment-Service
Standardmäßig arbeitet der Service mit einem internen Mock. Läuft der echte Payment-Service (Compose-Profil `payment`), setze folgende Variablen vor dem Start:
```bash
PAYMENT_MODE=http PAYMENT_SERVICE_URL=http://payment-service:8083 docker compose --profile payment up --build
```
So werden reale Zahlungen ausgelöst und Refunds lassen sich über den Payment-Service testen.

## Tests
```bash
cd services/order-service
pytest
```
