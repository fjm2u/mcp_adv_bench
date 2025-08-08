"""実行履歴管理モジュール"""

import time
from typing import List, Dict, Any, Optional
from models.scenario import Result


class HistoryManager:
    """実行履歴を管理するクラス"""
    
    @staticmethod
    def record_user_request(result: Result, request: str, timestamp: Optional[float] = None):
        """
        ユーザーリクエストを記録
        
        Args:
            result: 結果オブジェクト
            request: ユーザーリクエスト
            timestamp: タイムスタンプ（オプション）
        """
        if timestamp is None:
            timestamp = time.time()
        
        result.add_interaction(
            text=request,
            timestamp=timestamp,
            interaction_type="user"
        )
    
    @staticmethod
    def record_tool_call(result: Result, tool_name: str, tool_input: Any, timestamp: Optional[float] = None):
        """
        ツール呼び出しを記録
        
        Args:
            result: 結果オブジェクト
            tool_name: ツール名
            tool_input: ツール入力
            timestamp: タイムスタンプ（オプション）
        """
        if timestamp is None:
            timestamp = time.time()
        
        tool_request = f"Tool: {tool_name}"
        if tool_input:
            tool_request += f"\nInput: {tool_input}"
        
        result.add_interaction(
            text=tool_request,
            timestamp=timestamp,
            interaction_type="tool_call"
        )
    
    @staticmethod
    def record_tool_response(result: Result, response: str, timestamp: Optional[float] = None):
        """
        ツールレスポンスを記録
        
        Args:
            result: 結果オブジェクト
            response: ツールレスポンス
            timestamp: タイムスタンプ（オプション）
        """
        if timestamp is None:
            timestamp = time.time()
        
        result.add_interaction(
            text=response,
            timestamp=timestamp,
            interaction_type="tool_response"
        )
    
    @staticmethod
    def record_ai_response(result: Result, response: str, timestamp: Optional[float] = None):
        """
        AI応答を記録
        
        Args:
            result: 結果オブジェクト
            response: AI応答
            timestamp: タイムスタンプ（オプション）
        """
        if timestamp is None:
            timestamp = time.time()
        
        result.add_interaction(
            text=response,
            timestamp=timestamp,
            interaction_type="ai_response"
        )
    
    @staticmethod
    def record_error(result: Result, error_msg: str, timestamp: Optional[float] = None):
        """
        エラーを記録
        
        Args:
            result: 結果オブジェクト
            error_msg: エラーメッセージ
            timestamp: タイムスタンプ（オプション）
        """
        if timestamp is None:
            timestamp = time.time()
        
        result.set_error(error_msg)
        result.add_interaction(
            text=error_msg,
            timestamp=timestamp,
            interaction_type="ai_response"
        )