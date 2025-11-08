import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { clsx } from "clsx";
import { PageShell } from "./components/Layout";
import {
  createOrder,
  fetchMenu,
  fetchOrder,
  fetchOrderList,
  fetchRestaurants,
} from "./api";
import type { MenuItem, OrderSummary, Restaurant } from "./types";
import "./app.css";

type CartState = Record<string, number>;

const currency = new Intl.NumberFormat("de-DE", {
  style: "currency",
  currency: "EUR",
});

const fallbackRestaurants: Restaurant[] = [
  { id: "resto-roma", name: "La Trattoria Roma", status: "ONLINE" },
  { id: "resto-kyoto", name: "Sakura Sushi Kyoto", status: "ONLINE" },
];

const fallbackMenus: Record<string, MenuItem[]> = {
  "resto-roma": [
    {
      id: "roma-carbonara",
      name: "Pasta Carbonara",
      description: "Mit Pancetta und Pecorino",
      price: 12.5,
      available: true,
    },
    {
      id: "roma-margherita",
      name: "Pizza Margherita",
      description: "San-Marzano-Tomaten & Büffelmozzarella",
      price: 10,
      available: true,
    },
  ],
  "resto-kyoto": [
    {
      id: "kyoto-salmon",
      name: "Lachs Nigiri Set",
      description: "8 Stück Nigiri",
      price: 15.5,
      available: true,
    },
    {
      id: "kyoto-ramen",
      name: "Shoyu Ramen",
      description: "Sojasud mit Hühnchen",
      price: 13,
      available: true,
    },
  ],
};

function SectionCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="card">
      <div className="card__heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

