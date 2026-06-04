import sqlite3
import pandas as pd
import logging

# ---------------- LOGGING SETUP ----------------
logging.basicConfig(
    filename="logs/get_vendor_summary.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)

# ---------------- CREATE SUMMARY ----------------
def create_vendor_summary(conn):
    query = """
    WITH FreightSummary AS (
        SELECT 
            VendorNumber,
            SUM(Freight) AS FreightCost
        FROM vendor_invoice
        GROUP BY VendorNumber
    ),

    PurchaseSummary AS (
        SELECT
            p.VendorNumber,
            p.VendorName,
            p.Brand,
            p.Description,
            p.PurchasePrice,
            pp.Price AS ActualPrice,
            pp.Volume,
            SUM(p.Quantity) AS TotalPurchaseQuantity,
            SUM(p.Dollars) AS TotalPurchaseDollars
        FROM purchases p
        JOIN purchase_prices pp
            ON p.Brand = pp.Brand
        WHERE p.PurchasePrice > 0
        GROUP BY 
            p.VendorNumber, p.VendorName, p.Brand, 
            p.Description, p.PurchasePrice, 
            pp.Price, pp.Volume
    ),

    SalesSummary AS (
        SELECT
            VendorNo,
            Brand,
            SUM(SalesQuantity) AS TotalSalesQuantity,
            SUM(SalesDollars) AS TotalSalesDollars,
            SUM(SalesPrice) AS TotalSalesPrice,
            SUM(ExciseTax) AS TotalExciseTax
        FROM sales
        GROUP BY VendorNo, Brand
    )

    SELECT
        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice,
        ps.ActualPrice,
        ps.Volume,
        ps.TotalPurchaseQuantity,
        ps.TotalPurchaseDollars,
        ss.TotalSalesQuantity,
        ss.TotalSalesDollars,
        ss.TotalSalesPrice,
        ss.TotalExciseTax,
        fs.FreightCost
    FROM PurchaseSummary ps
    LEFT JOIN SalesSummary ss
        ON ps.VendorNumber = ss.VendorNo
        AND ps.Brand = ss.Brand
    LEFT JOIN FreightSummary fs
        ON ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.TotalPurchaseDollars DESC
    """

    df = pd.read_sql_query(query, conn)
    return df


# ---------------- CLEAN DATA ----------------
def clean_data(df):
    df['Volume'] = df['Volume'].astype(float)
    df.fillna(0, inplace=True)

    df['VendorName'] = df['VendorName'].str.strip()
    df['Description'] = df['Description'].str.strip()

    # New columns
    df['GrossProfit'] = df['TotalSalesDollars'] - df['TotalPurchaseDollars']
    df['ProfitMargin'] = (df['GrossProfit'] / df['TotalSalesDollars']) * 100
    df['StockTurnover'] = df['TotalSalesQuantity'] / df['TotalPurchaseQuantity']
    df['SalesToPurchaseRatio'] = df['TotalSalesDollars'] / df['TotalPurchaseDollars']

    return df


# ---------------- FAST INSERT ----------------
def ingest_db(df, table_name, conn):
    df.to_sql(
        table_name,
        conn,
        if_exists='replace',
        index=False,
        chunksize=10000,   # 🔥 improves speed
        method='multi'     # 🔥 batch insert
    )


# ---------------- MAIN ----------------
if __name__ == '__main__':
    conn = sqlite3.connect('inventory.db')

    try:
        logging.info('Creating Vendor Summary Table...')
        summary_df = create_vendor_summary(conn)
        logging.info(f"Summary shape: {summary_df.shape}")

        logging.info('Cleaning Data...')
        clean_df = clean_data(summary_df)
        logging.info(f"Cleaned shape: {clean_df.shape}")

        logging.info('Ingesting data...')
        ingest_db(clean_df, 'vendor_sales_summary', conn)

        logging.info('✅ Data successfully inserted!')

    finally:
        conn.close()   # 🔥 prevents database lock