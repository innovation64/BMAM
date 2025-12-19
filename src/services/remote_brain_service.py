"""
Remote Brain Service - Client Side
远程脑服务 - 客户端实现

功能:
1. 通过 HTTP/WebSocket 连接远程 Brain Server
2. 实现与 BrainService 相同的接口
3. 允许 UI 独立部署
"""

import logging
import aiohttp
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from .brain_service import BrainService, ProcessingResponseDTO, SystemStatusDTO, MemoryRegionStatsDTO

logger = logging.getLogger(__name__)

class RemoteBrainService:
    """
    Remote Brain Service Client
    
    Connects to a remote BMAM instance.
    """

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
            })
        return self.session

    async def process_input(self, text: str) -> ProcessingResponseDTO:
        """远程处理用户输入"""
        session = await self._get_session()
        async with session.post(f"{self.base_url}/api/process", json={"text": text}) as resp:
            data = await resp.json()
            return ProcessingResponseDTO(**data)

    async def get_system_status(self) -> SystemStatusDTO:
        """获取远程系统状态"""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/api/status") as resp:
            data = await resp.json()
            return SystemStatusDTO(**data)

    async def get_memory_stats(self) -> List[MemoryRegionStatsDTO]:
        """获取远程记忆统计"""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/api/memory/stats") as resp:
            data = await resp.json()
            return [MemoryRegionStatsDTO(**item) for item in data]

    async def export_memory(self, output_dir: Any, name: str, description: str) -> Dict[str, Any]:
        """
        请求远程导出记忆归档

        Args:
            output_dir: 本地输出目录
            name: 归档名称
            description: 归档描述

        Returns:
            导出结果，包含归档路径和统计信息
        """
        from pathlib import Path
        import aiofiles

        session = await self._get_session()

        # 请求远程服务器生成归档
        async with session.post(
            f"{self.base_url}/api/memory/export",
            json={"name": name, "description": description}
        ) as resp:
            if resp.status != 200:
                error_data = await resp.json()
                return {"success": False, "error": error_data.get("error", "Export failed")}

            # 下载归档文件
            output_path = Path(output_dir) / f"{name}.bma"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(output_path, 'wb') as f:
                async for chunk in resp.content.iter_chunked(8192):
                    await f.write(chunk)

            return {
                "success": True,
                "archive_path": str(output_path),
                "message": f"Archive downloaded to {output_path}"
            }

    async def import_memory(self, archive_path: Any) -> Dict[str, Any]:
        """
        请求远程导入记忆归档

        Args:
            archive_path: 本地归档文件路径

        Returns:
            导入结果，包含统计信息
        """
        from pathlib import Path
        import aiofiles

        archive_path = Path(archive_path)
        if not archive_path.exists():
            return {"success": False, "error": f"Archive not found: {archive_path}"}

        session = await self._get_session()

        # 上传归档文件
        data = aiohttp.FormData()
        async with aiofiles.open(archive_path, 'rb') as f:
            file_content = await f.read()
            data.add_field(
                'archive',
                file_content,
                filename=archive_path.name,
                content_type='application/octet-stream'
            )

        async with session.post(
            f"{self.base_url}/api/memory/import",
            data=data
        ) as resp:
            result = await resp.json()
            if resp.status != 200:
                return {"success": False, "error": result.get("error", "Import failed")}

            return {
                "success": True,
                "imported_count": result.get("imported_count", 0),
                "message": result.get("message", "Import completed")
            }

    async def close(self):
        if self.session:
            await self.session.close()
