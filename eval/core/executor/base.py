"""Executor基底クラスとインターフェース定義"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from models.scenario import Scenario, Result


class ExecutorBase(ABC):
    """
    Executor基底クラス
    
    シナリオの実行と評価を管理する基底クラス。
    実行用LLMと評価用LLMを分離して使用可能。
    """
    
    @abstractmethod
    def execute(self, scenario: Scenario) -> Result:
        """
        シナリオを実行
        
        Args:
            scenario: 実行するシナリオ
        
        Returns:
            実行結果（final_answerフィールドを含む）
        """
        pass
    
    @abstractmethod
    def cleanup(self):
        """リソースをクリーンアップ"""
        pass


class MCPManagerInterface(ABC):
    """MCP管理インターフェース"""
    
    @abstractmethod
    def setup(self, mcp_config: Dict[str, Any], llm: Any):
        """MCPエージェントをセットアップ"""
        pass
    
    @abstractmethod
    def run_async(self, coro):
        """非同期コルーチンを同期的に実行"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """MCPリソースをクリーンアップ"""
        pass
    
    @abstractmethod
    def get_agent(self):
        """MCPエージェントを取得"""
        pass


class EvaluatorInterface(ABC):
    """評価インターフェース"""
    
    @abstractmethod
    def evaluate_success(self, scenario: Scenario, response: str, llm: Any) -> bool:
        """
        成功/失敗を判定
        
        Args:
            scenario: シナリオ
            response: 実際のレスポンス
            llm: LLMインスタンス
        
        Returns:
            成功の場合True
        """
        pass