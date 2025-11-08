export type Restaurant = {
  id: string;
  name: string;
  status: string;
};

export type MenuItem = {
  id: string;
  name: string;
  description?: string | null;
  price: number;
  available: boolean;
};

export type OrderItemInput = {
  menu_item_id: string;
  quantity: number;
};

export type OrderSummary = {
  id: string;
  restaurant_id: string;
  status: string;
  total_amount: number | null;
  items: Array<{
    menu_item_id: string;
    name?: string;
    quantity: number;
    unit_price?: number;
    line_total?: number;
  }> | null;
  payment_reference?: string | null;
  failure_reason?: string | null;
  created_at: string;
  updated_at: string;
};
