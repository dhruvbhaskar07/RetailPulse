# RetailPulse — Power BI Dashboards

> [Power BI Dashboards Source Document](../source/RetailPulse%20PowerBI%20Dashboards%20(1).txt)

## Data Source

The primary dataset is **Online Retail II** (UCI Machine Learning Repository), transformed via `src/data/adapters/online_retail_ii.py` into the following tables:

| Table | Rows | Key Columns |
|-------|------|-------------|
| `sales.csv` | 779,119 | transaction_id, customer_id, product_id, store_id (country), quantity, price, total_amount, invoice_date |
| `customers.csv` | 5,931 | customer_id, country (store_id), total_spend, purchase_count, first_purchase, last_purchase |
| `products.csv` | 5,311 | product_id, description, unit_price, total_sold |
| `stores.csv` | 41 | store_id (country name), total_sales, transaction_count |
| `holidays.csv` | 12 | date, country, holiday_name |
| `inventory.csv` | ~2.87M (weekly snapshots) | product_id, store_id, week_start, stock_level, reorder_point |

Derived tables (from notebook execution in `data/processed/`):
- `rfm_segments.csv` — 314,581 customer RFM scores & segments
- `forecast_results.csv` — 26,747 demand forecast rows
- `ensemble_forecast_results.csv` — 22,742 ensemble forecasts
- `churn_scores.csv` — 705,036 churn probabilities
- `churn_importance.csv` — feature importance
- `inventory_recommendations.csv` — 36,424 reorder suggestions
- `product_demand.csv` — 278,622 demand signals
- `segment_profiles.csv` — 304 segment descriptions

---

## Setup in Power BI Desktop

### Step 1: Load Data

1. Open Power BI Desktop → **Get Data** → **Text/CSV**
2. Point to `data/processed/sales.csv` (or any derived CSV above)
3. Repeat for each CSV you need, or use **Folder** connector to load all CSVs at once
4. All other data sources can similarly be imported from `data/processed/`

### Step 2: Data Cleaning

- Ensure `invoice_date` is typed as **Date** (not DateTime if only date is needed)
- Ensure `quantity`, `price`, `total_amount` are typed as **Decimal**
- Remove rows where `quantity <= 0` or `price <= 0` (cancel/return entries)
- Set `customer_id` as text (some IDs start with non-numeric characters)

### Step 3: Create Calendar/Date Table (DAX)

```dax
Calendar = 
ADDCOLUMNS(
    CALENDAR(MIN(sales[invoice_date]), MAX(sales[invoice_date])),
    "Year", YEAR([Date]),
    "Month", FORMAT([Date], "MMMM"),
    "MonthNo", MONTH([Date]),
    "Quarter", "Q" & QUARTER([Date]),
    "WeekDay", WEEKDAY([Date], 2),
    "DayName", FORMAT([Date], "dddd")
)
```

Relate `Calendar[Date]` → `sales[invoice_date]` (many-to-one, single direction).

### Step 4: Key DAX Measures

```dax
Total Revenue = SUM(sales[total_amount])
Total Transactions = COUNTROWS(sales)
Total Customers = DISTINCTCOUNT(sales[customer_id])
Total Products = DISTINCTCOUNT(sales[product_id])

Avg Transaction Value = DIVIDE([Total Revenue], [Total Transactions])

Revenue per Customer = DIVIDE([Total Revenue], [Total Customers])

Month-over-Month Revenue % = 
VAR CurrentMonth = SUM(sales[total_amount])
VAR PrevMonth = 
    CALCULATE(
        SUM(sales[total_amount]),
        PREVIOUSMONTH('Calendar'[Date])
    )
RETURN
    DIVIDE(CurrentMonth - PrevMonth, PrevMonth)

Active Customers (Last 90d) = 
CALCULATE(
    DISTINCTCOUNT(sales[customer_id]),
    DATESINPERIOD('Calendar'[Date], MAX('Calendar'[Date]), -90, DAY)
)

Churn Rate = 
VAR TotalCust = [Total Customers]
VAR LostCust = 
    CALCULATE(
        DISTINCTCOUNT(sales[customer_id]),
        sales[last_purchase] < MAX('Calendar'[Date]) - 180
    )
RETURN DIVIDE(LostCust, TotalCust)

Repeat Purchase Rate = 
VAR Buyers = [Total Customers]
VAR Repeat = 
    COUNTROWS(
        FILTER(
            VALUES(sales[customer_id]),
            CALCULATE(COUNTROWS(sales)) > 1
        )
    )
RETURN DIVIDE(Repeat, Buyers)

Forecast Accuracy (MAPE) = 
VAR Forecast = SUM(forecast_results[yhat])
VAR Actual = SUM(forecast_results[y])
RETURN
    DIVIDE(SUMX(forecast_results, ABS(forecast_results[y] - forecast_results[yhat])), Actual)
```

