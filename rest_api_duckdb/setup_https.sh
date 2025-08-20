#!/bin/bash

# HTTPS Setup Script for Data Extraction API
# This script helps set up HTTPS certificates for production deployment

set -e

echo "🔐 Setting up HTTPS configuration for Data Extraction API"
echo "========================================================="

# Create certificates directory
CERT_DIR="./certificates"
mkdir -p "$CERT_DIR"

# Function to create self-signed certificates for development/testing
create_self_signed_certs() {
    echo "📜 Creating self-signed certificates for testing..."
    
    openssl req -x509 -newkey rsa:4096 -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" \
        -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    
    echo "✅ Self-signed certificates created:"
    echo "   - Certificate: $CERT_DIR/cert.pem"
    echo "   - Private Key: $CERT_DIR/key.pem"
    echo ""
    echo "⚠️  WARNING: These are self-signed certificates for testing only!"
    echo "   For production, use certificates from a trusted CA."
}

# Function to set up environment variables
setup_env() {
    local cert_file="$1"
    local key_file="$2"
    
    echo "🌍 Setting up environment variables..."
    
    cat > .env.production << EOF
# Production HTTPS Configuration
SSL_CERTFILE=$cert_file
SSL_KEYFILE=$key_file
HOST=0.0.0.0
PORT=8443
RELOAD=false

# Database Configuration
DUCKDB_DATABASE_PATH=data/production.duckdb
PARQUET_DATA_PATH=data/production_events.parquet

# Security Headers
PYTHONHTTPSVERIFY=1
EOF
    
    echo "✅ Production environment file created: .env.production"
}

# Function to display usage instructions
show_usage() {
    echo "📖 Usage Instructions:"
    echo "====================="
    echo ""
    echo "1. For development with self-signed certificates:"
    echo "   ./setup_https.sh --dev"
    echo ""
    echo "2. For production with your own certificates:"
    echo "   ./setup_https.sh --prod /path/to/cert.pem /path/to/key.pem"
    echo ""
    echo "3. To run with HTTPS:"
    echo "   uv run python -m app.main"
    echo "   # Or with production env:"
    echo "   source .env.production && uv run python -m app.main"
    echo ""
    echo "4. For Let's Encrypt certificates (recommended for production):"
    echo "   # Install certbot first"
    echo "   sudo certbot certonly --standalone -d your-domain.com"
    echo "   # Then use:"
    echo "   ./setup_https.sh --prod /etc/letsencrypt/live/your-domain.com/fullchain.pem /etc/letsencrypt/live/your-domain.com/privkey.pem"
}

# Main script logic
case "${1:-}" in
    "--dev")
        create_self_signed_certs
        setup_env "$CERT_DIR/cert.pem" "$CERT_DIR/key.pem"
        echo ""
        echo "🚀 Development HTTPS setup complete!"
        echo "   Run: SSL_CERTFILE=$CERT_DIR/cert.pem SSL_KEYFILE=$CERT_DIR/key.pem uv run python -m app.main"
        ;;
    "--prod")
        if [ $# -ne 3 ]; then
            echo "❌ Error: Production mode requires certificate and key file paths"
            echo "   Usage: $0 --prod /path/to/cert.pem /path/to/key.pem"
            exit 1
        fi
        
        cert_file="$2"
        key_file="$3"
        
        if [ ! -f "$cert_file" ]; then
            echo "❌ Error: Certificate file not found: $cert_file"
            exit 1
        fi
        
        if [ ! -f "$key_file" ]; then
            echo "❌ Error: Key file not found: $key_file"
            exit 1
        fi
        
        setup_env "$cert_file" "$key_file"
        echo "✅ Production HTTPS setup complete!"
        echo "   Certificate: $cert_file"
        echo "   Private Key: $key_file"
        ;;
    *)
        show_usage
        exit 0
        ;;
esac

echo ""
echo "📋 Next Steps:"
echo "1. Update your frontend API_BASE_URL to use https:// and the correct port"
echo "2. For production, ensure your firewall allows traffic on the HTTPS port"
echo "3. Consider using a reverse proxy (nginx/Apache) for additional security"
echo "4. Monitor your SSL certificate expiration dates"