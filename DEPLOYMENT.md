# Production Deployment Guide

This guide covers deploying the Data Extraction API and Excel Add-in system to production with HTTPS/HTTP2 support.

## Prerequisites

- Python 3.13+
- Node.js 18+ or Bun
- uv (Python package manager)
- SSL certificates (Let's Encrypt recommended)
- Reverse proxy (nginx/Apache) - optional but recommended

## Backend Deployment (FastAPI + DuckDB)

### 1. Environment Setup

```bash
# Clone and navigate to backend
cd rest_api_duckdb

# Install dependencies
uv sync --frozen

# Create production data directory
mkdir -p data
```

### 2. SSL Certificate Setup

#### Option A: Self-signed certificates (development/testing)
```bash
./setup_https.sh --dev
```

#### Option B: Let's Encrypt certificates (production)
```bash
# Install certbot
sudo apt-get install certbot

# Get certificates for your domain
sudo certbot certonly --standalone -d your-domain.com

# Configure with real certificates
./setup_https.sh --prod /etc/letsencrypt/live/your-domain.com/fullchain.pem /etc/letsencrypt/live/your-domain.com/privkey.pem
```

### 3. Production Environment Variables

Create `.env.production`:
```bash
# HTTPS Configuration
SSL_CERTFILE=/path/to/cert.pem
SSL_KEYFILE=/path/to/key.pem
HOST=0.0.0.0
PORT=8443

# CORS Configuration
ALLOWED_ORIGINS=https://your-domain.com,https://excel.office.com

# Database Configuration
DUCKDB_DATABASE_PATH=data/production.duckdb
PARQUET_DATA_PATH=data/production_events.parquet

# Security
PYTHONHTTPSVERIFY=1
RELOAD=false
```

### 4. Start Production Server

```bash
# Load environment and start server
source .env.production && uv run python -m app.main

# Or use systemd service (recommended)
sudo systemctl start data-extraction-api
```

### 5. Health Check

Test the deployment:
```bash
curl -k https://your-domain.com:8443/api/health
```

## Frontend Deployment (Svelte + Excel Add-in)

### 1. Environment Setup

```bash
# Navigate to frontend
cd excel-addin-svelte

# Install dependencies
bun install
```

### 2. Update API Configuration

Update the API_BASE_URL in `src/taskpane/App.svelte`:
```typescript
const API_BASE_URL = 'https://your-domain.com:8443';
```

### 3. Build for Production

```bash
# Build with optimizations
bun run build

# Verify build
ls -la dist/
```

### 4. Deploy Excel Add-in

#### Option A: Office 365 Admin Center
1. Upload `manifest.xml` to your Office 365 tenant
2. Deploy to users via admin center
3. Users install via "My Add-ins" in Excel

#### Option B: Direct Sideloading
1. Share the built `dist/` folder and `manifest.xml`
2. Users manually load via "Upload My Add-in" in Excel

## Production Security Checklist

### Backend Security
- [ ] HTTPS enabled with valid SSL certificates
- [ ] Security headers configured (HSTS, CSP, etc.)
- [ ] CORS properly configured for production domains
- [ ] Database files secured with proper permissions
- [ ] Logs configured for monitoring
- [ ] Rate limiting implemented if needed
- [ ] Firewall rules configured

### Frontend Security
- [ ] Built files served over HTTPS
- [ ] CSP headers allow necessary Office.js resources
- [ ] No sensitive data in client-side code
- [ ] Manifest.xml permissions minimized

## Monitoring and Maintenance

### Health Monitoring
```bash
# Check API health
curl -k https://your-domain.com:8443/api/health

# Check database status
curl -k https://your-domain.com:8443/api/info
```

### Log Monitoring
```bash
# View application logs
tail -f /var/log/data-extraction-api/app.log

# Check SSL certificate expiration
openssl x509 -in cert.pem -noout -dates
```

### Backup Strategy
```bash
# Backup Parquet data files
cp data/production_events.parquet backups/events_$(date +%Y%m%d).parquet

# Backup DuckDB database
cp data/production.duckdb backups/db_$(date +%Y%m%d).duckdb
```

## Reverse Proxy Setup (Optional)

### Nginx Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location /api/ {
        proxy_pass https://127.0.0.1:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location / {
        root /path/to/excel-addin-svelte/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

## Troubleshooting

### Common Issues

1. **SSL Certificate Issues**
   ```bash
   # Check certificate validity
   openssl x509 -in cert.pem -text -noout
   
   # Verify certificate chain
   openssl verify -CAfile ca.pem cert.pem
   ```

2. **CORS Issues**
   - Ensure `ALLOWED_ORIGINS` includes your Excel/Office domains
   - Check browser console for specific CORS errors
   - Verify preflight OPTIONS requests are handled

3. **Excel Add-in Issues**
   - Check manifest.xml URLs point to HTTPS endpoints
   - Verify Office.js is loaded correctly
   - Test in Excel Online vs Desktop

4. **Database Issues**
   ```bash
   # Check Parquet file integrity
   uv run python -c "import pandas as pd; print(pd.read_parquet('data/events.parquet').info())"
   
   # Verify DuckDB connection
   uv run python -c "import duckdb; conn = duckdb.connect('data/production.duckdb'); print(conn.execute('SELECT COUNT(*) FROM events').fetchone())"
   ```

## Performance Optimization

### Backend
- Use multiple workers: `workers=4` in uvicorn configuration
- Enable gzip compression
- Implement caching for frequently queried data
- Monitor memory usage with large Parquet files

### Frontend  
- Enable build minification and compression
- Use CDN for static assets
- Implement lazy loading for large result sets
- Cache API responses in browser storage

## Security Best Practices

1. **Keep certificates updated** - Set up automatic renewal
2. **Monitor access logs** - Watch for unusual access patterns  
3. **Regular security updates** - Keep all dependencies updated
4. **Input validation** - Verify all user inputs
5. **Rate limiting** - Prevent API abuse
6. **Backup encryption** - Encrypt sensitive backup data