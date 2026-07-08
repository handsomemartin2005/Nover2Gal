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

echo "[1/7] Installing system packages..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip nginx tar

echo "[2/7] Installing application files..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
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

echo "[3/7] Creating Python environment..."
python3 -m venv "$APP_DIR/backend/.venv"
"$APP_DIR/backend/.venv/bin/pip" install --upgrade pip wheel
"$APP_DIR/backend/.venv/bin/pip" install "fastapi>=0.116,<1.0" "uvicorn[standard]>=0.35,<1.0" "python-multipart>=0.0.20,<1.0"

echo "[4/7] Configuring environment..."
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
EOF
fi

if ! grep -q '^DEEPSEEK_API=.\+' /etc/novel2gal.env; then
  echo
  read -r -s -p "Paste DEEPSEEK_API for server, then press Enter: " DEEPSEEK_API_VALUE
  echo
  if [[ -n "$DEEPSEEK_API_VALUE" ]]; then
    sed -i "s|^DEEPSEEK_API=.*|DEEPSEEK_API=$DEEPSEEK_API_VALUE|" /etc/novel2gal.env
  fi
fi

echo "[5/7] Creating systemd service..."
cat >/etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Novel2Gal FastAPI service
After=network.target

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

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo "[6/7] Configuring Nginx..."
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

echo "[7/7] Checking service..."
sleep 2
systemctl --no-pager --full status "$SERVICE_NAME" || true
curl -fsS http://127.0.0.1:8001/health
echo
echo "Done. Open: http://47.94.183.24"
