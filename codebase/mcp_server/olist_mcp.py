import os
import json
import pandas as pd
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

DEFAULT_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data'))
DATA_DIR = os.environ.get('DATA_DIR', DEFAULT_DATA_DIR)

# Cached DataFrames
_db = {}

def load_data():
    """Load CSV files from DATA_DIR into memory."""
    if _db:
        return
    files = {
        'orders': 'olist_orders_dataset.csv',
        'customers': 'olist_customers_dataset.csv',
        'order_items': 'olist_order_items_dataset.csv',
        'order_payments': 'olist_order_payments_dataset.csv',
        'order_reviews': 'olist_order_reviews_dataset.csv',
        'products': 'olist_products_dataset.csv',
        'sellers': 'olist_sellers_dataset.csv',
        'category_translation': 'product_category_name_translation.csv'
    }
    for key, filename in files.items():
        filepath = os.path.join(DATA_DIR, filename)
        if os.path.exists(filepath):
            try:
                _db[key] = pd.read_csv(filepath)
            except Exception:
                _db[key] = pd.DataFrame()
        else:
            _db[key] = pd.DataFrame()

@asynccontextmanager
async def lifespan(server: FastMCP):
    """Lifespan context manager for loading data on startup."""
    load_data()
    yield
    _db.clear()

# Initialize FastMCP server with stdio transport and lifespan
try:
    mcp = FastMCP("olist_mcp", lifespan=lifespan)
except TypeError:
    # Fallback if lifespan is not supported in this FastMCP version
    mcp = FastMCP("olist_mcp")
    load_data()

def get_df(name: str) -> pd.DataFrame:
    """Helper to safely get a DataFrame, loading if necessary."""
    if not _db:
        load_data()
    return _db.get(name, pd.DataFrame())

def serialize_df(df: pd.DataFrame) -> str:
    """Convert DataFrame to JSON string, gracefully handling empty cases."""
    if df is None or df.empty:
        return "[]"
    return df.to_json(orient="records")

class OrderIdQuery(BaseModel):
    order_id: str = Field(..., description="The unique identifier of the order")

class CustomerIdQuery(BaseModel):
    customer_id: str = Field(..., description="The unique identifier of the customer")

class CustomerUniqueIdQuery(BaseModel):
    customer_unique_id: str = Field(..., description="The unique identifier of the customer (unique ID)")

class ProductIdQuery(BaseModel):
    product_id: str = Field(..., description="The unique identifier of the product")

class SellerIdQuery(BaseModel):
    seller_id: str = Field(..., description="The unique identifier of the seller")

@mcp.tool()
def olist_get_order(query: OrderIdQuery) -> str:
    """Get order details by order_id. Returns order status, timestamps, etc."""
    df = get_df('orders')
    if df.empty or 'order_id' not in df.columns:
        return "[]"
    result = df[df['order_id'] == query.order_id]
    return serialize_df(result)

@mcp.tool()
def olist_get_order_items(query: OrderIdQuery) -> str:
    """Get all items for an order_id. Returns product_id, seller_id, price, freight_value, shipping_limit_date."""
    df = get_df('order_items')
    if df.empty or 'order_id' not in df.columns:
        return "[]"
    result = df[df['order_id'] == query.order_id]
    return serialize_df(result)

@mcp.tool()
def olist_get_order_payments(query: OrderIdQuery) -> str:
    """Get all payment rows for an order_id. Returns payment_sequential, payment_type, payment_installments, payment_value."""
    df = get_df('order_payments')
    if df.empty or 'order_id' not in df.columns:
        return "[]"
    result = df[df['order_id'] == query.order_id]
    return serialize_df(result)

@mcp.tool()
def olist_get_customer(query: CustomerIdQuery) -> str:
    """Get customer info by customer_id. Returns customer_unique_id, location."""
    df = get_df('customers')
    if df.empty or 'customer_id' not in df.columns:
        return "[]"
    result = df[df['customer_id'] == query.customer_id]
    return serialize_df(result)

@mcp.tool()
def olist_get_customer_orders(query: CustomerUniqueIdQuery) -> str:
    """Get all orders by customer_unique_id. Returns list of order_ids and statuses."""
    customers_df = get_df('customers')
    orders_df = get_df('orders')
    if customers_df.empty or orders_df.empty or 'customer_unique_id' not in customers_df.columns:
        return "[]"
    
    cust_ids = customers_df[customers_df['customer_unique_id'] == query.customer_unique_id]['customer_id']
    if cust_ids.empty:
        return "[]"
    
    result = orders_df[orders_df['customer_id'].isin(cust_ids)][['order_id', 'order_status']]
    return serialize_df(result)

@mcp.tool()
def olist_get_product(query: ProductIdQuery) -> str:
    """Get product info by product_id. Returns category name, dimensions."""
    df = get_df('products')
    if df.empty or 'product_id' not in df.columns:
        return "[]"
    result = df[df['product_id'] == query.product_id]
    return serialize_df(result)

@mcp.tool()
def olist_get_seller(query: SellerIdQuery) -> str:
    """Get seller info by seller_id. Returns location."""
    df = get_df('sellers')
    if df.empty or 'seller_id' not in df.columns:
        return "[]"
    result = df[df['seller_id'] == query.seller_id]
    return serialize_df(result)

@mcp.tool()
def olist_get_order_reviews(query: OrderIdQuery) -> str:
    """Get reviews for an order_id."""
    df = get_df('order_reviews')
    if df.empty or 'order_id' not in df.columns:
        return "[]"
    result = df[df['order_id'] == query.order_id]
    return serialize_df(result)

if __name__ == "__main__":
    mcp.run(transport="stdio")
