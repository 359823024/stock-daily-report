# -*- coding: utf-8 -*-
"""A股「近两日放量上涨」日报 —— 云端定时版
数据源：新浪财经（免费、免key）
筛选：近两日连续收涨 + 两日成交量合计 > 前6日均量1.4倍 + 今日量比>1.2
输出：HTML邮件发送到指定邮箱
"""
import os, json, time, ssl, smtplib, datetime
import requests
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import markdown

H = {'Referer': 'https://finance.sina.com.cn', 'User-Agent': 'Mozilla/5.0'}
SMTP_USER = os.environ['SMTP_USER']
SMTP_CODE = os.environ['SMTP_AUTH_CODE']
SMTP_TO = os.environ['SMTP_TO']


def fetch_market():
    rows = []
    for p in range(1, 60):
        url = ("http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
               f"Market_Center.getHQNodeData?page={p}&num=100&sort=changepercent&asc=0&node=hs_a")
        try:
            r = requests.get(url, headers=H, timeout=15)
            data = json.loads(r.text)
        except Exception:
            break
        if not data:
            break
        rows += data
        if len(data) < 100:
            break
    return rows


def get_kline(symbol, n=12):
    u = ("https://quotes.sina.cn/cn/api/jsonp_v2.php/var _=/CN_MarketDataService.getKLineData"
         f"?symbol={symbol}&scale=240&ma=no&datalen={n}")
    t = requests.get(u, headers=H, timeout=10).text
    t = t[t.find('(') + 1:t.rfind(')')]
    return json.loads(t)


def scan():
    rows = fetch_market()
    print(f"行情条数: {len(rows)}")
    cand = [r for r in rows
            if r.get('changepercent') is not None
            and float(r['changepercent']) > 2
            and float(r['trade']) > 0
            and not r['symbol'].startswith(('sh688', 'sz30', 'bj'))
            and 'ST' not in r['name']]
    cand = sorted(cand, key=lambda x: -float(x['changepercent']))[:80]
    print(f"今日涨幅>2%候选: {len(cand)}")

    res = []
    for r in cand:
        try:
            d = get_kline(r['symbol'])
            if len(d) < 9:
                continue
            c1, c2, c3 = float(d[-1]['close']), float(d[-2]['close']), float(d[-3]['close'])
            v1, v2 = float(d[-1]['volume']), float(d[-2]['volume'])
            vavg = sum(float(x['volume']) for x in d[-8:-2]) / 6
            r1, r2 = v1 / vavg, v2 / vavg
            if c1 > c2 and c2 > c3 and r1 > 1.2 and r2 > 1.0 and (v1 + v2) / (2 * vavg) > 1.4:
                res.append({
                    '代码': r['symbol'], '名称': r['name'], '最新价': c1,
                    '今日涨幅%': round(float(r['changepercent']), 2),
                    '昨日涨幅%': round((c2 / c3 - 1) * 100, 2),
                    '今日量比': round(r1, 2), '昨日量比': round(r2, 2),
                    '合计放量': round((v1 + v2) / (2 * vavg), 2),
                    '日期': d[-1]['day'],
                })
        except Exception:
            pass
        time.sleep(0.12)
    return pd.DataFrame(res)


