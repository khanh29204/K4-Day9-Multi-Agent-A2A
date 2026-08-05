"""Tests for OrderProductAgent output limits.

Run with: python3 -m unittest codebase.tests.test_order_product_agent -v
"""
import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.order_product_agent import OrderProductAgent


class FakeDataAccess:
    """In-memory stand-in for DataAccess, no pandas/CSV required."""

    def __init__(self, items, products=None, sellers=None):
        self._items = items
        self._products = products or {}
        self._sellers = sellers or {}

    def get_order_items(self, order_id):
        return [item for item in self._items if item["order_id"] == order_id]

    def get_product(self, product_id):
        return self._products.get(product_id)

    def get_seller(self, seller_id):
        return self._sellers.get(seller_id)

    def get_category_translation(self, category_name):
        return category_name


def make_items(order_id, count):
    return [
        {
            "order_id": order_id,
            "order_item_id": i + 1,
            "product_id": f"product_{i}",
            "seller_id": f"seller_{i}",
        }
        for i in range(count)
    ]


class OrderProductAgentLimitsTest(unittest.TestCase):
    def test_affected_item_ids_capped_at_five(self):
        order_id = "order_with_many_items"
        items = make_items(order_id, 8)
        data = FakeDataAccess(items)
        agent = OrderProductAgent(llm_client=None, data_access=data)

        result = asyncio.run(agent.process({"order_id": order_id}))

        self.assertEqual(len(result["affected_item_ids"]), 5)
        self.assertEqual(
            result["affected_item_ids"],
            [f"{order_id}:{i}" for i in range(1, 6)],
        )
        # Raw items list and multi-item flag stay based on full data, not the cap.
        self.assertEqual(len(result["items"]), 8)
        self.assertTrue(result["is_multi_item"])

    def test_affected_item_ids_not_truncated_when_under_limit(self):
        order_id = "order_with_two_items"
        items = make_items(order_id, 2)
        data = FakeDataAccess(items)
        agent = OrderProductAgent(llm_client=None, data_access=data)

        result = asyncio.run(agent.process({"order_id": order_id}))

        self.assertEqual(
            result["affected_item_ids"],
            [f"{order_id}:1", f"{order_id}:2"],
        )


if __name__ == "__main__":
    unittest.main()
