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
