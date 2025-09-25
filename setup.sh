#!/bin/bash

echo "Setting up FrameFinder..."

# Backend setup
echo "Setting up Django backend..."
cd backend

# Create media directory
mkdir -p media/videos

# Run migrations
echo "Running migrations..."
uv run python manage.py makemigrations
uv run python manage.py migrate

# Create superuser (optional)
echo "You can create a superuser with: cd backend && uv run python manage.py createsuperuser"

cd ..

# Frontend setup
echo "Setting up Next.js frontend..."
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    npm install
fi

cd ..

echo "Setup complete!"
echo ""
echo "To run the application:"
echo "1. Start the Django backend: cd backend && uv run python manage.py runserver"
echo "2. Start the Next.js frontend: cd frontend && npm run dev"
echo "3. Access the application at http://localhost:3000"
echo ""
echo "Don't forget to set your GOOGLE_API_KEY in the .env file!"