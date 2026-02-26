# E-commerce Domain Knowledge Base
# 适用范围：所有电商类project
# 最后更新：2026-02-25

## 行业基本判断框架

### 选品判断
- 看趋势早于看销量：销量是滞后指标，趋势是领先指标
- 合规优先：NMPA注册、中文标签、进口文件——缺一不可
- 供应链稳定性比利润率更重要：断货的成本远高于低利润

### 定价判断
- 毛利率低于30%的产品需要特别理由才能引入
- 季节性产品的定价要提前考虑清仓成本
- 折扣销售必须记录原价和折扣原因，否则利润数据失真

### 库存判断
- 有效期管理是K-Beauty的核心风险点
- 滞销信号：30天无销售记录的SKU需要主动干预
- 安全库存 = 平均周销量 × 补货周期 × 1.5

### 客户判断
- 复购率是健康度的核心指标
- 客户投诉必须在24小时内响应，否则影响口碑传播

## 踩过的坑
（随项目积累持续更新）

## 成功模式
（随项目积累持续更新）

## 跨境电商架构判断（迁移自旧架构 2026-02-25）

### 数据流设计
- 跨境服务器之间网络不通是常态，不是故障
- 数据中转方案：选择 Slack 而非自建消息队列，因为 Slack 天然支持 Bot Token 认证、消息持久化、频道隔离
- 数据采集应由靠近数据源的 Agent 执行（中国节点采集中国数据），而非远程调用

### Agent 架构决策
- [2026-02-25] Slack Bot 作为 Manager Agent 部署在 GCP：需要异步通信通道连接美国和中国系统
- [2026-02-25] 采用 3-layer 架构（Manager / Dev / Business Agents）：受 Elvis OpenClaw 架构启发，Orchestrator 持有上下文，agents 接收精准 prompt
- [2026-02-25] Agent 记忆和 Project 上下文分离：Agent 身份/规则稳定，Project 上下文频繁变化，分离后可支持多 project 扩展

## 开发规范（适用于电商 Dev EMP_0005）

### 代码风格
- Python: Black (line-length=100, py311), snake_case, type hints on public functions
- JavaScript: Prettier (printWidth=100, singleQuote), const by default, PascalCase for components
- SQL: 关键字大写（SELECT, WHERE, JOIN）

### Git 工作流
- Commit format: type(scope): description (feat/fix/refactor/style/docs/perf/chore/test)
- Branch format: type/short-description
- 每个完成的任务必须提交，保持 atomic commits
- 禁止 force-push、禁止提交 .env 和数据库文件

### 部署协议
1. 本地测试 → 2. SCP 文件到服务器 → 3. 安装依赖 → 4. 重启服务 → 5. 线上验证 → 6. 标记完成
