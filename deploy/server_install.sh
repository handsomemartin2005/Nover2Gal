#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/novel2gal"
PACKAGE_PATH="${1:-/tmp/novel2gal-release.tar.gz}"
SERVICE_NAME="novel2gal"
DOMAIN_NAME="${NOVEL2GAL_DOMAIN:-_}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root."
  exit 1
fi

if [[ ! -f "$PACKAGE_PATH" ]]; then
  echo "Release package not found: $PACKAGE_PATH"
  echo "Upload novel2gal-release.tar.gz to /tmp/novel2gal-release.tar.gz first."
  exit 1
fi

echo "[1/10] Installing system packages..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip nginx tar certbot python3-certbot-nginx redis-server postgresql curl

echo "[2/10] Ensuring swap space..."
if ! swapon --show=NAME | grep -qx '/swapfile'; then
  if [[ ! -f /swapfile ]]; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
  fi
  swapon /swapfile || true
fi
if ! grep -q '^/swapfile ' /etc/fstab; then
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "[3/10] Installing application files..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
systemctl stop "${SERVICE_NAME}-worker" 2>/dev/null || true
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
case "$PACKAGE_PATH" in
  *.tar.gz|*.tgz)
    tar -xzf "$PACKAGE_PATH" -C "$APP_DIR"
    ;;
  *.zip)
    apt-get install -y unzip
    unzip -q "$PACKAGE_PATH" -d "$APP_DIR"
    ;;
  *)
    echo "Unsupported package format: $PACKAGE_PATH"
    exit 1
    ;;
esac

echo "[4/10] Creating Python environment..."
python3 -m venv "$APP_DIR/backend/.venv"
"$APP_DIR/backend/.venv/bin/pip" install --upgrade pip wheel
"$APP_DIR/backend/.venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

echo "[5/10] Configuring environment..."
if [[ ! -f /etc/novel2gal.env ]]; then
  echo "DEEPSEEK_API=" > /etc/novel2gal.env
  chmod 600 /etc/novel2gal.env
fi

if ! grep -q '^LLM_MODEL=' /etc/novel2gal.env; then
  cat >> /etc/novel2gal.env <<'EOF'
LLM_MODEL=deepseek-v4-pro
APP_ENV=prod
MAX_RETRIEVED_CHUNKS=8
MAX_CHUNK_CHARS=1500
CHUNK_OVERLAP_CHARS=200
MAX_UPLOAD_BYTES=26214400
MAX_PIPELINE_TEXT_CHARS=1200000
MAX_PIPELINE_PROCESS_CHARS=120000
EOF
fi

if ! grep -q '^MAX_UPLOAD_BYTES=' /etc/novel2gal.env; then
  echo 'MAX_UPLOAD_BYTES=26214400' >> /etc/novel2gal.env
fi

if ! grep -q '^MAX_PIPELINE_TEXT_CHARS=' /etc/novel2gal.env; then
  echo 'MAX_PIPELINE_TEXT_CHARS=1200000' >> /etc/novel2gal.env
fi

if ! grep -q '^MAX_PIPELINE_PROCESS_CHARS=' /etc/novel2gal.env; then
  echo 'MAX_PIPELINE_PROCESS_CHARS=120000' >> /etc/novel2gal.env
fi

if ! grep -q '^PROJECT_STORE_DIR=' /etc/novel2gal.env; then
  echo 'PROJECT_STORE_DIR=/var/lib/novel2gal/projects' >> /etc/novel2gal.env
fi

if ! grep -q '^AUTH_DB_PATH=' /etc/novel2gal.env; then
  echo 'AUTH_DB_PATH=/var/lib/novel2gal/auth.sqlite3' >> /etc/novel2gal.env
fi

if ! grep -q '^SESSION_COOKIE_SECURE=' /etc/novel2gal.env; then
  echo 'SESSION_COOKIE_SECURE=true' >> /etc/novel2gal.env
fi

mkdir -p /var/lib/novel2gal/projects
chmod 700 /var/lib/novel2gal

echo "[6/10] Configuring Redis and PostgreSQL..."
systemctl enable --now redis-server postgresql
if ! grep -q '^REDIS_URL=' /etc/novel2gal.env; then
  echo 'REDIS_URL=redis://127.0.0.1:6379/0' >> /etc/novel2gal.env
fi
if ! grep -q '^DATABASE_URL=' /etc/novel2gal.env; then
  DB_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(36))')"
  if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='novel2gal'" | grep -q 1; then
    runuser -u postgres -- psql -c "CREATE ROLE novel2gal LOGIN PASSWORD '${DB_PASSWORD}'"
  else
    runuser -u postgres -- psql -c "ALTER ROLE novel2gal PASSWORD '${DB_PASSWORD}'"
  fi
  if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='novel2gal'" | grep -q 1; then
    runuser -u postgres -- createdb -O novel2gal novel2gal
  fi
  echo "DATABASE_URL=postgresql://novel2gal:${DB_PASSWORD}@127.0.0.1:5432/novel2gal" >> /etc/novel2gal.env
