# Novel2Gal 自动部署

## 日常发布

在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\publish.ps1
```

脚本会自动完成：

1. 打包 `backend`、`frontend` 和发布所需文件。
2. 通过 `.deploy_keys\novel2gal_aliyun_ed25519` 上传到 `47.94.183.24`。
3. 上传服务器安装脚本并远程执行。
4. 重启 `novel2gal` 和 Nginx。
5. 请求 `http://dianlijiliang.cn/health`，确认返回 `{"status":"ok"}`。

安装脚本还会以本机回环地址部署 Redis、PostgreSQL 和 MinIO，并启动独立的
`novel2gal-worker`。发布成功需要 `/health/ready` 中三个依赖全部为 `true`。

默认不会保留本地发布包。需要保留时：

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\publish.ps1 -KeepPackage
```

## 参数

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\publish.ps1 `
  -Server 47.94.183.24 `
  -User root `
  -Domain dianlijiliang.cn `
  -KeyPath .deploy_keys\novel2gal_aliyun_ed25519
```

首次部署或服务器重装时，直接运行原有的 `server_install.sh`。服务器上的 `/etc/novel2gal.env` 会被保留，里面的 `DEEPSEEK_API` 不会被打包，也不会进入 Git。

发布前建议先运行：

```powershell
$env:PYTHONPATH = "$PWD\backend"
& "$PWD\backend\.venv\Scripts\python.exe" -m unittest discover -s tests
```

## HTTPS 与首次管理员

安装脚本会为真实域名安装 Certbot、签发证书并把 HTTP 重定向到 HTTPS。注册与登录上线前必须确认 `https://<域名>/health` 可访问。

首次上线账户系统时，在服务器的 `/etc/novel2gal.env` 临时加入：

```text
AUTH_DB_PATH=/var/lib/novel2gal/auth.sqlite3
SESSION_COOKIE_SECURE=true
NOVEL2GAL_ADMIN_USERNAME=admin
NOVEL2GAL_ADMIN_PASSWORD=<一次性强密码>
NOVEL2GAL_CLAIM_LEGACY_TO_ADMIN=true
```

服务首次成功启动后，旧的无归属项目与样例会转给管理员。随后删除 `NOVEL2GAL_ADMIN_PASSWORD` 与 `NOVEL2GAL_CLAIM_LEGACY_TO_ADMIN` 两行并重启服务，避免在环境文件中长期保留引导密码。