export default function App() {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [selectedRestaurant, setSelectedRestaurant] = useState<string>("");
  const [cart, setCart] = useState<CartState>({});
  const [customerNote, setCustomerNote] = useState("");

  const [orderResult, setOrderResult] = useState<OrderSummary | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [isPlacingOrder, setIsPlacingOrder] = useState(false);
  const [simulatePaymentFailure, setSimulatePaymentFailure] = useState(false);
  const [statusId, setStatusId] = useState("");
  const [statusResult, setStatusResult] = useState<OrderSummary | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [orderOverview, setOrderOverview] = useState<OrderSummary[]>([]);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  useEffect(() => {
    fetchRestaurants()
      .then((data) => {
        if (data.length === 0) {
          setRestaurants(fallbackRestaurants);
        } else {
          setRestaurants(data);
        }
      })
      .catch(() => {
        setOrderError("Backend nicht erreichbar – nutze Demodaten.");
        setRestaurants(fallbackRestaurants);
      });
  }, []);

  useEffect(() => {
    if (!selectedRestaurant) {
      setMenu([]);
      setCart({});
      return;
    }
    fetchMenu(selectedRestaurant)
      .then((items) => {
        if (items.length === 0) {
          setMenu(fallbackMenus[selectedRestaurant] ?? []);
        } else {
          setMenu(items);
        }
        setCart({});
      })
      .catch(() => {
        setOrderError("Konnte Menü nicht laden – zeige Demo-Auswahl.");
        setMenu(fallbackMenus[selectedRestaurant] ?? []);
      });
  }, [selectedRestaurant]);

  const cartItems = useMemo(() => {
    return Object.entries(cart)
      .map(([menuId, quantity]) => {
        const item = menu.find((m) => m.id === menuId);
        if (!item) return null;
        return { ...item, quantity, lineTotal: item.price * quantity };
      })
      .filter(Boolean) as Array<MenuItem & { quantity: number; lineTotal: number }>;
  }, [cart, menu]);

  const cartTotal = cartItems.reduce((sum, item) => sum + item.lineTotal, 0);

  const handleAddItem = (itemId: string) => {
    setCart((prev) => ({ ...prev, [itemId]: (prev[itemId] ?? 0) + 1 }));
  };

  const handleRemoveItem = (itemId: string) => {
    setCart((prev) => {
      const next = { ...prev };
      if (!next[itemId]) return next;
      if (next[itemId] === 1) {
        delete next[itemId];
      } else {
        next[itemId]! -= 1;
      }
      return next;
    });
  };

  const loadStatusFor = async (orderId: string) => {
    setLoadingStatus(true);
    setStatusError(null);
    setStatusId(orderId);
    try {
      const payload = await fetchOrder(orderId.trim());
      setStatusResult(payload);
      return payload;
    } catch (error) {
      setStatusError(error instanceof Error ? error.message : "Status konnte nicht geladen werden");
      setStatusResult(null);
      throw error;
    } finally {
      setLoadingStatus(false);
    }
  };

  const loadOverview = async () => {
    setOverviewLoading(true);
    setOverviewError(null);
    try {
      const data = await fetchOrderList(50);
      setOrderOverview(data);
    } catch (error) {
      setOverviewError(error instanceof Error ? error.message : "Bestellübersicht fehlgeschlagen");
    } finally {
      setOverviewLoading(false);
    }
  };

  useEffect(() => {
    loadOverview().catch(() => null);
  }, []);

  const placeOrder = async () => {
    if (!selectedRestaurant || cartItems.length === 0) return;
    setIsPlacingOrder(true);
    setOrderError(null);
    const generatedOrderId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `order-${Date.now()}`;
    try {
      const payload = await createOrder({
        restaurantId: selectedRestaurant,
        items: cartItems.map((item) => ({
          menu_item_id: item.id,
          quantity: item.quantity,
        })),
        customerReference: customerNote || undefined,
        simulationMode: simulatePaymentFailure ? "payment_failure" : undefined,
        orderId: generatedOrderId,
      });
      setOrderResult(payload);
      setStatusId(payload.id);
      setStatusResult(payload);
      setCart({});
      await loadOverview();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unbekannter Fehler";
      setOrderError(`${message} – Order-ID ${generatedOrderId}`);
      try {
        await loadStatusFor(generatedOrderId);
        await loadOverview();
      } catch {
        // Monitoring schlug fehl; Fehler wird bereits im Status-Panel angezeigt
      }
    } finally {
      setIsPlacingOrder(false);
    }
  };

  const loadStatus = async () => {
    if (!statusId) return;
    await loadStatusFor(statusId);
    await loadOverview();
  };

  return (
    <PageShell>
      <SectionCard
        title="1. Restaurant & Menü"
        subtitle="Wähle ein Restaurant aus und stelle deine Wunschkombination zusammen."
      >
        <div className="restaurant-picker">
          <label htmlFor="restaurant-select">Restaurant</label>
          <select
            id="restaurant-select"
            value={selectedRestaurant}
            onChange={(event) => setSelectedRestaurant(event.target.value)}
          >
            <option value="">Bitte auswählen</option>
            {restaurants.map((restaurant) => (
              <option key={restaurant.id} value={restaurant.id}>
                {restaurant.name}
              </option>
            ))}
          </select>
        </div>

        <div className="menu-grid">
          {menu.map((item) => (
            <article key={item.id} className={clsx("menu-card", { disabled: !item.available })}>
              <div>
                <h3>{item.name}</h3>
                {item.description && <p>{item.description}</p>}
              </div>
              <div className="menu-card__meta">
                <span>{currency.format(item.price)}</span>
                <button
                  type="button"
                  disabled={!item.available}
                  onClick={() => handleAddItem(item.id)}
                >
                  Hinzufügen
                </button>
              </div>
            </article>
          ))}
          {menu.length === 0 && (
            <p className="muted">
              Noch kein Menü geladen. Bitte ein Restaurant auswählen.
            </p>
          )}
        </div>
      </SectionCard>

      <SectionCard
        title="2. Warenkorb & Bestellung"
        subtitle="Überprüfe deine Auswahl und löse die Saga im Order-Service aus."
      >
        <div className="cart-panel">
          {cartItems.length === 0 && <p className="muted">Dein Warenkorb ist leer.</p>}
          {cartItems.map((item) => (
            <div key={item.id} className="cart-item">
              <div>
                <strong>{item.name}</strong>
                <small>{currency.format(item.price)} · Menge {item.quantity}</small>
              </div>
              <div className="cart-item__actions">
                <button onClick={() => handleRemoveItem(item.id)}>-</button>
                <span>{item.quantity}</span>
                <button onClick={() => handleAddItem(item.id)}>+</button>
              </div>
            </div>
          ))}
        </div>
        <label className="note-field">
          Kundenreferenz (optional)
          <input
            type="text"
            value={customerNote}
            onChange={(event) => setCustomerNote(event.target.value)}
            placeholder="z. B. Tisch 4 oder Tracking-ID"
          />
        </label>
        <label className="toggle-field">
          <input
            type="checkbox"
            checked={simulatePaymentFailure}
            onChange={(event) => setSimulatePaymentFailure(event.target.checked)}
          />
          Zahlungsausfall simulieren (Saga-Failure-Test)
        </label>

        <div className="order-summary">
          <div>
            <span>Zwischensumme</span>
            <strong>{currency.format(cartTotal)}</strong>
          </div>
          <button
            type="button"
            className="primary"
            disabled={cartItems.length === 0 || !selectedRestaurant || isPlacingOrder}
            onClick={placeOrder}
          >
            {isPlacingOrder ? "Bestellung wird gesendet..." : "Bestellung auslösen"}
          </button>
          {orderError && <p className="error">{orderError}</p>}
          {orderResult && (
            <p className="success">
              Bestellung `{orderResult.id}` bestätigt – Status: {orderResult.status}
            </p>
          )}
        </div>
      </SectionCard>

      <SectionCard
        title="3. Saga Monitoring"
        subtitle="Aktuellen Status abfragen – inkl. Failure Reason bei Kompensation."
      >
        <div className="status-panel">
          <label>
            Order-ID
            <input
              type="text"
              value={statusId}
              onChange={(event) => setStatusId(event.target.value)}
              placeholder="order-123..."
            />
          </label>
          <button type="button" className="ghost" onClick={loadStatus} disabled={!statusId || loadingStatus}>
            {loadingStatus ? "Lade..." : "Status abrufen"}
          </button>
          {statusError && <p className="error">{statusError}</p>}
          {statusResult && (
            <div className="status-card">
              <header>
                <strong>Status:</strong>
                <span className={`badge badge--${statusResult.status.toLowerCase()}`}>
                  {statusResult.status}
                </span>
              </header>
              <dl>
                <div>
                  <dt>Gesamt</dt>
                  <dd>{statusResult.total_amount ? currency.format(statusResult.total_amount) : "–"}</dd>
                </div>
                <div>
                  <dt>Payment</dt>
                  <dd>{statusResult.payment_reference ?? "–"}</dd>
                </div>
                <div>
                  <dt>Failure Reason</dt>
                  <dd>{statusResult.failure_reason ?? "–"}</dd>
                </div>
              </dl>
            </div>
          )}
        </div>
      </SectionCard>

      <SectionCard
        title="4. Bestellübersicht"
        subtitle="Zeigt die zuletzt aktualisierten Orders inkl. Status und Failure Reason."
      >
        <div className="overview-actions">
          <button type="button" className="ghost" onClick={loadOverview} disabled={overviewLoading}>
            {overviewLoading ? "Aktualisiere..." : "Aktualisieren"}
          </button>
          {overviewError && <p className="error">{overviewError}</p>}
        </div>
        <div className="overview-list">
          {orderOverview.map((order) => (
            <article key={order.id} className="status-card">
              <header>
                <div>
                  <strong>{order.id}</strong>
                  <small>Restaurant: {order.restaurant_id}</small>
                </div>
                <span className={`badge badge--${order.status.toLowerCase()}`}>{order.status}</span>
              </header>
              <dl>
                <div>
                  <dt>Updated</dt>
                  <dd>{new Date(order.updated_at).toLocaleString("de-DE")}</dd>
                </div>
                <div>
                  <dt>Amount</dt>
                  <dd>
                    {order.total_amount ? currency.format(order.total_amount) : "–"}
                  </dd>
                </div>
                <div>
                  <dt>Payment</dt>
                  <dd>{order.payment_reference ?? "–"}</dd>
                </div>
                <div>
                  <dt>Failure Reason</dt>
                  <dd>{order.failure_reason ?? "–"}</dd>
                </div>
              </dl>
            </article>
          ))}
          {orderOverview.length === 0 && !overviewLoading && (
            <p className="muted">Noch keine Orders gespeichert.</p>
          )}
        </div>
      </SectionCard>
    </PageShell>
  );
}
