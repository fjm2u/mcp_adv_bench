"""Executorファサード - 既存のインターフェースを維持"""

from typing import Dict, Any
from models.scenario import Scenario, Result
from .base import ExecutorBase
from .mcp_manager import MCPManager
from .runner import ScenarioRunner


class Executor(ExecutorBase):
    """
    シナリオ実行クラス（ファサード）
    既存のインターフェースを維持しながら、内部的にモジュール化された実装を使用
    """
    
    def __init__(self, mcp_config: Dict[str, Any], llm=None, verbose: bool = False, evaluation_llm=None):
        """
        Args:
            mcp_config: MCP設定辞書（必須）
            llm: LLMインスタンス（必須）
            verbose: 詳細出力を有効にするかどうか
            evaluation_llm: 評価用LLMインスタンス（オプション、指定しない場合はllmを使用）
        """
        if llm is None:
            raise ValueError("llm parameter is required")
        if mcp_config is None:
            raise ValueError("mcp_config parameter is required")
        
        self.mcp_config = mcp_config
        self.llm = llm
        self.evaluation_llm = evaluation_llm or llm  # 評価用LLMが指定されない場合は実行用LLMを使用
        self.verbose = verbose
        self.mcp_manager = None
        self.runner = None
        
        # MCPマネージャーをセットアップ
        self.mcp_manager = MCPManager(verbose=verbose)
        self.mcp_manager.setup(mcp_config, llm)
        
        # ランナーを初期化（評価用LLMも渡す）
        self.runner = ScenarioRunner(mcp_manager=self.mcp_manager, llm=llm, evaluation_llm=self.evaluation_llm, verbose=verbose)
    
    def execute(self, scenario: Scenario) -> Result:
        """
        シナリオを実行
        
        Args:
            scenario: 実行するシナリオ
        
        Returns:
            実行結果
        """
        return self.runner.execute(scenario)
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        if self.mcp_manager:
            self.mcp_manager.cleanup()
    
    # 後方互換性のためのメソッド
    def _call_mcp(self, scenario: Scenario) -> str:
        """
        MCPを呼び出す（後方互換性のため残す）
        
        Args:
            scenario: シナリオ
        
        Returns:
            レスポンス文字列
        """
        if self.mcp_manager.get_agent():
            try:
                # 非同期処理を同期的に実行
                response = self.mcp_manager.run_async(
                    self.mcp_manager.run_execution(scenario.user_request)
                )
                
                # レスポンスがリストの場合、最初の要素のテキストを取得
                if isinstance(response, list) and len(response) > 0:
                    if isinstance(response[0], dict) and 'text' in response[0]:
                        return response[0]['text']
                
                return str(response)
            except Exception as e:
                return f"MCP execution error: {str(e)}"
        else:
            # MCPエージェントが初期化されていない場合はエラー
            raise RuntimeError("MCP agent not initialized - cannot execute without tool support")