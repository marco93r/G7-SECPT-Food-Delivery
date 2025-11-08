# Payment Service

Der Payment-Service kümmert sich um Autorisierungen, Captures und Refunds. Über Umgebungsvariablen lässt sich Fehlverhalten simulieren, damit Saga-Kompensationen getestet werden können.

## Endpunkte
- `GET /healthz` – Health-Check
- `POST /payments` – autorisiert & captured eine Zahlung (`{order_id, amount}`)
- `GET /payments/{payment_id}` – liefert Zahlungsdetails
- `POST /payments/{payment_id}/refund` – führt einen Refund durch

## Konfiguration
- `DATABASE_URL` – Postgres-Verbindung (Compose: `postgresql://mifos:mifos@payment-db:5432/payment_service`)
- `FAILURE_MODE` – `none` (default), `authorize`, `capture`, `refund`

## Lokales Setup
```bash
cd services/payment-service
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
DATABASE_URL=postgresql://mifos:mifos@localhost:5432/payment_service uvicorn main:app --reload --port 8083
```

## Docker
```bash
docker build -t mifos/payment-service:dev services/payment-service
docker run --rm -p 8083:8083 \
  -e DATABASE_URL=postgresql://mifos:mifos@payment-db:5432/payment_service \
  mifos/payment-service:dev
```

## Tests
```bash
cd services/payment-service
pytest
```

## Zusammenspiel mit Order-Service
Beim Start via Compose kann der Order-Service auf HTTP-Zahlungen umgestellt werden:
```bash
PAYMENT_MODE=http PAYMENT_SERVICE_URL=http://payment-service:8083 docker compose --profile payment up --build
```
So testest du End-to-End inklusive Autorisierung und Refund – in Kombination mit `FAILURE_MODE` lassen sich auch gezielt Fehler provozieren.
