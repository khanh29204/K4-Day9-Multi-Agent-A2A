"""Data Access Layer - Direct CSV data access using pandas.

This module loads all Olist CSV files into memory and provides
query methods for each agent to use. This is the non-MCP alternative
for direct data access within the same process.
"""
import os
import pandas as pd
from typing import Dict, List, Optional, Any


class DataAccess:
    """Provides query methods over Olist CSV data."""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self._orders: Optional[pd.DataFrame] = None
        self._customers: Optional[pd.DataFrame] = None
        self._order_items: Optional[pd.DataFrame] = None
        self._payments: Optional[pd.DataFrame] = None
        self._reviews: Optional[pd.DataFrame] = None
        self._products: Optional[pd.DataFrame] = None
        self._sellers: Optional[pd.DataFrame] = None
        self._category_translation: Optional[pd.DataFrame] = None
    
    def load(self):
        """Load all CSV files into memory."""
        self._orders = pd.read_csv(os.path.join(self.data_dir, "olist_orders_dataset.csv"))
        self._customers = pd.read_csv(os.path.join(self.data_dir, "olist_customers_dataset.csv"))
        self._order_items = pd.read_csv(os.path.join(self.data_dir, "olist_order_items_dataset.csv"))
        self._payments = pd.read_csv(os.path.join(self.data_dir, "olist_order_payments_dataset.csv"))
        self._reviews = pd.read_csv(os.path.join(self.data_dir, "olist_order_reviews_dataset.csv"))
        self._products = pd.read_csv(os.path.join(self.data_dir, "olist_products_dataset.csv"))
        self._sellers = pd.read_csv(os.path.join(self.data_dir, "olist_sellers_dataset.csv"))
        self._category_translation = pd.read_csv(os.path.join(self.data_dir, "product_category_name_translation.csv"))
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order details by order_id."""
        row = self._orders[self._orders["order_id"] == order_id]
        if row.empty:
            return None
        return row.iloc[0].where(row.iloc[0].notna(), None).to_dict()
    
    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer details by customer_id."""
        row = self._customers[self._customers["customer_id"] == customer_id]
        if row.empty:
            return None
        return row.iloc[0].where(row.iloc[0].notna(), None).to_dict()
    
    def get_customer_orders(self, customer_unique_id: str) -> List[Dict[str, Any]]:
        """Get all orders for a customer_unique_id."""
        customer_ids = self._customers[
            self._customers["customer_unique_id"] == customer_unique_id
        ]["customer_id"].tolist()
        orders = self._orders[self._orders["customer_id"].isin(customer_ids)]
        return orders.where(orders.notna(), None).to_dict(orient="records")
    
    def get_order_items(self, order_id: str) -> List[Dict[str, Any]]:
        """Get all items for an order."""
        items = self._order_items[self._order_items["order_id"] == order_id]
        return items.where(items.notna(), None).to_dict(orient="records")
    
    def get_order_payments(self, order_id: str) -> List[Dict[str, Any]]:
        """Get all payment rows for an order."""
        payments = self._payments[self._payments["order_id"] == order_id]
        return payments.where(payments.notna(), None).to_dict(orient="records")
    
    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details by product_id."""
        row = self._products[self._products["product_id"] == product_id]
        if row.empty:
            return None
        return row.iloc[0].where(row.iloc[0].notna(), None).to_dict()
    
    def get_seller(self, seller_id: str) -> Optional[Dict[str, Any]]:
        """Get seller details by seller_id."""
        row = self._sellers[self._sellers["seller_id"] == seller_id]
        if row.empty:
            return None
        return row.iloc[0].where(row.iloc[0].notna(), None).to_dict()
    
    def get_order_reviews(self, order_id: str) -> List[Dict[str, Any]]:
        """Get reviews for an order."""
        reviews = self._reviews[self._reviews["order_id"] == order_id]
        return reviews.where(reviews.notna(), None).to_dict(orient="records")
    
    def get_category_translation(self, category_name: str) -> Optional[str]:
        """Get English translation for a category name."""
        if not category_name or pd.isna(category_name):
            return None
        row = self._category_translation[
            self._category_translation["product_category_name"] == category_name
        ]
        if row.empty:
            return category_name  # Return original if no translation
        return row.iloc[0]["product_category_name_english"]
