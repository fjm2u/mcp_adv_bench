"""MCP接続・管理モジュール"""

import os
import asyncio
import threading
from typing import Dict, Any
from mcp_use import MCPAgent, MCPClient
from .base import MCPManagerInterface


class MCPManager(MCPManagerInterface):
    """MCP接続と管理を担当するクラス"""
    
    def __init__(self, verbose: bool = False):
        """初期化"""
        self.mcp_agent = None
        self.loop = None
        self.loop_thread = None
        self.llm = None
        self.verbose = verbose
    
    def setup(self, mcp_config: Dict[str, Any], llm: Any):
        """
        MCPエージェントをセットアップ
        
        Args:
            mcp_config: MCP設定辞書
            llm: LLMインスタンス
        """
        try:
            # テレメトリを無効化
            os.environ["MCP_USE_TELEMETRY"] = "false"
            os.environ["MCP_USE_ANONYMIZED_TELEMETRY"] = "false"
            
            # MCPクライアントとエージェントを作成
            client = MCPClient.from_dict(mcp_config)
            self.mcp_agent = MCPAgent(llm=llm, client=client, max_steps=10)
            self.llm = llm
            
            # 専用のイベントループとスレッドを作成
            self.loop = asyncio.new_event_loop()
            self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self.loop_thread.start()
            
            if self.verbose:
                print("MCP Agent initialized successfully")
        except Exception as e:
            raise Exception(f"Failed to setup MCP agent: {e}")
    
    def _run_event_loop(self):
        """イベントループを実行するスレッド"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def run_async(self, coro):
        """
        非同期コルーチンを同期的に実行
        
        Args:
            coro: 実行するコルーチン
        
        Returns:
            コルーチンの実行結果
        """
        if self.loop is None:
            # フォールバック: 新しいループで実行
            return asyncio.run(coro)
        else:
            # 既存のループにタスクを送信して結果を待つ
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            return future.result()
    
    def cleanup(self):
        """MCPリソースをクリーンアップ"""
        if self.loop and self.loop_thread:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.loop_thread.join(timeout=5)
            self.loop.close()
            self.loop = None
            self.loop_thread = None
            self.mcp_agent = None
    
    def get_agent(self):
        """
        MCPエージェントを取得
        
        Returns:
            MCPエージェントインスタンス
        """
        return self.mcp_agent
    
    async def stream_execution(self, request: str):
        """
        MCPエージェントのストリーミング実行
        
        Args:
            request: ユーザーリクエスト
        
        Yields:
            実行の各ステップ
        """
        if not self.mcp_agent:
            raise ValueError("MCP agent not initialized")
        
        if self.verbose:
            print(f"[MCP] Executing request: {request}")
        
        async for item in self.mcp_agent.stream(request):
            if self.verbose and isinstance(item, dict):
                if 'type' in item:
                    print(f"[MCP] Step type: {item['type']}")
                if 'tool_call' in item:
                    print(f"[MCP] Tool call: {item['tool_call'].get('name', 'Unknown')}")
            yield item
    
    async def run_execution(self, request: str):
        """
        MCPエージェントの通常実行
        
        Args:
            request: ユーザーリクエスト
        
        Returns:
            実行結果
        """
        if not self.mcp_agent:
            raise ValueError("MCP agent not initialized")
        
        if self.verbose:
            print(f"[MCP] Executing request: {request}")
        
        result = await self.mcp_agent.run(request)
        
        if self.verbose:
            print(f"[MCP] Execution completed")
        
        return result