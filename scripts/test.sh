# !/bin/bash     
set -e

echo "Ejecutando pruebas..."

curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"customer": "Berny", "items": [{"sku": "A1", "qty": 2}]}'


curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "inigo@iberopuebla.mx","password": "123", "name": "Inigo"}'


curl -X POST http://localhost:8000/bookings \
  -H "Content-Type: application/json" \
  -d '{"guest": "Pingul Barranco","room_type": "double","check_in": "2026-05-01","check_out": "2026-05-05"}'


echo "Pruebas terminadas exitosamente! (‾◡◝)"