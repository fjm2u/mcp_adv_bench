"""シナリオ実行制御モジュール"""

import time
from typing import Any
from models.scenario import Scenario, Result
from .mcp_manager import MCPManager
from .history import HistoryManager
from .evaluator import ScenarioEvaluator


class ScenarioRunner:
    """シナリオ実行を制御するクラス"""
    
    def __init__(self, mcp_manager: MCPManager, llm: Any = None, evaluation_llm: Any = None, verbose: bool = False, config_manager: Any = None):
        """
        初期化
        
        Args:
            mcp_manager: MCP管理インスタンス（必須）
            llm: LLMインスタンス
            evaluation_llm: 評価用LLMインスタンス（オプション）
            verbose: 詳細出力を有効にするかどうか
            config_manager: 設定管理インスタンス（オプション）
        """
        self.mcp_manager = mcp_manager
        self.llm = llm
        self.evaluation_llm = evaluation_llm or llm  # 評価用LLMが指定されない場合は実行用LLMを使用
        self.verbose = verbose
        self.config_manager = config_manager
        self.history = HistoryManager()
        self.evaluator = ScenarioEvaluator(verbose=verbose, config_manager=config_manager)
    
    def _evaluate_with_handler(self, scenario: Scenario, result: Result, final_answer: str) -> bool:
        """
        評価を実行し、エラーハンドリングを行う共通メソッド
        
        Args:
            scenario: 評価対象のシナリオ
            result: 結果オブジェクト
            final_answer: 評価に使用する最終回答
            
        Returns:
            bool: 評価が成功したかどうか
        """
        try:
            success, evaluation_details = self.evaluator.evaluate_success(scenario, final_answer, self.evaluation_llm)
            result.evaluation_details = evaluation_details
            return success
        except Exception as e:
            if self.verbose:
                print(f"  Evaluation failed: {e}")
            result.error = True
            result.error_message = f"Evaluation error: {str(e)}"
            result.evaluation_details = {
                "evaluation_type": "error",
                "error": str(e)
            }
            return False
    
    def execute(self, scenario: Scenario) -> Result:
        """
        シナリオを実行
        
        Args:
            scenario: 実行するシナリオ
        
        Returns:
            実行結果
        """
        if self.verbose:
            print(f"\n  Executing scenario: {scenario.name}")
            print(f"  User request: {scenario.user_request}")
            if scenario.attack_case:
                print(f"  Attack goal: {scenario.attack_goal}")
        
        start_time = time.time()
        
        # 結果オブジェクトを作成
        result = Result(
            name=scenario.name,
            attack_case=scenario.attack_case
        )
        
        # 実行（MCPを使用）
        if self.mcp_manager.get_agent():
            self._execute_with_mcp(scenario, result)
        else:
            # MCPエージェントが初期化されていない場合はエラー
            result.error = True
            result.error_message = "MCP agent not initialized"
            if self.verbose:
                print(f"    ERROR: MCP agent not initialized")
        
        # ツール使用のチェック
        if not result.has_tool_calls():
            # ツールが一度も使われていない場合はエラー
            if self.verbose:
                print(f"  Error: No tool calls found in scenario '{scenario.name}'")
            result.error = True
            result.error_message = "No tool calls detected - Agent did not use any tools"
            success = False
            result.evaluation_details = {
                "evaluation_type": "error",
                "error": "No tool usage detected"
            }
        # Final Answerの取得と評価
        else:
            # Final Answerを取得（ない場合は最終レスポンス全体を使用）
            final_answer = result.get_final_answer()
            if not final_answer:
                if self.verbose:
                    print(f"  Warning: No Final Answer found for scenario '{scenario.name}', using full response")
                final_answer = result.get_final_response()
                result.final_answer = final_answer
            
            # 評価を実行
            success = self._evaluate_with_handler(scenario, result, final_answer)
        
        execution_time = time.time() - start_time
        
        # 最終結果を更新
        result.meets_expected_behavior = success
        result.execution_time = execution_time
        
        return result
    
    def _execute_with_mcp(self, scenario: Scenario, result: Result):
        """
        MCPを使用してシナリオを実行
        
        Args:
            scenario: シナリオ
            result: 結果オブジェクト
        """
        try:
            async def run_with_history():
                final_response = ""
                
                # ユーザーリクエストを記録
                self.history.record_user_request(result, scenario.user_request)
                
                # ストリーミング実行で中間ステップを収集
                async for item in self.mcp_manager.stream_execution(scenario.user_request):
                    # ステップ（ツール呼び出し）の場合
                    if isinstance(item, tuple) and len(item) == 2:
                        action, observation = item
                        
                        if hasattr(action, 'tool'):
                            # ツール呼び出しを記録
                            tool_input = getattr(action, 'tool_input', None)
                            self.history.record_tool_call(result, action.tool, tool_input)
                            
                            if self.verbose:
                                print(f"    Tool: {action.tool}")
                                if tool_input:
                                    print(f"    Input: {tool_input}")
                            
                            # ツールレスポンスを記録
                            self.history.record_tool_response(result, observation)
                            
                            if self.verbose:
                                print(f"    Response: {observation[:200]}..." if len(str(observation)) > 200 else f"    Response: {observation}")
                    
                    # 最終結果の場合
                    elif isinstance(item, str):
                        final_response = item
                    elif isinstance(item, list):
                        # LangChainメッセージ形式の処理
                        if item and isinstance(item[0], dict) and 'text' in item[0]:
                            final_response = item[0]['text']
                        else:
                            final_response = str(item)
                    else:
                        final_response = str(item) if item else ""
                
                # AI応答を記録
                if final_response:
                    self.history.record_ai_response(result, final_response)
                    if self.verbose:
                        print(f"    Final response: {final_response[:200]}..." if len(final_response) > 200 else f"    Final response: {final_response}")
            
            # 非同期処理を同期的に実行
            self.mcp_manager.run_async(run_with_history())
            
        except Exception as e:
            error_msg = f"MCP execution error: {str(e)}"
            self.history.record_error(result, error_msg)
            if self.verbose:
                print(f"    ERROR: {error_msg}")
    
