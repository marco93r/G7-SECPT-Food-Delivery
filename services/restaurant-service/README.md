# Restaurant Service

Der Restaurant-Service stellt Menüs bereit, bestätigt Bestellungen und kann sie im Fehlerfall stornieren. Er wird vom Order-Service über HTTP angesprochen und ist eigenständig lauffähig.

## Features
- `GET /healthz` – einfacher Health-Check
- `GET /restaurants` – listet alle Restaurants
- `GET /restaurants/{restaurant_id}/menu` – liefert Menüeinträge eines Restaurants
- `POST /restaurants/{restaurant_id}/orders` – bestätigt eine Bestellung (Saga-Step)
- `POST /restaurants/{restaurant_id}/orders/{order_id}/cancel` – kompensiert eine Bestellung

## Lokales Setup
```bash
cd services/restaurant-service
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
DATABASE_URL=postgresql://mifos:mifos@localhost:5432/restaurant_service uvicorn main:app --reload
```
Der Service erwartet eine Postgres-Datenbank (z. B. wie im Compose-Setup bereitgestellt). Für schnelle Experimente kannst du auch `DATABASE_URL=sqlite:///./restaurant.db` setzen – die Tabellen werden automatisch erzeugt und mit Beispieldaten befüllt.

## Docker
```bash
docker build -t mifos/restaurant-service:dev services/restaurant-service
docker run --rm -p 8082:8082 \
  -e DATABASE_URL=postgresql://mifos:mifos@restaurant-db:5432/restaurant_service \
  --network app \
  mifos/restaurant-service:dev
```
Im Verbund mit den anderen Komponenten wird der Service über `docker compose up` (Repository-Wurzel) gestartet. Standard-Endpunkt des Gateways lautet dann `http://localhost:8080/api/restaurants`.

## Tests
```bash
cd services/restaurant-service
pytest
```
