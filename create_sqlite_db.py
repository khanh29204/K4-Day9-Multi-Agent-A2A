import os
import sqlite3
import pandas as pd
import time

DATA_DIR = r"d:\Vin_AI\K4-Day9-Multi-Agent-A2A\data"
DB_PATH = os.path.join(DATA_DIR, "olist_ecommerce.db")

CSV_TABLE_MAP = {
    "olist_orders_dataset.csv": ("orders", ["order_id", "customer_id"]),
    "olist_order_items_dataset.csv": ("order_items", ["order_id", "product_id", "seller_id"]),
    "olist_order_payments_dataset.csv": ("order_payments", ["order_id"]),
    "olist_order_reviews_dataset.csv": ("order_reviews", ["order_id"]),
    "olist_customers_dataset.csv": ("customers", ["customer_id", "customer_unique_id"]),
    "olist_products_dataset.csv": ("products", ["product_id", "product_category_name"]),
    "olist_sellers_dataset.csv": ("sellers", ["seller_id"]),
    "product_category_name_translation.csv": ("product_category_translation", ["product_category_name"]),
    "olist_geolocation_dataset.csv": ("geolocation", ["geolocation_zip_code_prefix"])
}

def main():
    print(f"Creating SQLite Database at {DB_PATH}...")
    start_time = time.time()
    
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    
    for csv_name, (table_name, indexes) in CSV_TABLE_MAP.items():
        csv_path = os.path.join(DATA_DIR, csv_name)
        if not os.path.exists(csv_path):
            print(f"Skipping {csv_name} (not found)")
            continue
            
        print(f"Loading {csv_name} -> Table '{table_name}'...")
        t0 = time.time()
        df = pd.read_csv(csv_path)
        
        # Write to SQLite
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        
        # Create Indexes
        for idx_col in indexes:
            idx_name = f"idx_{table_name}_{idx_col}"
            conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({idx_col});")
            
        print(f"  Done in {time.time() - t0:.2f}s ({len(df)} rows, {len(indexes)} indexes created)")
        
    conn.commit()
    conn.close()
    
    db_size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"\nSQLite DB created successfully in {time.time() - start_time:.2f}s!")
    print(f"Database Size: {db_size_mb:.2f} MB")

if __name__ == "__main__":
    main()
