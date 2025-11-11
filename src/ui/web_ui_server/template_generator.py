"""
Template Generator Mixin
HTML模板生成器 - 负责生成和提供HTML模板
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TemplateGeneratorMixin:
    """HTML模板生成和管理"""

    def get_template_path(self) -> Path:
        """获取模板文件路径"""
        return Path(__file__).parent / 'static' / 'index.html'

    def ensure_template_exists(self) -> bool:
        """确保模板文件存在"""
        template_path = self.get_template_path()

        if not template_path.exists():
            logger.warning(f"Template file not found at {template_path}")
            # Generate default HTML if not exists
            html_content = self.generate_default_html()
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_text(html_content)
            logger.info(f"Generated default template at {template_path}")
            return True

        return True

    def generate_default_html(self) -> str:
        """
        生成默认HTML页面

        注意: 实际的HTML模板应该位于 static/index.html
        此方法仅用于在模板文件缺失时生成最小可用版本
        """
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BMAM Voice Anime UI</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
            color: white;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        h1 {
            margin-bottom: 20px;
        }
        p {
            margin-bottom: 10px;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>BMAM Voice UI</h1>
        <p>Template file is missing.</p>
        <p>Expected location: static/index.html</p>
        <p>Please ensure the template file exists and refresh the page.</p>
    </div>
</body>
</html>'''
