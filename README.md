# DNF Admin v4

DNF 游戏后台管理系统 — 单文件架构，轻量高效。

## 架构

```
┌─────────────────────────────────────────────┐
│              Browser (前端)                  │
│         dashboard.html (单文件 SPA)          │
│   Vue 3 + Element Plus + ECharts            │
└──────────────────┬──────────────────────────┘
                   │ HTTP REST API
┌──────────────────▼──────────────────────────┐
│           server.py (Python 后端)            │
│        http.server + pymysql 直连            │
├─────────────────────────────────────────────┤
│  路由层        │  业务层        │  数据层     │
│  GET/POST     │  GM/统计/PVF  │  MySQL      │
│  静态文件     │  服务器监控    │  直连查询   │
└─────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│              MySQL 数据库                    │
│   taiwan_cain / taiwan_login / taiwan_bone  │
└─────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + Element Plus + ECharts | 单文件 SPA，内嵌 CSS/JS |
| 后端 | Python 3 + http.server | 零依赖框架，仅需 pymysql |
| 数据库 | MySQL 5.7 | DNF 服务端数据库直连 |
| 部署 | 单进程 | `python3 server.py` 即可运行 |

### 设计理念

- **单文件优先**: 前端 `dashboard.html` + 后端 `server.py`，两个文件搞定一切
- **零框架依赖**: 不用 Flask/FastAPI/Django，Python 标准库 http.server 足够
- **直连数据库**: pymysql 直连 MySQL，无 ORM，SQL 透明可控
- **参考 edict 架构**: 轻量、高效、易维护

## 功能模块

### 📊 仪表盘
- 服务器状态概览
- 账号/角色/在线统计
- 实时数据图表

### 👥 账号管理
- 账号列表（分页、搜索、筛选）
- 账号详情（角色列表、封禁状态）
- 封禁/解封操作

### 🎮 角色管理
- 角色列表（按等级/职业/在线筛选）
- 角色详情（属性、装备、背包、技能）
- GM 操作（发物品、改等级、加金币）

### 📦 物品系统
- 物品查询（支持 ID/名称搜索）
- 物品详情（属性、描述）
- PVF 数据解析

### 🐉 怪物查询
- 怪物列表（分页、搜索）
- 怪物详情（属性、掉落）

### 📮 GM 功能
- 公告管理（发布/修改）
- 物品发放
- 等级调整
- 金币操作
- 踢人/封禁/解封

### 🗂️ PVF 管理
- PVF 文件列表
- 加载/上传 PVF 文件
- 导入 PVF 数据到数据库

### 📈 服务端监控
- Docker/MySQL/游戏服务状态
- 系统资源（磁盘/内存/网络）
- 启动/停止服务
- 问题诊断（自动检测封禁等问题）
- 服务端配置查看

### 🎯 活动管理
- 活动列表（79 个活动）
- 活动详情（ID/名称/说明/类型/日期/状态）
- 活动开关（启用/禁用）
- 自定义日期设置
- 批量操作

### 📊 统计分析
- 账号增长趋势
- 角色等级分布
- 职业分布
- 在线人数统计

## 快速开始

### 环境要求

- Python 3.8+
- pymysql (`pip install pymysql`)
- MySQL 数据库（DNF 服务端）

### 启动

```bash
# 安装依赖
pip install pymysql

# 启动服务
python3 server.py

# 访问 http://localhost:18885
```

### 配置

编辑 `server.py` 顶部的数据库配置：

```python
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'root',
    'password': 'your_password',
    'charset': 'latin1',
    'use_unicode': False,
}
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 统计数据 |
| GET | `/api/accounts` | 账号列表 |
| GET | `/api/accounts/<uid>` | 账号详情 |
| GET | `/api/characters` | 角色列表 |
| GET | `/api/characters/<id>` | 角色详情 |
| GET | `/api/items` | 物品查询 |
| GET | `/api/items/<id>` | 物品详情 |
| GET | `/api/monsters` | 怪物查询 |
| GET | `/api/monsters/<idx>` | 怪物详情 |
| GET | `/api/skills/<job_id>` | 技能列表 |
| GET | `/api/notice` | 获取公告 |
| POST | `/api/notice` | 发布公告 |
| POST | `/api/gm/send-item` | 发放物品 |
| POST | `/api/gm/set-level` | 设置等级 |
| POST | `/api/gm/add-gold` | 添加金币 |
| POST | `/api/gm/kick` | 踢人 |
| POST | `/api/gm/ban` | 封禁 |
| POST | `/api/gm/unban` | 解封 |
| GET | `/api/pvf/files` | PVF 文件列表 |
| POST | `/api/pvf/load` | 加载 PVF |
| POST | `/api/pvf/upload` | 上传 PVF |
| POST | `/api/pvf/import` | 导入 PVF |
| GET | `/api/server/status` | 服务端状态 |
| GET | `/api/server/issues` | 问题诊断 |
| GET | `/api/server/config` | 服务端配置 |
| POST | `/api/server/start` | 启动服务 |
| POST | `/api/server/stop` | 停止服务 |
| GET | `/api/events` | 活动列表 |
| POST | `/api/events/<id>` | 更新活动 |

## 文件结构

```
dnf-admin-v4/
├── server.py          # Python 后端（1328 行）
├── dashboard.html     # 前端 SPA（2508 行）
├── .gitignore
└── README.md
```

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v4.8.1 | 2026-06-14 | 修复活动管理中文乱码 |
| v4.8 | 2026-06-14 | 活动管理完善（79个活动、开关、批量操作） |
| v4.7 | 2026-06-13 | 服务端监控、活动管理、解封功能 |
| v4.6 | 2026-06-13 | PVF 文件管理功能 |
| v4.5 | 2026-06-13 | 完善前端（标签页、详情弹窗） |
| v4.4 | 2026-06-13 | 修复背包物品显示 |
| v4.3 | 2026-06-13 | 修复装备显示 |
| v4.2 | 2026-06-13 | 修复怪物查询和背包物品 |
| v4.1 | 2026-06-13 | 修复背包物品名称和技能显示 |
| v4.0 | 2026-06-13 | 参考 edict 架构重构 |

## 相关仓库

- [dnf-private-deploy](https://github.com/wpp9527/dnf-private-deploy) - DNF 私有部署配置和运维脚本

## License

MIT
