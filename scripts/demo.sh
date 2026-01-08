#!/usr/bin/env bash

set -e

echo "🚀 Starting SunnyBest Retail Intelligence Platform..."
echo ""

# Start Docker Compose
docker compose up -d --build

echo ""
echo "⏳ Waiting for services to start..."
sleep 5

API_URL="http://localhost:8000"
DASHBOARD_URL="http://localhost:8501"

echo ""
echo "✅ Services are running:"
echo "📊 Dashboard: $DASHBOARD_URL"
echo "📘 API Docs:  $API_URL/docs"
echo ""

echo "🔎 Checking API health..."
curl -s $API_URL/health | jq .
echo ""

echo "📈 Running sample prediction..."
curl -s -X POST "$API_URL/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "store_id": 1,
    "product_category": "Mobile Phones",
    "price": 799,
    "promotion": true,
    "stock_level": 120
  }' | jq .

echo ""
echo "🎉 Demo complete. Open the dashboard to explore!"