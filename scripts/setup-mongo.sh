#!/bin/bash
set -e


CONTAINER_NAME="dbvault-mongo-test"
DB_NAME="testdb"
DB_PORT="27017"

echo "🍃 Setting up MongoDB test container..."

if docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping and removing existing container..."
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
fi

echo "Starting MongoDB container..."
docker run -d \
    --name $CONTAINER_NAME \
    -p $DB_PORT:27017 \
    --health-cmd="mongosh --eval 'db.runCommand({ping: 1})'" \
    --health-interval=10s \
    --health-timeout=5s \
    --health-retries=5 \
    mongo:latest

echo "Waiting for MongoDB to be ready..."
timeout=60
while [ $timeout -gt 0 ]; do
    if docker exec $CONTAINER_NAME mongosh --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
        echo "✅ MongoDB is ready!"
        break
    fi
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    echo "❌ MongoDB failed to start within 60 seconds"
    exit 1
fi

echo "Creating test collections and data..."
docker exec -i $CONTAINER_NAME mongosh $DB_NAME << 'EOF'
// Drop collections if they exist
db.customers.drop();
db.products.drop();
db.orders.drop();

// Create customers collection with sample data
db.customers.insertMany([
    {
        _id: ObjectId(),
        name: "John Doe",
        email: "john.doe@example.com",
        phone: "+1-555-0101",
        address: {
            street: "123 Main St",
            city: "Anytown",
            state: "CA",
            zipCode: "12345",
            country: "USA"
        },
        preferences: {
            newsletter: true,
            notifications: true,
            language: "en"
        },
        tags: ["premium", "loyal"],
        joinDate: new Date("2023-01-15"),
        lastLogin: new Date(),
        isActive: true
    },
    {
        _id: ObjectId(),
        name: "Jane Smith",
        email: "jane.smith@example.com",
        phone: "+1-555-0102",
        address: {
            street: "456 Oak Ave",
            city: "Somewhere",
            state: "NY",
            zipCode: "67890",
            country: "USA"
        },
        preferences: {
            newsletter: false,
            notifications: true,
            language: "en"
        },
        tags: ["new", "prospect"],
        joinDate: new Date("2024-03-20"),
        lastLogin: new Date(),
        isActive: true
    },
    {
        _id: ObjectId(),
        name: "Bob Johnson",
        email: "bob.johnson@example.com",
        phone: "+1-555-0103",
        address: {
            street: "789 Pine Rd",
            city: "Elsewhere",
            state: "TX",
            zipCode: "54321",
            country: "USA"
        },
        preferences: {
            newsletter: true,
            notifications: false,
            language: "en"
        },
        tags: ["enterprise", "bulk"],
        joinDate: new Date("2022-11-08"),
        lastLogin: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // 7 days ago
        isActive: true
    },
    {
        _id: ObjectId(),
        name: "Alice Brown",
        email: "alice.brown@example.com",
        phone: "+1-555-0104",
        address: {
            street: "321 Elm St",
            city: "Nowhere",
            state: "FL",
            zipCode: "98765",
            country: "USA"
        },
        preferences: {
            newsletter: true,
            notifications: true,
            language: "es"
        },
        tags: ["vip", "international"],
        joinDate: new Date("2023-07-12"),
        lastLogin: new Date(),
        isActive: false
    },
    {
        _id: ObjectId(),
        name: "Charlie Davis",
        email: "charlie.davis@example.com",
        phone: "+1-555-0105",
        address: {
            street: "654 Maple Dr",
            city: "Anywhere",
            state: "WA",
            zipCode: "13579",
            country: "USA"
        },
        preferences: {
            newsletter: false,
            notifications: false,
            language: "en"
        },
        tags: ["trial", "evaluation"],
        joinDate: new Date("2024-06-01"),
        lastLogin: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
        isActive: true
    }
]);

// Create products collection with sample data
db.products.insertMany([
    {
        _id: ObjectId(),
        name: "Premium Laptop",
        description: "High-performance laptop for professionals",
        price: 1299.99,
        category: "Electronics",
        subcategory: "Computers",
        brand: "TechCorp",
        model: "ProBook 2024",
        specifications: {
            processor: "Intel i7-12700H",
            memory: "16GB DDR4",
            storage: "512GB NVMe SSD",
            display: "15.6\" 4K IPS",
            graphics: "NVIDIA RTX 3060",
            weight: "2.1kg"
        },
        inventory: {
            stock: 25,
            reserved: 3,
            available: 22,
            warehouse: "West Coast"
        },
        ratings: {
            average: 4.7,
            count: 89,
            breakdown: { 5: 67, 4: 15, 3: 5, 2: 1, 1: 1 }
        },
        tags: ["professional", "gaming", "portable"],
        isActive: true,
        featured: true,
        createdAt: new Date("2024-01-01"),
        updatedAt: new Date()
    },
    {
        _id: ObjectId(),
        name: "Wireless Ergonomic Mouse",
        description: "Comfortable wireless mouse with long battery life",
        price: 29.99,
        category: "Electronics",
        subcategory: "Accessories",
        brand: "ErgoTech",
        model: "ComfortGrip Pro",
        specifications: {
            connection: "Wireless 2.4GHz",
            battery: "AA x2 (included)",
            batteryLife: "18 months",
            dpi: "800-3200 adjustable",
            buttons: 6,
            weight: "120g"
        },
        inventory: {
            stock: 150,
            reserved: 12,
            available: 138,
            warehouse: "East Coast"
        },
        ratings: {
            average: 4.3,
            count: 234,
            breakdown: { 5: 145, 4: 67, 3: 18, 2: 3, 1: 1 }
        },
        tags: ["wireless", "ergonomic", "office"],
        isActive: true,
        featured: false,
        createdAt: new Date("2023-08-15"),
        updatedAt: new Date()
    },
    {
        _id: ObjectId(),
        name: "Smart Coffee Maker",
        description: "WiFi-enabled coffee maker with app control",
        price: 199.99,
        category: "Appliances",
        subcategory: "Kitchen",
        brand: "BrewMaster",
        model: "Smart Brew 3000",
        specifications: {
            capacity: "12 cups",
            connectivity: "WiFi 2.4GHz",
            features: ["Programmable", "Auto-shutoff", "Keep warm"],
            dimensions: "14\" x 10\" x 12\"",
            weight: "4.2kg",
            power: "1200W"
        },
        inventory: {
            stock: 45,
            reserved: 8,
            available: 37,
            warehouse: "Central"
        },
        ratings: {
            average: 4.1,
            count: 156,
            breakdown: { 5: 89, 4: 45, 3: 15, 2: 5, 1: 2 }
        },
        tags: ["smart", "wifi", "kitchen", "coffee"],
        isActive: true,
        featured: true,
        createdAt: new Date("2023-12-01"),
        updatedAt: new Date()
    }
]);