def build_md(df):
    if df.empty:
        return ("# A股「近两日放量上涨」日报\n\n"
                f"**数据日期**：{datetime.date.today()}\n\n"
                "## 要点提示\n\n- 今日无符合「近两日连续收涨且明显放量」条件的股票。\n")
    df = df.sort_values('合计放量', ascending=False).reset_index(drop=True)
    n = len(df)
    date0 = df['日期'].iloc[0]
    L = ["# A股「近两日放量上涨」日报\n"]
    L.append(f"**数据日期**：{date0}（最近两个交易日）\n")
    L.append("**筛选条件**：最近两日连续收涨；两日成交量合计 > 前6日均量 1.4 倍；今日量比 > 1.2；剔除科创/创业/北交所/ST。\n")
    L.append(f"**命中数量**：共 **{n}** 只\n")
    L.append("## 放量强度前 15 名\n")
    L.append("| 排名 | 代码 | 名称 | 最新价 | 今日涨幅 | 昨日涨幅 | 两日合计放量 |")
    L.append("|---|---|---|---|---|---|---|")
    for i in range(min(15, n)):
        r = df.iloc[i]
        L.append(f"| {i+1} | {r['代码']} | {r['名称']} | {r['最新价']} | +{r['今日涨幅%']}% | +{r['昨日涨幅%']}% | {r['合计放量']}× |")
    L.append("\n## 全部命中明细\n")
    L.append("| 代码 | 名称 | 最新价 | 今日涨幅 | 昨日涨幅 | 今日量比 | 昨日量比 | 合计放量 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for i in range(n):
        r = df.iloc[i]
        L.append(f"| {r['代码']} | {r['名称']} | {r['最新价']} | +{r['今日涨幅%']}% | +{r['昨日涨幅%']}% | {r['今日量比']} | {r['昨日量比']} | {r['合计放量']}× |")

    tips = []
    zt = df[(df['今日涨幅%'] >= 9.8) & (df['昨日涨幅%'] >= 9.8)]
    if len(zt):
        tips.append(f"**两连板情绪股**：{'、'.join(zt['名称'].head(6))}（两日均涨停，追高风险大）")
    t = df.iloc[0]
    tips.append(f"**放量最猛**：{t['名称']}（{t['代码']}），两日放量为前期均量 {t['合计放量']} 倍")
    hl = df[(df['合计放量'] >= 1.5) & (df['合计放量'] <= 5)
            & (df['今日涨幅%'].between(1, 7)) & (df['昨日涨幅%'].between(1, 7))].head(5)
    if len(hl):
        tips.append("**量价配合较健康**：" + "、".join(f"{r['名称']}(+{r['今日涨幅%']}%)" for _, r in hl.iterrows()))
    sg = df[(df['今日量比'] >= 2.5) & (df['今日涨幅%'] >= 5)]
    if len(sg):
        tips.append(f"**今日突发放量拉升**：{'、'.join(sg['名称'].head(5))}（谨防一日游）")
    tips.append(f"**结构特征**：{n} 只中今日涨停 {len(df[df['今日涨幅%'] >= 9.8])} 只，放量超3倍 {len(df[df['合计放量'] >= 3])} 只")

    L.append("\n## 要点提示\n")
    for x in tips:
        L.append(f"- {x}")
    L.append("\n> 本报告由量化规则自动筛选生成，仅为数据统计，不构成任何投资建议。\n")
    return "\n".join(L)


def send(md_text, subject):
    body = markdown.markdown(md_text, extensions=['tables'])
    html = f"""<html><body style="font-family:Microsoft YaHei,Arial;max-width:860px;">
<style>table{{border-collapse:collapse;font-size:14px;}}th,td{{border:1px solid #ccc;padding:6px 10px;}}
th{{background:#f0f0f0;}}</style>{body}
<p style="color:#999;font-size:12px;">本邮件由云端定时任务自动发送，仅为数据统计，不构成投资建议。</p>
</body></html>"""
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = SMTP_TO
    msg['Subject'] = Header(subject, 'utf-8')
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.qq.com', 465, context=ctx) as s:
        s.login(SMTP_USER, SMTP_CODE)
        s.sendmail(SMTP_USER, [SMTP_TO], msg.as_string())
    print(f"邮件已发送至 {SMTP_TO}")


if __name__ == '__main__':
    df = scan()
    md_text = build_md(df)
    print(md_text[:500])
    date0 = df['日期'].iloc[0] if not df.empty else str(datetime.date.today())
    send(md_text, f"A股「近两日放量上涨」日报 {date0}（{len(df)}只）")
