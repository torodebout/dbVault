#!/bin/bash
set -e


CONTAINER_NAME="dbvault-postgres-test"
DB_NAME="testdb"
DB_USER="testuser"
DB_PASS="testpass123"
DB_PORT="5432"

echo "🐘 Setting up PostgreSQL test container..."

if docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping and removing existing container..."
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
fi

echo "Starting PostgreSQL container..."
docker run -d \
    --name $CONTAINER_NAME \
    -e POSTGRES_DB=$DB_NAME \
    -e POSTGRES_USER=$DB_USER \
    -e POSTGRES_PASSWORD=$DB_PASS \
    -p $DB_PORT:5432 \
    --health-cmd="pg_isready -U $DB_USER -d $DB_NAME" \
    --health-interval=10s \
    --health-timeout=5s \
    --health-retries=5 \
    postgres:15-alpine

echo "Waiting for PostgreSQL to be ready..."
timeout=60
while [ $timeout -gt 0 ]; do
    if docker exec $CONTAINER_NAME pg_isready -U $DB_USER -d $DB_NAME 2>/dev/null; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    echo "❌ PostgreSQL failed to start within 60 seconds"
    exit 1
fi

echo "Creating test tables and data..."
docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME << 'EOF'
-- Drop tables if they exist
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS products CASCADE;

-- Create customers table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(50),
    stock_quantity INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending'
);

-- Insert test customers
INSERT INTO customers (name, email, phone, address) VALUES
('John Doe', 'john.doe@example.com', '+1-555-0101', '123 Main St, Anytown, USA'),
('Jane Smith', 'jane.smith@example.com', '+1-555-0102', '456 Oak Ave, Somewhere, USA'),
('Bob Johnson', 'bob.johnson@example.com', '+1-555-0103', '789 Pine Rd, Elsewhere, USA'),
('Alice Brown', 'alice.brown@example.com', '+1-555-0104', '321 Elm St, Nowhere, USA'),
('Charlie Davis', 'charlie.davis@example.com', '+1-555-0105', '654 Maple Dr, Anywhere, USA'),
('Diana Wilson', 'diana.wilson@example.com', '+1-555-0106', '987 Cedar Ln, Someplace, USA'),
('Eve Miller', 'eve.miller@example.com', '+1-555-0107', '147 Birch Way, Othertown, USA'),
('Frank Garcia', 'frank.garcia@example.com', '+1-555-0108', '258 Spruce St, Newplace, USA'),
('Grace Lee', 'grace.lee@example.com', '+1-555-0109', '369 Willow Ave, Oldtown, USA'),
('Henry Wang', 'henry.wang@example.com', '+1-555-0110', '741 Ash Rd, Nextplace, USA');

-- Insert test products
INSERT INTO products (name, description, price, category, stock_quantity) VALUES
('Laptop Computer', 'High-performance laptop for professionals', 1299.99, 'Electronics', 25),
('Wireless Mouse', 'Ergonomic wireless mouse with long battery life', 29.99, 'Electronics', 150),
('Office Chair', 'Comfortable ergonomic office chair', 249.99, 'Furniture', 45),
('Desk Lamp', 'LED desk lamp with adjustable brightness', 89.99, 'Furniture', 75),
('Coffee Mug', 'Ceramic coffee mug with company logo', 12.99, 'Accessories', 200),
('Notebook Set', 'Set of 3 premium notebooks', 24.99, 'Stationery', 100),
('Pen Pack', 'Pack of 10 ballpoint pens', 8.99, 'Stationery', 300),
('Monitor Stand', 'Adjustable monitor stand with storage', 59.99, 'Electronics', 60),
('Keyboard', 'Mechanical keyboard with RGB lighting', 149.99, 'Electronics', 40),
('Webcam', 'HD webcam for video conferencing', 79.99, 'Electronics', 85);

-- Insert test orders
INSERT INTO orders (customer_id, product_id, quantity, unit_price, status) VALUES
(1, 1, 1, 1299.99, 'completed'),
(1, 2, 2, 29.99, 'completed'),
(2, 3, 1, 249.99, 'pending'),
(3, 4, 1, 89.99, 'shipped'),
(3, 5, 3, 12.99, 'completed'),
(4, 6, 2, 24.99, 'completed'),
(5, 7, 5, 8.99, 'pending'),
(6, 8, 1, 59.99, 'shipped'),
(7, 9, 1, 149.99, 'completed'),
(8, 10, 1, 79.99, 'pending'),
(9, 1, 1, 1299.99, 'shipped'),
(10, 2, 1, 29.99, 'completed'),
(1, 5, 2, 12.99, 'completed'),
(2, 7, 3, 8.99, 'pending'),
(4, 9, 1, 149.99, 'shipped');

-- Create indexes for better performance
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_product_id ON orders(product_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_products_category ON products(category);

-- Display summary
SELECT 
    'Customers' as table_name, 
    COUNT(*) as record_count 
FROM customers
UNION ALL
SELECT 
    'Products' as table_name, 
    COUNT(*) as record_count 
FROM products
UNION ALL
SELECT 
    'Orders' as table_name, 
    COUNT(*) as record_count 
FROM orders;

EOF

echo "✅ PostgreSQL test container setup complete!"
echo ""
echo "📊 Container Details:"
echo "   Name: $CONTAINER_NAME"
echo "   Database: $DB_NAME"
echo "   Username: $DB_USER"
echo "   Password: $DB_PASS"
echo "   Port: $DB_PORT"
echo ""
echo "🔗 Connection string: postgresql://$DB_USER:$DB_PASS@localhost:$DB_PORT/$DB_NAME"
echo ""
echo "💡 Test the connection:"
echo "   dbvault test --config config/postgres.yaml"
