# Mall Platform Backend

Backend API for the Mall e-commerce platform built with Django REST Framework.

## Features

- **Multi-tenant Architecture**: Support for multiple stores
- **Persian Language Support**: Full RTL and Persian optimization
- **Advanced Product Management**: Hierarchical categories with flexible attributes
- **OTP Authentication**: SMS-based authentication system
- **Comprehensive Admin**: Django admin with Persian interface
- **API Documentation**: Auto-generated OpenAPI docs
- **Scalable Design**: Optimized for 1000+ concurrent users

## Quick Start

### Using Docker (Recommended)

1. **Clone and setup**
   ```bash
   git clone https://github.com/ehsan4232/shop-back.git
   cd shop-back
   cp .env.example .env
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

3. **Run migrations**
   ```bash
   docker-compose exec backend python manage.py migrate
   docker-compose exec backend python manage.py createsuperuser
   ```

### Manual Setup

1. **Setup environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure database**
   ```bash
   # Setup PostgreSQL and Redis
   cp .env.example .env
   # Edit .env with your database settings
   ```

3. **Run migrations**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

## API Documentation

- **Swagger UI**: http://localhost:8000/api/docs/
- **Admin Panel**: http://localhost:8000/admin/
- **API Schema**: http://localhost:8000/api/schema/

## Project Structure

```
shop-back/
├── mall/                 # Main Django project
│   ├── settings.py      # Configuration
│   ├── urls.py          # URL routing
│   └── celery.py        # Background tasks
├── apps/                # Django applications
│   ├── accounts/        # User authentication & OTP
│   ├── stores/          # Store management
│   ├── products/        # Product catalog & hierarchy
│   └── orders/          # Order processing & cart
├── requirements.txt     # Dependencies
└── docker-compose.yml   # Development environment
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/send-otp/` - Send OTP code
- `POST /api/v1/auth/verify-otp/` - Verify OTP and login
- `GET /api/v1/auth/profile/` - Get user profile

### Stores
- `GET /api/v1/stores/` - List user stores
- `POST /api/v1/stores/` - Create new store
- `GET /api/v1/stores/my-store/` - Get current user's store

### Products
- `GET /api/v1/products/categories/` - Product categories
- `GET /api/v1/products/products/` - Product listings
- `GET /api/v1/products/instances/` - Product instances

### Orders
- `GET /api/v1/orders/orders/` - Order history
- `GET /api/v1/orders/cart/` - Shopping cart
- `POST /api/v1/orders/checkout/` - Process checkout

## Key Features

### Persian Language Support
- RTL admin interface
- Persian field names and help text
- Cultural number formatting
- Persian SMS templates

### Product Hierarchy System
- Unlimited category depth with MPTT
- Flexible product attributes
- Categorizer attributes for subclass generation
- Product instances with variations

### Multi-tenant Architecture
- Store isolation
- Custom domain support
- Theme and layout customization

## Development

### Running Tests
```bash
pytest
```

### Background Tasks
```bash
# Start Celery worker
celery -A mall worker -l info
```

### Code Quality
```bash
flake8
black .
```

## Deployment

Refer to the main [Architecture documentation](../shop/ARCHITECTURE.md) for production deployment guidelines.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

Proprietary - All rights reserved