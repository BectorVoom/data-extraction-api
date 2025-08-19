# Data Extraction API System

A complete full-stack application featuring a **FastAPI backend** with **DuckDB** database and a **Svelte frontend** with **TypeScript** and **Tailwind CSS**. Built for production with comprehensive validation, testing, and documentation.

## 🎯 Project Overview

This system allows users to query data from a database based on ID and date range criteria. It demonstrates modern web development practices with:

- **Backend**: FastAPI + DuckDB + Python 3.13 + uv
- **Frontend**: Svelte 5 + TypeScript + Tailwind CSS + Bun
- **Testing**: pytest + 48 comprehensive tests
- **Validation**: Strict date format validation (yyyy/mm/dd)
- **Security**: SQL injection prevention, CORS configuration
- **Documentation**: Complete API docs + interactive Swagger UI

## ✅ Acceptance Criteria

All project requirements have been met:

- ✅ **Valid POST returns 200**: `/api/query` endpoint returns JSON array of matching rows
- ✅ **Validation errors return 422**: Malformed dates return descriptive error messages  
- ✅ **Tests pass**: 48 unit and integration tests with pytest
- ✅ **Builds locally**: Both frontend and backend build and run successfully
- ✅ **Production-ready**: Logging, error handling, security measures implemented

## 🚀 Quick Start

### Prerequisites
- **Python 3.13+** with **uv** installed
- **Node.js 18+** or **Bun**

### 1. Backend Setup
```bash
cd rest_api_duckdb
uv sync --extra dev
uv run python -m app.main
```
Backend runs on: `http://localhost:8000`

### 2. Frontend Setup  
```bash
cd frontend_svelte_tailwindcss
bun install
bun run dev
```
Frontend runs on: `http://localhost:5173`

### 3. Run Tests
```bash
cd rest_api_duckdb
uv run pytest  # 48 tests should pass
```

## 📋 API Usage Examples

### Valid Query
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"id": "12345", "fromDate": "2024/01/01", "toDate": "2024/12/31"}'
```

**Response (200 OK)**:
```json
{
  "data": [
    {
      "id": "12345",
      "event_date": "2024-01-15", 
      "event_type": "login",
      "description": "User login event",
      "value": 1.0,
      "created_at": "2024-01-15T10:30:00"
    }
  ],
  "count": 1,
  "query_info": {...}
}
```

### Invalid Date Format (Validation Error)
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"id": "12345", "fromDate": "2024-01-01", "toDate": "2024/12/31"}'
```

**Response (422 Unprocessable Entity)**:
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "fromDate"],
      "msg": "Date must be in yyyy/mm/dd format"
    }
  ]
}
```

## 🏗️ Architecture

```
extract_data_env/
├── rest_api_duckdb/           # FastAPI Backend
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   ├── api/query.py      # API endpoints  
│   │   ├── models/schemas.py # Pydantic models
│   │   └── services/database.py # DuckDB service
│   ├── tests/                # 48 comprehensive tests
│   └── pyproject.toml        # uv dependencies
├── frontend_svelte_tailwindcss/ # Svelte Frontend
│   ├── src/
│   │   ├── lib/
│   │   │   ├── QueryForm.svelte    # Main form component
│   │   │   ├── ResultsTable.svelte # Results display
│   │   │   ├── api.ts             # API service layer
│   │   │   ├── types.ts           # TypeScript interfaces
│   │   │   └── validation.ts      # Client validation
│   │   └── App.svelte        # Root component
│   └── package.json          # Bun dependencies
└── test_acceptance.sh        # End-to-end tests
```

## 🧪 Testing Strategy

### Backend Testing (48 tests)
- **Unit Tests**: Pydantic model validation, date parsing, database operations
- **Integration Tests**: Full API endpoint testing with TestClient
- **Edge Cases**: Leap years, invalid dates, SQL injection prevention
- **Error Handling**: Validation errors, missing fields, malformed JSON

```bash
cd rest_api_duckdb
uv run pytest -v  # Run all tests with verbose output
```

### End-to-End Testing
```bash
./test_acceptance.sh  # Automated acceptance tests
```

## 🔒 Security Features

### Backend Security
- **SQL Injection Prevention**: All queries use parameterized statements
- **Input Validation**: Strict Pydantic validation on all inputs
- **Error Handling**: Production-safe error messages
- **CORS Configuration**: Restricted to development origins

### Frontend Security  
- **Client-Side Validation**: Real-time validation prevents invalid submissions
- **Type Safety**: TypeScript prevents runtime errors
- **XSS Prevention**: Svelte's automatic escaping

## 📊 Sample Data

The system includes sample data for testing:

| ID | Events | Date Range |
|----|--------|------------|
| `12345` | login, purchase, logout | 2024-01-15 to 2024-03-10 |
| `67890` | login, view, purchase | 2024-01-20 to 2024-04-15 |
| `11111` | signup, login | 2024-05-01 to 2024-05-02 |
| `22222` | login, purchase | 2023-12-15 to 2024-01-01 |

## 📖 Documentation

### Interactive API Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Health & Monitoring
- **Health Check**: `http://localhost:8000/api/health`
- **Database Info**: `http://localhost:8000/api/info`