fi

echo "[7/10] Configuring S3-compatible object storage..."
if ! command -v minio >/dev/null 2>&1; then
  curl -fsSL https://dl.min.io/server/minio/release/linux-amd64/minio -o /usr/local/bin/minio
  chmod +x /usr/local/bin/minio
fi
if ! id -u minio-user >/dev/null 2>&1; then
  useradd --system --home /var/lib/minio --shell /usr/sbin/nologin minio-user
fi
mkdir -p /var/lib/minio
chown -R minio-user:minio-user /var/lib/minio
if ! grep -q '^S3_ACCESS_KEY_ID=' /etc/novel2gal.env; then
  MINIO_USER="novel2gal-$(python3 -c 'import secrets; print(secrets.token_hex(4))')"
  MINIO_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  cat >> /etc/novel2gal.env <<EOF
S3_ENDPOINT_URL=http://127.0.0.1:9000
S3_ACCESS_KEY_ID=${MINIO_USER}
S3_SECRET_ACCESS_KEY=${MINIO_PASSWORD}
S3_BUCKET=novel2gal-media
S3_REGION=us-east-1
MINIO_ROOT_USER=${MINIO_USER}
MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}
EOF
fi
cat >/etc/systemd/system/minio.service <<'EOF'
[Unit]
Description=Novel2Gal MinIO object storage
After=network-online.target

[Service]
User=minio-user
Group=minio-user
EnvironmentFile=/etc/novel2gal.env
ExecStart=/usr/local/bin/minio server /var/lib/minio --address 127.0.0.1:9000 --console-address 127.0.0.1:9001
Restart=always
RestartSec=3
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now minio

if ! grep -q '^DEEPSEEK_API=.\+' /etc/novel2gal.env; then
  echo
  read -r -s -p "Paste DEEPSEEK_API for server, then press Enter: " DEEPSEEK_API_VALUE
  echo
  if [[ -n "$DEEPSEEK_API_VALUE" ]]; then
    sed -i "s|^DEEPSEEK_API=.*|DEEPSEEK_API=$DEEPSEEK_API_VALUE|" /etc/novel2gal.env
  fi
fi

echo "[8/10] Creating systemd services..."
cat >/etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Novel2Gal FastAPI service
After=network.target redis-server.service postgresql.service minio.service
Requires=redis-server.service postgresql.service minio.service

[Service]
Type=simple
WorkingDirectory=${APP_DIR}/backend
EnvironmentFile=/etc/novel2gal.env
ExecStart=${APP_DIR}/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/${SERVICE_NAME}-worker.service <<EOF
[Unit]
Description=Novel2Gal Redis background worker
After=network.target redis-server.service postgresql.service minio.service
Requires=redis-server.service postgresql.service minio.service

[Service]
Type=simple
WorkingDirectory=${APP_DIR}/backend
EnvironmentFile=/etc/novel2gal.env
ExecStart=${APP_DIR}/backend/.venv/bin/python -m app.worker
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl enable "${SERVICE_NAME}-worker"
systemctl restart "$SERVICE_NAME"
systemctl restart "${SERVICE_NAME}-worker"

echo "[9/10] Configuring Nginx..."
cat >/etc/nginx/sites-available/novel2gal <<EOF
server {
    listen 80;
    server_name ${DOMAIN_NAME};

    client_max_body_size 100m;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/novel2gal /etc/nginx/sites-enabled/novel2gal
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl reload nginx

if [[ "$DOMAIN_NAME" != "_" && ! "$DOMAIN_NAME" =~ ^[0-9.]+$ ]]; then
  echo "[9/10] Enabling HTTPS..."
  certbot --nginx --non-interactive --agree-tos --register-unsafely-without-email \
    --redirect --keep-until-expiring -d "$DOMAIN_NAME"
fi

echo "[10/10] Checking services..."
sleep 2
systemctl --no-pager --full status "$SERVICE_NAME" || true
systemctl --no-pager --full status "${SERVICE_NAME}-worker" || true
curl -fsS http://127.0.0.1:8001/health
echo
curl -fsS http://127.0.0.1:8001/health/ready
echo
if [[ "$DOMAIN_NAME" != "_" && ! "$DOMAIN_NAME" =~ ^[0-9.]+$ ]]; then
  echo "Done. Open: https://${DOMAIN_NAME}"
else
  echo "Done. Open: http://47.94.183.24"
fi
