#!/bin/bash

echo "Starting FrameFinder..."

# Check if GOOGLE_API_KEY is set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "WARNING: GOOGLE_API_KEY is not set in .env file"
    echo "Please add your Google API key to the .env file"
fi

# Start Django backend in background
echo "Starting Django backend..."
cd backend
uv run python manage.py runserver &
DJANGO_PID=$!

sleep 2

# Start Next.js frontend
echo "Starting Next.js frontend..."
cd ../frontend
npm run dev &
NEXT_PID=$!

echo ""
echo "FrameFinder is running!"
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait and handle shutdown
trap "echo 'Shutting down...'; kill $DJANGO_PID $NEXT_PID; exit" SIGINT SIGTERM

wait