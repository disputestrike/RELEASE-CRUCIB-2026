---
name: data-dashboard-builder
description: Build data analytics dashboards with interactive charts, KPI cards, filters, date range pickers, and data table views. Use when the user wants to visualize data, build a reporting dashboard, create analytics views, or display metrics with charts. Triggers on phrases like "build a dashboard", "create analytics charts", "I need to visualize my data", "build a reporting tool", "create a metrics dashboard".
metadata:
  version: '1.0'
  category: build
  icon: 📊
  color: '#6366f1'
---

# Data Dashboard Builder

## When to Use This Skill

Apply this skill when the user wants to visualize and explore data:

- "Build a dashboard to track my metrics"
- "Create an analytics report for X"
- "I need charts showing my sales/usage/performance data"
- "Build a reporting tool with filters and date ranges"
- "Create a real-time monitoring dashboard"
- Any request for data visualization, charts, KPIs, or analytics

## What This Skill Builds

A production-ready data dashboard:

**Layout**
- Sidebar navigation with dashboard sections
- Sticky header with date range picker and filter controls
- KPI card row (metric, trend arrow, % change vs previous period)
- Chart section (line, bar, area, pie/donut)
- Data table with sort and export

**Chart Types (recharts)**
- Line chart — trend over time
- Bar chart — comparison across categories
- Area chart — cumulative metrics
- Pie/donut chart — distribution breakdown
- Composed chart — multiple metrics on one axis
- Scatter plot — correlation analysis

**KPI Cards**
- Primary metric (large number)
- Trend indicator (↑↓ with % change, colored green/red)
- Comparison label ("vs last 30 days")
- Mini sparkline chart
- Click to drill down

**Filters & Controls**
- Date range picker (7d, 30d, 90d, 1y, custom)
- Category/segment filter (multi-select)
- Comparison toggle (compare to previous period)
- Granularity selector (daily/weekly/monthly)
- Export button (CSV/PNG)

**Data Sources**
- Mock data with realistic distributions for preview
- API integration pattern (fetches from backend on filter change)
- CSV upload for custom data exploration
- Refresh interval for near-real-time updates

**Advanced Features**
- Drill-down (click chart segment → see detail table)
- Cohort analysis table
- Funnel visualization
- Heatmap (7-day × 24-hour activity)
- Anomaly highlighting (mark unusual spikes)

## Instructions

1. **Define the metrics** — what data is being tracked, what questions the user needs answered, what decisions the dashboard supports

2. **Design the layout** — which metrics are primary KPIs (top row), which are secondary charts, which need drill-down

3. **Generate realistic mock data** — create data that demonstrates the dashboard properly (30-90 days of daily data, realistic distributions, seasonal patterns)

4. **Build in 3 passes**:
   - Pass 1: Config + data model + mock data generator + filter state management
   - Pass 2: KPI cards + primary charts with responsive containers
   - Pass 3: Data table + drill-down + export + filters wired to all charts

5. **Chart quality rules**:
   - Always use `ResponsiveContainer` with 100% width
   - Custom tooltip with formatted numbers (currency, percentages)
   - Proper axis labels with units
   - Legend only when needed (2+ series)
   - Color palette: consistent across all charts (use CSS variables)

6. **Performance rules**:
   - Memoize chart data calculations with `useMemo`
   - Debounce filter changes (300ms)
   - Show loading skeleton during data fetch
   - Paginate tables over 100 rows

## Example Input → Output

Input: "Build a sales analytics dashboard showing monthly revenue, top products, conversion funnel, and customer cohort retention"

Output includes:
- KPI row: Total Revenue, New Customers, Avg Order Value, Conversion Rate (each with trend)
- Line chart: Monthly revenue + target line
- Bar chart: Top 10 products by revenue
- Funnel chart: Visit → Add to Cart → Checkout → Purchase
- Cohort table: 6-month retention heatmap
- Data table: Order-level data with search + CSV export
- `/src/data/mockData.ts` — realistic 12-month sales data
- `/src/components/charts/` — RevenueChart, ProductsChart, FunnelChart, CohortTable