### Component Documentation
- [Backend README](rest_api_duckdb/README.md) - FastAPI + DuckDB details
- [Frontend README](frontend_svelte_tailwindcss/README.md) - Svelte + TypeScript details

## 🛠️ Development Commands

### Backend Commands
```bash
cd rest_api_duckdb
uv sync --extra dev          # Install dependencies
uv run python -m app.main    # Start development server
uv run pytest              # Run all tests
uv run pytest -v           # Run tests with verbose output
```

### Frontend Commands
```bash
cd frontend_svelte_tailwindcss
bun install                 # Install dependencies  
bun run dev                # Start development server
bun run build              # Build for production
bun run preview            # Preview production build
bun run check              # TypeScript type checking
```

## 🚀 Production Deployment

### Backend Deployment
```bash
cd rest_api_duckdb
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend Deployment
```bash
cd frontend_svelte_tailwindcss
bun run build
# Deploy `dist/` folder to static hosting (Vercel, Netlify, etc.)
```

## 🎨 Technology Stack

### Backend Technologies
- **FastAPI** - Modern Python web framework
- **DuckDB** - High-performance analytical database  
- **Pydantic** - Data validation and serialization
- **pytest** - Testing framework
- **uv** - Fast Python package manager

### Frontend Technologies
- **Svelte 5** - Reactive UI framework with runes
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **Vite** - Fast build tool and dev server
- **Bun** - Fast JavaScript runtime and package manager

## 📈 Performance Features

### Backend Performance
- **Connection Pooling**: Efficient DuckDB connection management
- **Parameterized Queries**: Optimized and secure database queries
- **Response Caching**: Structured response format for client caching
- **Error Logging**: Comprehensive logging for monitoring

### Frontend Performance  
- **Tree Shaking**: Unused code elimination in production builds
- **CSS Purging**: Remove unused Tailwind classes
- **Code Splitting**: Optimal bundle loading
- **Reactive Updates**: Efficient DOM updates with Svelte

## 🤝 Contributing

This project demonstrates production-ready development practices:

1. **Code Quality**: TypeScript strict mode, comprehensive testing
2. **Documentation**: Detailed README files and API documentation
3. **Security**: Input validation, parameterized queries, error handling
4. **Testing**: Unit tests, integration tests, end-to-end validation
5. **Performance**: Optimized builds, efficient data handling

## 📄 License

This project is a technical implementation demonstrating modern full-stack development with Python, TypeScript, and production-ready practices.

---

**🎉 Ready to use! Start both servers and visit `http://localhost:5173` to see the complete system in action.**