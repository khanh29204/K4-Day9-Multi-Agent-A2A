"""Order & Product Agent - Analyzes order items, sellers, products, categories.

Responsibilities:
- Fetch all items for the order
- Look up product details and categories
- Identify seller information
- Use LLM to analyze order items, sellers, products, and categories
- Detect multi_item_order, multi_seller_order, multiple_categories

Data access: order_items, products, sellers, product_category_translation
"""
from typing import Any, Dict
from .base_agent import BaseAgent


class OrderProductAgent(BaseAgent):
    def __init__(self, llm_client, data_access):
        super().__init__("order_product_agent", llm_client, data_access)

    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze order items, products, and sellers.

        Expected context keys:
            - order_id: str

        Returns:
            - items: list of item dicts
            - products: list of product dicts
            - sellers: list of seller dicts
            - categories: list[str]
            - is_multi_item: bool
            - is_multi_seller: bool
            - is_multiple_categories: bool
            - affected_item_ids: list[str]
            - affected_seller_ids: list[str]
            - affected_product_ids: list[str]
        """
        order_id = context["order_id"]
        items = self.data.get_order_items(order_id)

        if not items:
            return {
                "items": [],
                "products": [],
                "sellers": [],
                "categories": [],
                "is_multi_item": False,
                "is_multi_seller": False,
                "is_multiple_categories": False,
                "affected_item_ids": [],
                "affected_seller_ids": [],
                "affected_product_ids": [],
            }

        products = []
        sellers = []
        categories = []
        affected_item_ids = []
        affected_seller_ids = []
        affected_product_ids = []

        seen_seller_ids = set()
        seen_product_ids = set()
        seen_categories = set()

        for item in items:
            item_seq = int(float(item['order_item_id'])) if item.get('order_item_id') is not None else 1
            affected_item_ids.append(f"{order_id}:{item_seq}")


            product_id = item.get("product_id")
            product = self.data.get_product(product_id) if product_id else None
            if product:
                products.append(product)
                category_name = product.get("product_category_name")
                if category_name and str(category_name).strip().lower() not in ("nan", "none", "nat", "") and category_name not in seen_categories:
                    seen_categories.add(category_name)
                    categories.append(category_name)



            if product_id and product_id not in seen_product_ids:
                seen_product_ids.add(product_id)
                affected_product_ids.append(product_id)

            seller_id = item.get("seller_id")
            seller = self.data.get_seller(seller_id) if seller_id else None
            if seller_id and seller_id not in seen_seller_ids:
                seen_seller_ids.add(seller_id)
                if seller:
                    sellers.append(seller)
                affected_seller_ids.append(seller_id)

        is_multi_item = len(items) >= 2
        is_multi_seller = len(seen_seller_ids) >= 2
        is_multiple_categories = len(seen_categories) >= 2

        # LLM reasoning integration
        if self.llm:
            try:
                system_prompt = (
                    "You are Order & Product Agent in an e-commerce multi-agent dispute resolution system. "
                    "Analyze the order items, sellers, product details, and category structure. "
                    "Return a JSON object evaluating item complexity, seller count, and category diversity."
                )
                user_prompt = (
                    f"Order ID: {order_id}\n"
                    f"Total item rows: {len(items)}\n"
                    f"Unique seller IDs: {affected_seller_ids}\n"
                    f"Categories (English): {categories}\n"
                    f"Flags: multi_item={is_multi_item}, multi_seller={is_multi_seller}, multi_category={is_multiple_categories}\n"
                    "Analyze and confirm the item and product structure in JSON format."
                )
                messages = self._build_prompt(system_prompt, user_prompt)
                llm_response = self.llm.chat_json(messages)
                self.logger.info(f"[{self.name}] LLM response received for order {order_id}")
            except Exception as e:
                self.logger.warning(f"[{self.name}] LLM analysis fallback due to: {e}")

        return {
            "items": items,
            "products": products,
            "sellers": sellers,
            "categories": categories,
            "is_multi_item": is_multi_item,
            "is_multi_seller": is_multi_seller,
            "is_multiple_categories": is_multiple_categories,
            "affected_item_ids": affected_item_ids[:5],
            "affected_seller_ids": affected_seller_ids[:3],
            "affected_product_ids": affected_product_ids[:5],
        }