---

## Dashboard Pages (12)

### Page 1: Executive Summary
- **KPI Cards**: Total Revenue, Total Transactions, Active Customers, Churn Rate
- **Line Chart**: Revenue trend (monthly) with forecast overlay
- **Top 10 Products** by revenue (horizontal bar)
- **Map**: Revenue by country/store
- **Gauges**: Forecast accuracy (MAPE), Repeat Purchase Rate

### Page 2: Sales Trend Analysis
- **Multi-line**: Daily/Weekly/Monthly revenue & transaction volume
- **Area Chart**: Cumulative revenue YTD
- **Small Multiples**: Revenue by weekday/hour heatmap (if time available)
- **Trend Line**: Moving average (7-day / 30-day)

### Page 3: Product Performance
- **Matrix**: Product categories → revenue, quantity, margin
- **Top/Bottom N**: Best & worst sellers (dynamic slicer)
- **Decomposition Tree**: Revenue breakdown by category → product
- **Waterfall**: Revenue drivers (top products contributing to change)

### Page 4: Customer Analytics
- **RFM Segmentation** bar chart (segments vs. count)
- **Donut chart**: % of customers in each RFM tier (Bronze/Silver/Gold/Platinum)
- **Scatter**: Recency vs. Frequency (bubble = Monetary)
- **Clustered bar**: Avg order value by segment
- **Line**: Customer acquisition trend (new customers per month)

### Page 5: Region / Country Sales
- **Filled Map**: Revenue by country
- **Stacked bar**: Top 10 countries by revenue & transactions
- **Treemap**: Country → product category revenue breakdown
- **Ribbon chart**: Country rank over time

### Page 6: Monthly & Seasonal Sales
- **Line chart**: Monthly revenue comparison (year-over-year)
- **Heatmap**: Weekday × Month → total revenue
- **Box plot**: Revenue distribution by month
- **Slicer**: Month, Quarter, Year

### Page 7: Customer Behaviour
- **Cohort Analysis table**: Customer retention by acquisition month
- **Histogram**: Purchase frequency distribution
- **Funnel**: Browse → Add-to-cart → Purchase → Repeat
- **Sankey**: Customer journey between product categories

### Page 8: Profit & Revenue Analysis
- **Waterfall**: Monthly revenue change breakdown
- **Combo chart**: Revenue vs. profit margin %
- **Scatter**: Revenue vs. transaction count per customer
- **KPIs**: YoY growth %, Avg Revenue Per User (ARPU)

### Page 9: Inventory Risk
- **Bar + Line**: Stock levels by product category vs. reorder point
- **Conditional formatting**: Red/Yellow/Green for stock-out risk
- **Table**: Products below reorder point with supplier info
- **Gauge**: Overall inventory health score

### Page 10: Orders & Transactions
- **Line chart**: Daily order volume
- **Pie**: Payment method / order channel distribution
- **Table**: Top transactions (with drill-through to detail)
- **Q&A visual**: "Show orders where quantity > 50"

### Page 11: Advanced Analytics
- **Key Influencers**: What drives high-value transactions?
- **Decomposition Tree**: Revenue breakdown by any hierarchy
- **Scatter**: Price elasticity (price vs. quantity sold)
- **AI visuals**: Anomaly detection on daily revenue

### Page 12: Interactive Filters
- **Slicers**: Year, Quarter, Month, Country, Product Category, Customer Segment, Date Range
- **Sync slicers** across all pages for cross-filtering
- **Bookmarks**: Toggle between light/dark theme
- **Reset button**: Clear all filters bookmark

---

## Publishing & Sharing

1. **Publish** to Power BI Service (workspace: RetailPulse)
2. Set up **scheduled refresh** (Daily) pointing to CSV files on OneDrive/SharePoint or your data source
3. Create **Apps** for stakeholder distribution
4. Enable **Row-Level Security (RLS)** if needed (e.g., store manager sees only their country)
5. Pin KPIs to **dashboard tiles** and set **data alerts** (e.g., "Revenue drops below threshold")

---

## Connecting to the Streamlit Dashboard

The Power BI reports complement the Streamlit dashboard by providing:

- **Self-service analytics** (drag & drop exploration)
- **Mobile-optimized** Power BI app access
- **Email subscriptions** for scheduled report delivery
- **Natural language Q&A** for ad-hoc queries

Both tools read from the same processed data in `data/processed/`, guaranteeing consistency.
