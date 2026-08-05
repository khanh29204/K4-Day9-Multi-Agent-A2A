"""
DB Helper Tools for Multi-Agent Systems on Olist E-commerce Dataset.
Provides fast, indexed SQL queries to feed clean context to LLMs / Subagents.
"""

import os
import sqlite3
from typing import Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "olist_ecommerce.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_order(order_id: str) -> Dict[str, Any]:
    """Retrieve order status and delivery timestamps for a given order_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        return dict(row) if row else {}

def get_order_items(order_id: str) -> List[Dict[str, Any]]:
    """Retrieve items, prices, freight, and shipping limits for an order."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, p.product_category_name, t.product_category_name_english
            FROM order_items i
            LEFT JOIN products p ON i.product_id = p.product_id
            LEFT JOIN product_category_translation t ON p.product_category_name = t.product_category_name
            WHERE i.order_id = ?
            ORDER BY i.order_item_id ASC
        """, (order_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_order_payments(order_id: str) -> List[Dict[str, Any]]:
    """Retrieve payment rows, sequential IDs, payment types, and values for an order."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM order_payments WHERE order_id = ? ORDER BY payment_sequential ASC", (order_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_customer_context(customer_id: str, claimed_order_id: str) -> Dict[str, Any]:
    """Retrieve customer_unique_id and historical related order_ids."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Find unique customer id
        cursor.execute("SELECT customer_unique_id FROM customers WHERE customer_id = ?", (customer_id,))
        c_row = cursor.fetchone()
        if not c_row:
            return {"customer_unique_id": None, "related_order_ids": []}
            
        unique_id = c_row["customer_unique_id"]
        
        # Find other orders by this customer
        cursor.execute("""
            SELECT o.order_id 
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE c.customer_unique_id = ? AND o.order_id != ?
            LIMIT 5
        """, (unique_id, claimed_order_id))
        
        related_ids = [row["order_id"] for row in cursor.fetchall()]
        return {
            "customer_unique_id": unique_id,
            "related_order_ids": related_ids
        }

def get_full_case_context(claimed_order_id: str) -> Dict[str, Any]:
    """
    Convenience method: Fetches complete consolidated database records for a case
    in < 5ms for Agents to consume instantly without multi-round SQL calls.
    """
    order = get_order(claimed_order_id)
    if not order:
        return {"error": f"Order {claimed_order_id} not found."}
        
    items = get_order_items(claimed_order_id)
    payments = get_order_payments(claimed_order_id)
    customer = get_customer_context(order["customer_id"], claimed_order_id)
    
    return {
        "order": order,
        "items": items,
        "payments": payments,
        "customer": customer
    }

if __name__ == "__main__":
    # Test lookup speed
    import time
    t0 = time.time()
    res = get_full_case_context("9b75cdaf2d85857ef023980e15d01546")
    print(f"Fetched full case context in {(time.time() - t0)*1000:.2f} ms")
    print("Order status:", res["order"].get("order_status"))
    print("Items count:", len(res["items"]))
    print("Payments count:", len(res["payments"]))
