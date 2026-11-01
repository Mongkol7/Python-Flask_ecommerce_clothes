#!/usr/bin/env bash
set -e

echo "=== [1/5] Writing mk7.service for Gunicorn ==="
sudo tee /etc/systemd/system/mk7.service > /dev/null << 'EOF'
[Unit]
Description=MK7 Luxury Storefront
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/ecommerce_clothes
Environment="PATH=/home/ubuntu/ecommerce_clothes/.venv/bin"
ExecStart=/home/ubuntu/ecommerce_clothes/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "=== [2/5] Writing Nginx Configuration ==="
sudo tee /etc/nginx/sites-available/mk7 > /dev/null << 'EOF'
server {
    listen 80 default_server;
    server_name _;

    client_max_body_size 10M;

    location /static/ {
        alias /home/ubuntu/ecommerce_clothes/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

echo "=== [3/5] Setting Static Directory Permissions & Enabling Nginx Site ==="
# Allow Nginx (www-data) to access static assets in /home/ubuntu
chmod 755 /home/ubuntu
chmod -R 755 /home/ubuntu/ecommerce_clothes/static

sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/mk7
sudo ln -s /etc/nginx/sites-available/mk7 /etc/nginx/sites-enabled/mk7
sudo nginx -t

echo "=== [4/5] Reloading and Starting Services ==="
sudo systemctl daemon-reload
sudo systemctl enable mk7
sudo systemctl restart mk7
sudo systemctl restart nginx

echo "=== [5/5] Checking Service Status ==="
sudo systemctl status mk7 --no-pager -n 5 || true

echo ""
echo "=========================================================="
echo "🎉 SUCCESS: MK7 Luxury Store is now running!"
echo "Open your browser and navigate to: http://$(curl -s http://checkip.amazonaws.com)"
echo "=========================================================="