// Create orders collection with sample data
const customers = db.customers.find().toArray();
const products = db.products.find().toArray();

db.orders.insertMany([
    {
        _id: ObjectId(),
        orderNumber: "ORD-2024-001",
        customerId: customers[0]._id,
        customerEmail: customers[0].email,
        items: [
            {
                productId: products[0]._id,
                productName: products[0].name,
                quantity: 1,
                unitPrice: products[0].price,
                totalPrice: products[0].price
            },
            {
                productId: products[1]._id,
                productName: products[1].name,
                quantity: 2,
                unitPrice: products[1].price,
                totalPrice: products[1].price * 2
            }
        ],
        subtotal: products[0].price + (products[1].price * 2),
        tax: (products[0].price + (products[1].price * 2)) * 0.08,
        shipping: 15.99,
        total: (products[0].price + (products[1].price * 2)) * 1.08 + 15.99,
        status: "completed",
        paymentStatus: "paid",
        paymentMethod: "credit_card",
        shippingAddress: customers[0].address,
        trackingNumber: "TRK123456789",
        orderDate: new Date("2024-06-15"),
        shippedDate: new Date("2024-06-16"),
        deliveredDate: new Date("2024-06-18")
    },
    {
        _id: ObjectId(),
        orderNumber: "ORD-2024-002",
        customerId: customers[1]._id,
        customerEmail: customers[1].email,
        items: [
            {
                productId: products[2]._id,
                productName: products[2].name,
                quantity: 1,
                unitPrice: products[2].price,
                totalPrice: products[2].price
            }
        ],
        subtotal: products[2].price,
        tax: products[2].price * 0.08,
        shipping: 25.99,
        total: products[2].price * 1.08 + 25.99,
        status: "pending",
        paymentStatus: "paid",
        paymentMethod: "paypal",
        shippingAddress: customers[1].address,
        trackingNumber: null,
        orderDate: new Date(),
        shippedDate: null,
        deliveredDate: null
    },
    {
        _id: ObjectId(),
        orderNumber: "ORD-2024-003",
        customerId: customers[2]._id,
        customerEmail: customers[2].email,
        items: [
            {
                productId: products[1]._id,
                productName: products[1].name,
                quantity: 5,
                unitPrice: products[1].price,
                totalPrice: products[1].price * 5
            }
        ],
        subtotal: products[1].price * 5,
        tax: (products[1].price * 5) * 0.08,
        shipping: 0, // Free shipping for bulk order
        total: (products[1].price * 5) * 1.08,
        status: "shipped",
        paymentStatus: "paid",
        paymentMethod: "bank_transfer",
        shippingAddress: customers[2].address,
        trackingNumber: "TRK987654321",
        orderDate: new Date("2024-07-01"),
        shippedDate: new Date("2024-07-02"),
        deliveredDate: null
    }
]);

// Create indexes for better performance
db.customers.createIndex({ email: 1 }, { unique: true });
db.customers.createIndex({ "address.zipCode": 1 });
db.customers.createIndex({ tags: 1 });
db.customers.createIndex({ joinDate: 1 });

db.products.createIndex({ category: 1, subcategory: 1 });
db.products.createIndex({ brand: 1 });
db.products.createIndex({ price: 1 });
db.products.createIndex({ "ratings.average": -1 });
db.products.createIndex({ tags: 1 });

db.orders.createIndex({ customerId: 1 });
db.orders.createIndex({ orderDate: -1 });
db.orders.createIndex({ status: 1 });
db.orders.createIndex({ orderNumber: 1 }, { unique: true });

// Display summary
print("\n📊 Collection Summary:");
print("Customers:", db.customers.countDocuments());
print("Products:", db.products.countDocuments());
print("Orders:", db.orders.countDocuments());

print("\n📈 Sample Queries:");
print("Active customers:", db.customers.countDocuments({ isActive: true }));
print("Featured products:", db.products.countDocuments({ featured: true }));
print("Completed orders:", db.orders.countDocuments({ status: "completed" }));

EOF

echo "✅ MongoDB test container setup complete!"
echo ""
echo "📊 Container Details:"
echo "   Name: $CONTAINER_NAME"
echo "   Database: $DB_NAME"
echo "   Port: $DB_PORT"
echo ""
echo "🔗 Connection string: mongodb://localhost:$DB_PORT/$DB_NAME"
echo ""
echo "💡 Test the connection:"
echo "   dbvault test --config config/mongo-s3-test.yaml"
