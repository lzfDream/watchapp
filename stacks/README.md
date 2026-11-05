# 自建容器栈

把本机在跑的自建服务统一收在这里。每个服务一个子目录，各自带 `compose.yaml`；新机器复制整个 `stacks/` 后执行一条命令即可启动。

| 子目录 | 服务 | 端口 | 数据目录 | 镜像 |
|---|---|---|---|---|
| `navbook/` | Navbook 轻导航 | 5556 | `navbook/data/` | `ghcr.io/lzfdream/navbook:1.0.0` |
| `notes/` | LeafWiki 本地笔记 | 40001 | `notes/books/` | `ghcr.io/perber/leafwiki:latest`（当前 v0.14.1） |

## 一键启动

在仓库根目录执行：

```bash
./stacks/up.sh
```

或者进入本目录：

```bash
cd stacks
./up.sh
```

首次启动会自动创建 `navbook/data/`、`notes/books/`，并执行各自的 `init-data` 服务修正目录权限。

- 打开 Navbook：<http://localhost:5556>
- 打开笔记：<http://localhost:40001>

## 更新与运维

```bash
./stacks/up.sh --pull   # 先拉最新镜像再启动（跟进上游版本）
./stacks/status.sh      # 查看两个栈的状态
./stacks/down.sh        # 停止（数据目录保留）
```

只更新某一个栈也可以直接进子目录：

```bash
cd stacks/navbook
docker compose pull && docker compose up -d
```

Navbook 的版本固定在 compose 里；升版本时先改镜像 tag，再 `up -d`。LeafWiki 使用 `latest`，升级前建议先看上游 release 说明。

## 数据

- `navbook/data/`：`db.json`、`db.json.bak`，以及可选的 `bg.jpg|png|webp...`。
- `notes/books/`：LeafWiki 的笔记目录，一本书一个文件夹。
- 两个目录都在 `.gitignore` 里，**不会进仓库**。
- `down.sh` 只停容器，不删数据。

### 从旧部署迁移数据

当前机器上这两个服务仍在原来的目录运行。要把数据切到 `stacks/`，先停旧容器，再复制数据，最后启动：

```bash
# 示例（把 <旧目录> 换成旧部署目录）
cp -a <旧 navbook 目录>/data/. stacks/navbook/data/
cp -a <旧 notes 目录>/books/. stacks/notes/books/
./stacks/up.sh
```

如果直接启动空的 `stacks/`，会是空书签 / 空笔记，不要和旧目录同时挂载。

## 安全

- 两个服务都**没有账号保护**（LeafWiki 明确关闭了认证，Navbook 本身无登录），只适合本机 / 内网使用，不要直接暴露公网。
- LeafWiki 的 `LEAFWIKI_JWT_SECRET` 默认值只是占位符，仅在认证关闭时满足启动校验；需要公网访问时请自行加反向代理认证。
- 两个 `init-data` 服务只以 root 执行一次 `mkdir/chown`，应用容器本身以 uid 1000 运行。

## 文件

```
stacks/
├── README.md
├── up.sh          # 一键启动，--pull / --dry-run
├── down.sh        # 停止，保留数据
├── status.sh      # 状态
├── navbook/
│   └── compose.yaml
└── notes/
    └── compose.yaml
```
