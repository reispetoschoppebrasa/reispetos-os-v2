services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: reispetos
      POSTGRES_USER: reispetos
      POSTGRES_PASSWORD: reispetos123
    volumes: [postgres_data:/var/lib/postgresql/data]
  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+psycopg2://reispetos:reispetos123@db:5432/reispetos
      SECRET_KEY: altere-esta-chave
      FRONTEND_URL: http://localhost:3000
    depends_on: [db]
    ports: ["8000:8000"]
  frontend:
    build:
      context: ./frontend
      args:
        VITE_API_URL: http://localhost:8000
    depends_on: [backend]
    ports: ["3000:80"]
volumes:
  postgres_data:
