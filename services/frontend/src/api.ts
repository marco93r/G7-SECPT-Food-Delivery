import type { MenuItem, OrderItemInput, OrderSummary, Restaurant } from "./types";

const RESTAURANT_API =
  import.meta.env.VITE_RESTAURANT_API ?? "http://localhost:8082";
const ORDER_API = import.meta.env.VITE_ORDER_API ?? "http://localhost:8081";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export async function fetchRestaurants(): Promise<Restaurant[]> {
  const response = await fetch(`${RESTAURANT_API}/restaurants`);
  return handleResponse(response);
}

export async function fetchMenu(restaurantId: string): Promise<MenuItem[]> {
  const response = await fetch(
    `${RESTAURANT_API}/restaurants/${restaurantId}/menu`,
  );
  return handleResponse(response);
}

export async function createOrder(params: {
  restaurantId: string;
  items: OrderItemInput[];
  customerReference?: string;
  simulationMode?: "payment_failure" | "restaurant_failure";
  orderId?: string;
}): Promise<OrderSummary> {
  const response = await fetch(`${ORDER_API}/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      restaurant_id: params.restaurantId,
      customer_reference: params.customerReference,
      items: params.items,
      simulation_mode: params.simulationMode,
      order_id: params.orderId,
    }),
  });
  return handleResponse(response);
}

export async function fetchOrder(orderId: string): Promise<OrderSummary> {
  const response = await fetch(`${ORDER_API}/orders/${orderId}`);
  return handleResponse(response);
}

export async function fetchOrderList(limit = 50): Promise<OrderSummary[]> {
  const response = await fetch(`${ORDER_API}/orders?limit=${limit}`);
  return handleResponse(response);
}
