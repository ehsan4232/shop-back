# Mall Platform Backend (فروشگاه‌ساز مال)

Backend API for Mall - a Persian e-commerce platform for building store websites in Iran.

## 🏪 About Mall Platform

**Mall (فروشگاه‌ساز مال)** is a platform for building websites for stores in Iran. Store owners can login to the platform to manage their stores and have their products available on their websites with customers being able to create accounts, view orders, edit cart, and checkout.

### Key Features (Product Description Compliance)

✅ **Multi-Store Platform**: Support for 1000+ store owners with independent domains  
✅ **Persian-Only Interface**: Complete Farsi support with RTL design  
✅ **Flexible Product System**: Clothing, jewelry, accessories, pet shop, services, electronics  
✅ **Product Instances**: Multiple identical products (e.g., 3 yellow Adidas XL t-shirts)  
✅ **Stock Warnings**: Alert customers when ≤3 items remaining  
✅ **Social Media Integration**: Import from Telegram/Instagram (last 5 posts)  
✅ **OTP Authentication**: All logins use SMS OTP verification  
✅ **Iranian Integrations**: Logistics providers and payment gateways  
✅ **Analytics Dashboard**: Sales, views, and interaction charts for store owners  

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone and setup
git clone https://github.com/ehsan4232/shop-back.git
cd shop-back
cp .env.example .env

# Start services
docker-compose up -d

# Run migrations and create admin
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
```

### Manual Setup

```bash
# Setup environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure database and Redis
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## 📖 API Documentation

- **Swagger UI**: http://localhost:8000/api/docs/
- **Django Admin**: http://localhost:8000/admin/
- **API Schema**: http://localhost:8000/api/schema/

## 🏗️ Architecture

```
apps/
├── accounts/        # User authentication & OTP
├── stores/          # Store management & themes
├── products/        # Product catalog & instances
├── orders/          # Cart & checkout system
├── payments/        # Iranian payment gateways
├── social_media/    # Telegram/Instagram integration
├── communications/  # SMS campaigns & notifications
└── core/           # Shared utilities & mixins
```

## 🔑 Core API Endpoints

### Authentication (OTP-based)
```
POST /api/v1/auth/send-otp/     # Send OTP to phone
POST /api/v1/auth/verify-otp/   # Verify OTP and login
GET  /api/v1/auth/profile/      # User profile
```

### Store Management
```
GET  /api/v1/stores/            # List stores
POST /api/v1/stores/            # Create store
GET  /api/v1/stores/my-store/   # Current store
PUT  /api/v1/stores/themes/     # Change theme
```

### Products (Per Product Description)
```
GET  /api/v1/products/categories/     # Product categories
GET  /api/v1/products/products/       # Product listings
POST /api/v1/products/instances/      # Create product instances
POST /api/v1/products/social-import/  # Import from social media
GET  /api/v1/products/stock-warnings/ # Products with low stock
```

### Customer Features
```
GET  /api/v1/orders/cart/       # Shopping cart
POST /api/v1/orders/checkout/   # Process checkout
GET  /api/v1/orders/history/    # Order history
```

## 🎨 Product Description Features

### Product System
- **Various Types**: Cloth, jewelry, accessories, pet shop, services, electronics
- **Attributes**: Color, size, brand, weight, categories (sex, type, season)
- **Instances**: Support for multiple identical products
- **Stock Warnings**: Automatic alerts when ≤3 items remaining

### Social Media Integration
- **Telegram/Instagram Import**: Gets last 5 posts and stories
- **Content Extraction**: Separates pics, videos, and text
- **Easy Selection**: Store owners can select materials for product definition

### Store Features
- **Independent Domains**: Each store can have its own domain/subdomain
- **Theme Selection**: Multiple fancy and modern designs
- **Analytics**: Charts for sales, website views, and interactions
- **Marketing**: SMS campaigns and promotion management

## 🔧 Development

### Running Tests
```bash
pytest
```

### Background Tasks (Celery)
```bash
celery -A mall worker -l info
```

### Code Quality
```bash
flake8
black .
```

## 🚀 Production Deployment

Refer to `MIGRATION_GUIDE.md` for complete production deployment instructions.

### Performance Specs
- **Concurrent Users**: Supports 1000+ online users
- **Store Capacity**: 1000+ store owners
- **Response Time**: <200ms API responses
- **Database**: PostgreSQL with Redis caching

## 🇮🇷 Iranian Compliance

- **Language**: Complete Persian (Farsi) interface
- **Payment**: Integration with Iranian payment gateways
- **Logistics**: Support for Iranian delivery providers
- **SMS**: Persian SMS templates for OTP and campaigns
- **Cultural**: Persian calendar and number formatting

## 📱 Related Repositories

- **Frontend**: [shop-front](https://github.com/ehsan4232/shop-front) - Next.js store websites and admin
- **Documentation**: [shop](https://github.com/ehsan4232/shop) - Architecture and product description

## 📄 License

Proprietary - All rights reserved

---

*Built for Iranian entrepreneurs and store owners 🇮🇷*