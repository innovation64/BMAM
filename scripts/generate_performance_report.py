#!/usr/bin/env python3
"""
性能测试报告生成器
从测试结果生成 HTML 仪表盘和趋势分析
"""

import json
import os
import glob
from datetime import datetime
from typing import List, Dict, Any
import sys


class PerformanceReportGenerator:
    """性能报告生成器"""

    def __init__(self, reports_dir: str = "benchmark_reports"):
        self.reports_dir = reports_dir
        self.reports = []

    def load_reports(self) -> List[Dict[str, Any]]:
        """加载所有测试报告"""
        json_files = glob.glob(f"{self.reports_dir}/benchmark_*.json")

        for json_file in sorted(json_files, reverse=True)[:10]:  # 最近10个报告
            try:
                with open(json_file, 'r') as f:
                    report = json.load(f)
                    report['file'] = json_file
                    self.reports.append(report)
            except Exception as e:
                print(f"⚠️  无法加载报告 {json_file}: {e}")

        return self.reports

    def generate_html_dashboard(self, output_file: str = None) -> str:
        """生成 HTML 仪表盘"""
        if not output_file:
            output_file = f"{self.reports_dir}/dashboard.html"

        if not self.reports:
            self.load_reports()

        latest_report = self.reports[0] if self.reports else None

        html = self._generate_html_template(latest_report, self.reports)

        with open(output_file, 'w') as f:
            f.write(html)

        print(f"✅ HTML 仪表盘已生成: {output_file}")
        return output_file

    def _generate_html_template(self, latest: Dict[str, Any], history: List[Dict[str, Any]]) -> str:
        """生成 HTML 模板"""

        # 提取历史数据用于趋势图
        dates = []
        pass_rates = []
        totals = []

        for report in reversed(history[-7:]):  # 最近7次
            dates.append(report.get('timestamp', ''))
            pass_rates.append(report.get('summary', {}).get('pass_rate', 0))
            totals.append(report.get('summary', {}).get('total', 0))

        latest_summary = latest.get('summary', {}) if latest else {}
        latest_status = latest.get('status', 'UNKNOWN') if latest else 'NO DATA'
        latest_date = latest.get('date', 'N/A') if latest else 'N/A'

        status_color = {
            'PASS': '#28a745',
            'FAIL': '#dc3545',
            'UNKNOWN': '#6c757d',
            'NO DATA': '#6c757d'
        }.get(latest_status, '#6c757d')

        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BMAM Performance Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        .header {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }}

        h1 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}

        .subtitle {{
            color: #666;
            font-size: 1.1em;
        }}

        .status-badge {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            color: white;
            font-weight: bold;
            margin-top: 15px;
            background: {status_color};
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }}

        .card h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}

        .metric {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-radius: 10px;
            transition: transform 0.2s;
        }}

        .metric:hover {{
            transform: translateX(5px);
        }}

        .metric-label {{
            font-weight: 600;
            color: #555;
        }}

        .metric-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }}

        .metric-value.success {{
            color: #28a745;
        }}

        .metric-value.warning {{
            color: #ffc107;
        }}

        .metric-value.danger {{
            color: #dc3545;
        }}

        .chart-container {{
            position: relative;
            height: 300px;
            margin-top: 20px;
        }}

        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            padding: 20px;
        }}

        .timestamp {{
            color: #999;
            font-size: 0.9em;
            margin-top: 10px;
        }}

        .large-card {{
            grid-column: 1 / -1;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}

        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}

        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
        }}

        tr:hover {{
            background: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 BMAM Performance Dashboard</h1>
            <p class="subtitle">Brain-Inspired Multi-Agent Memory System - Performance & Robustness Monitor</p>
            <span class="status-badge">Status: {latest_status}</span>
            <p class="timestamp">Last Update: {latest_date}</p>
        </div>

        <div class="grid">
            <div class="card">
                <h2>📊 Latest Results</h2>
                <div class="metric">
                    <span class="metric-label">Total Tests</span>
                    <span class="metric-value">{latest_summary.get('total', 0)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Passed</span>
                    <span class="metric-value success">{latest_summary.get('passed', 0)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Failed</span>
                    <span class="metric-value danger">{latest_summary.get('failed', 0)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Timeout</span>
                    <span class="metric-value warning">{latest_summary.get('timeout', 0)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Pass Rate</span>
                    <span class="metric-value {'success' if latest_summary.get('pass_rate', 0) >= 80 else 'warning' if latest_summary.get('pass_rate', 0) >= 60 else 'danger'}">{latest_summary.get('pass_rate', 0)}%</span>
                </div>
            </div>

            <div class="card">
                <h2>🎯 Performance Trends</h2>
                <div class="chart-container">
                    <canvas id="trendChart"></canvas>
                </div>
            </div>
        </div>

        <div class="grid">
            <div class="card large-card">
                <h2>📈 Test History (Last 7 Runs)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Total</th>
                            <th>Passed</th>
                            <th>Failed</th>
                            <th>Timeout</th>
                            <th>Pass Rate</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
"""

        # 添加历史记录
        for report in history[:7]:
            summary = report.get('summary', {})
            status = report.get('status', 'UNKNOWN')
            date = report.get('date', report.get('timestamp', 'N/A'))

            status_emoji = '✅' if status == 'PASS' else '❌' if status == 'FAIL' else '⚠️'

            html += f"""
                        <tr>
                            <td>{date[:19] if date != 'N/A' else 'N/A'}</td>
                            <td>{summary.get('total', 0)}</td>
                            <td>{summary.get('passed', 0)}</td>
                            <td>{summary.get('failed', 0)}</td>
                            <td>{summary.get('timeout', 0)}</td>
                            <td>{summary.get('pass_rate', 0)}%</td>
                            <td>{status_emoji} {status}</td>
                        </tr>
"""

        html += """
                    </tbody>
                </table>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>🔍 Test Categories</h2>
                <div class="metric">
                    <span class="metric-label">✅ Functional Tests</span>
                    <span class="metric-value">Fast</span>
                </div>
                <div class="metric">
                    <span class="metric-label">💪 Stress Tests</span>
                    <span class="metric-value">Batch/Long Session/Capacity</span>
                </div>
                <div class="metric">
                    <span class="metric-label">🔥 Fault Injection</span>
                    <span class="metric-value">DB/API/Concurrency</span>
                </div>
                <div class="metric">
                    <span class="metric-label">🎯 LoCoMo Benchmark</span>
                    <span class="metric-value">Optional</span>
                </div>
            </div>

            <div class="card">
                <h2>⚙️ Environment Info</h2>
"""

        if latest:
            env = latest.get('environment', {})
            html += f"""
                <div class="metric">
                    <span class="metric-label">OS</span>
                    <span class="metric-value">{env.get('os', 'N/A')}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Python</span>
                    <span class="metric-value">{env.get('python_version', 'N/A')}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Hostname</span>
                    <span class="metric-value">{env.get('hostname', 'N/A')}</span>
                </div>
"""

        html += """
            </div>
        </div>

        <div class="footer">
            <p>© 2025 BMAM Project - Brain-Inspired Multi-Agent Memory System</p>
            <p style="margin-top: 10px;">Generated by Performance Report Generator</p>
        </div>
    </div>

    <script>
        // 趋势图
        const ctx = document.getElementById('trendChart').getContext('2d');
        const trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: """ + json.dumps(dates) + """,
                datasets: [{
                    label: 'Pass Rate (%)',
                    data: """ + json.dumps(pass_rates) + """,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""

        return html

    def generate_summary_report(self) -> Dict[str, Any]:
        """生成摘要报告"""
        if not self.reports:
            self.load_reports()

        if not self.reports:
            return {'error': 'No reports found'}

        latest = self.reports[0]
        summary = latest.get('summary', {})

        # 计算趋势
        if len(self.reports) >= 2:
            prev_report = self.reports[1]
            prev_summary = prev_report.get('summary', {})

            trend = {
                'pass_rate_change': summary.get('pass_rate', 0) - prev_summary.get('pass_rate', 0),
                'total_change': summary.get('total', 0) - prev_summary.get('total', 0)
            }
        else:
            trend = {'pass_rate_change': 0, 'total_change': 0}

        return {
            'latest_status': latest.get('status', 'UNKNOWN'),
            'latest_pass_rate': summary.get('pass_rate', 0),
            'total_reports': len(self.reports),
            'trend': trend,
            'timestamp': latest.get('timestamp', 'N/A')
        }


def main():
    """主函数"""
    print("=" * 50)
    print("BMAM Performance Report Generator")
    print("=" * 50)
    print()

    generator = PerformanceReportGenerator()

    # 加载报告
    print("加载测试报告...")
    reports = generator.load_reports()
    print(f"✓ 已加载 {len(reports)} 个报告")
    print()

    # 生成 HTML 仪表盘
    print("生成 HTML 仪表盘...")
    dashboard_file = generator.generate_html_dashboard()
    print()

    # 生成摘要
    print("生成摘要报告...")
    summary = generator.generate_summary_report()

    print("=" * 50)
    print("摘要信息:")
    print(f"  最新状态: {summary.get('latest_status', 'UNKNOWN')}")
    print(f"  通过率: {summary.get('latest_pass_rate', 0)}%")
    print(f"  总报告数: {summary.get('total_reports', 0)}")

    trend = summary.get('trend', {})
    pass_rate_change = trend.get('pass_rate_change', 0)
    if pass_rate_change > 0:
        print(f"  趋势: ↗ +{pass_rate_change}%")
    elif pass_rate_change < 0:
        print(f"  趋势: ↘ {pass_rate_change}%")
    else:
        print(f"  趋势: → 持平")

    print("=" * 50)
    print()
    print(f"✅ 报告生成完成！")
    print(f"   查看仪表盘: {dashboard_file}")


if __name__ == "__main__":
    main()
