import type { MenuItem, OrderItemInput, OrderSummary, Restaurant } from "./types";

const RESTAURANT_API =
  import.meta.env.VITE_RESTAURANT_API ?? "http://localhost:8082";
const ORDER_API = import.meta.env.VITE_ORDER_API ?? "http://localhost:8081";
const API_TOKEN = import.meta.env.VITE_API_TOKEN;

function withAuth(init: RequestInit = {}): RequestInit {
  if (!API_TOKEN) {
    return init;
  }
  const headers = new Headers(init.headers ?? {});
  headers.set("X-API-Token", API_TOKEN);
  return { ...init, headers };
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export async function fetchRestaurants(): Promise<Restaurant[]> {
  const response = await fetch(
    `${RESTAURANT_API}/restaurants`,
    withAuth(),
  );
  return handleResponse(response);
}

export async function fetchMenu(restaurantId: string): Promise<MenuItem[]> {
  const response = await fetch(
    `${RESTAURANT_API}/restaurants/${restaurantId}/menu`,
    withAuth(),
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
  const response = await fetch(
    `${ORDER_API}/orders`,
    withAuth({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: params.restaurantId,
        customer_reference: params.customerReference,
        items: params.items,
        simulation_mode: params.simulationMode,
        order_id: params.orderId,
      }),
    }),
  );
  return handleResponse(response);
}

export async function fetchOrder(orderId: string): Promise<OrderSummary> {
  const response = await fetch(
    `${ORDER_API}/orders/${orderId}`,
    withAuth(),
  );
  return handleResponse(response);
}

export async function fetchOrderList(limit = 50): Promise<OrderSummary[]> {
  const response = await fetch(
    `${ORDER_API}/orders?limit=${limit}`,
    withAuth(),
  );
  return handleResponse(response);
}
