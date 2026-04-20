# 炸金花在线卡牌游戏

多人在线炸金花卡牌对战游戏，支持实时WebSocket通信。

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动服务器
```bash
python -c "from backend.app import run_server; run_server()"
```
或双击 `start.bat`

### 3. 打开浏览器
访问 http://localhost:5002

## 游戏规则

### 基本规则
- 每局使用标准52张扑克牌(无大小王)
- 每位玩家发3张牌
- 初始积分: 100点

### 玩家操作
| 操作 | 条件 | 效果 |
|------|------|------|
| 闷牌 | 未看牌 | 投入1/2/4积分 |
| 看牌 | 未看牌 | 查看自己手牌 |
| 跟牌 | 已看牌 | 投入2X底注积分 |
| 弃牌 | 任意时刻 | 放弃本局 |
| 开牌 | 任意时刻 | 与对手比牌 |

### 牌型大小(从大到小)
1. 豹子 - 三张相同
2. 同花顺 - 同花色顺子
3. 同花 - 同花色非顺子
4. 顺子 - 不同花色顺子
5. 对子 - 两张相同
6. 单张 - 无组合

## 技术栈
- 后端: Python + Flask + Flask-SocketIO
- 前端: HTML/CSS/JavaScript
- 通信: WebSocket (Socket.IO)
