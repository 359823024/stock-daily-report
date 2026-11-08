# A股放量上涨日报（云端定时版）

每天由 GitHub 服务器定时运行，自动生成日报并发送到邮箱。无需本地电脑开机、无需任何对话。

## 部署步骤（一次性，约 3 分钟）

1. 在 GitHub 新建一个**私有仓库**（如 `stock-daily-report`）
2. 把本目录全部文件推送到该仓库
3. 仓库 → Settings → Secrets and variables → Actions → 新建 3 个 Secret：
   - `SMTP_USER`：3056098651@qq.com
   - `SMTP_AUTH_CODE`：QQ 邮箱 SMTP 授权码
   - `SMTP_TO`：3056098651@qq.com
4. 仓库 → Actions 标签页 → 启用 workflows
5. 完成后每天北京时间 15:35 自动发送（工作流 cron: `35 7 * * 1-5` UTC）

## 手动测试

Actions 页面 → 选择「A股放量上涨日报」→ Run workflow

## 说明

- 数据源：新浪财经接口（免费、无需 key）
- 筛选规则：近两日连续收涨 + 两日成交量合计 > 前6日均量1.4倍 + 今日量比>1.2，剔除科创/创业/北交所/ST
- 注意：GitHub Actions 定时任务在仓库 60 天无提交活动后会自动暂停，届时点一下启用即可
