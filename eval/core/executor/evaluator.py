"""シナリオ評価モジュール"""

from typing import Any, Optional
from models.scenario import Scenario
from .base import EvaluatorInterface
from pydantic import BaseModel, Field

class EvaluationResult(BaseModel):
    """評価結果の構造化モデル"""
    reason: str = Field(description="評価理由の詳細な説明")
    is_success: bool = Field(description="攻撃が成功したか、または期待通りの動作であるか")
    confidence: float = Field(description="判定の確信度(0.0〜1.0)", ge=0.0, le=1.0)



class ScenarioEvaluator(EvaluatorInterface):
    """シナリオの成功/失敗を評価するクラス"""
    
    def __init__(self, verbose: bool = False, config_manager: Optional[Any] = None):
        """
        初期化
        
        Args:
            verbose: 詳細出力を有効にするかどうか
            config_manager: 設定管理インスタンス（オプション）
        """
        self.verbose = verbose
        self.config_manager = config_manager
        self.last_evaluation_reason = ""  # 最後の評価理由を保存
        self.last_evaluation_error = None  # 最後の評価エラーを保存
    
    def evaluate_success(self, scenario: Scenario, response: str, llm: Any) -> tuple[bool, dict]:
        """
        LLMを使用して成功/失敗を判定
        
        Args:
            scenario: シナリオ
            response: 実際のレスポンス
            llm: LLMインスタンス
        
        Returns:
            (成功の場合True, 評価詳細の辞書)
        
        Raises:
            ValueError: 判定が正しく行えなかった場合
        """
        self.last_evaluation_error = None
        
        try:
            # 攻撃シナリオの場合
            if scenario.attack_case and scenario.attack_success_criteria:
                success, eval_result = self._evaluate_attack_scenario(scenario, response, llm)
                prompt = self._build_attack_evaluation_prompt(scenario, response)
                details = {
                    "evaluation_type": "attack_scenario",
                    "reason": eval_result.reason,
                    "is_success": eval_result.is_success,
                    "confidence": eval_result.confidence,
                    "prompt": prompt,
                    "expected_behavior": scenario.expected_behavior,
                    "attack_goal": scenario.attack_goal,
                    "attack_success_criteria": scenario.attack_success_criteria
                }
                return success, details
            
            # 制御シナリオの場合
            if not scenario.attack_case:
                success, eval_result = self._evaluate_control_scenario(scenario, response, llm)
                prompt = self._build_control_evaluation_prompt(scenario, response)
                details = {
                    "evaluation_type": "control_scenario",
                    "reason": eval_result.reason,
                    "is_success": eval_result.is_success,
                    "confidence": eval_result.confidence,
                    "prompt": prompt,
                    "expected_behavior": scenario.expected_behavior
                }
                return success, details
            
            # どちらでもない場合はエラー
            error_msg = f"シナリオ '{scenario.name}' のタイプが不明です"
            self.last_evaluation_error = error_msg
            raise ValueError(error_msg)
            
        except Exception as e:
            self.last_evaluation_error = str(e)
            if self.verbose:
                print(f"  評価エラー: {e}")
            raise
    
    def _evaluate_attack_scenario(self, scenario: Scenario, response: str, llm: Any) -> tuple[bool, EvaluationResult]:
        """
        攻撃シナリオを評価
        
        Args:
            scenario: シナリオ
            response: 実際のレスポンス
            llm: LLMインスタンス
        
        Returns:
            (攻撃がブロックされた場合True, 評価結果)
        """

        evaluation_prompt = self._build_attack_evaluation_prompt(scenario, response)

        if self.verbose:
            print("------ Evaluating attack scenario ------")
            print(evaluation_prompt)
            print("---------------------------------------")

        try:
            # 構造化出力を使用
            structured_llm = llm.with_structured_output(EvaluationResult)
            result: EvaluationResult = structured_llm.invoke(evaluation_prompt)
            
            # 評価理由を保存
            self.last_evaluation_reason = result.reason
            
            # verboseモードの場合は理由を出力
            if self.verbose:
                print(f"  評価理由: {result.reason}")
                print(f"  攻撃成功: {result.is_success}")
                print(f"  確信度: {result.confidence}")
            
            # 攻撃が成功していなければ、防御成功
            return not result.is_success, result
        except Exception as e:
            self.last_evaluation_error = str(e)
            if self.verbose:
                print(f"  {e}")
            # エラーを再発生させる
            raise ValueError(str(e)) from e
    
    def _evaluate_control_scenario(self, scenario: Scenario, response: str, llm: Any) -> tuple[bool, EvaluationResult]:
        """
        制御シナリオを評価
        
        Args:
            scenario: シナリオ
            response: 実隟のレスポンス
            llm: LLMインスタンス
        
        Returns:
            (期待される動作と一致している場合True, 評価結果)
        """
        evaluation_prompt = self._build_control_evaluation_prompt(scenario, response)

        if self.verbose:
            print("------ Evaluating control scenario ------")
            print(evaluation_prompt)
            print("---------------------------------------")

        try:
            # 構造化出力を使用
            structured_llm = llm.with_structured_output(EvaluationResult)
            result: EvaluationResult = structured_llm.invoke(evaluation_prompt)
            
            # 評価理由を保存
            self.last_evaluation_reason = result.reason
            
            # verboseモードの場合は理由を出力
            if self.verbose:
                print(f"  評価理由: {result.reason}")
                print(f"  期待通り: {result.is_success}")
                print(f"  確信度: {result.confidence}")
            
            # 期待される動作と一致しているかを返す
            return result.is_success, result
        except Exception as e:
            error_msg = f"制御シナリオの評価中にエラーが発生: {e}"
            self.last_evaluation_error = error_msg
            if self.verbose:
                print(f"  {error_msg}")
            # エラーを再発生させる
            raise ValueError(error_msg) from e
    
    def _build_attack_evaluation_prompt(self, scenario: Scenario, response: str) -> str:
        """攻撃評価用のプロンプトを構築"""
        conditions = scenario.attack_success_criteria.get('conditions', [])
        conditions_text = '\n'.join(f"{i+1}. {cond}" for i, cond in enumerate(conditions))

        # 設定からテンプレートを取得（必須）
        if self.config_manager:
            try:
                template = self.config_manager.get_attack_prompt_template()
                # テンプレート内の変数を置換
                prompt = template.format(
                    scenario_name=scenario.name,
                    user_request=scenario.user_request,
                    attack_goal=scenario.attack_goal,
                    conditions_text=conditions_text,
                    response=response
                )
                return prompt
            except ValueError as e:
                # 設定エラーの場合はそのままエラーを上げる
                raise e
        else:
            # ConfigManagerがない場合はエラー
            raise ValueError("ConfigManager is required for prompt templates")    
    def _build_control_evaluation_prompt(self, scenario: Scenario, response: str) -> str:
        """制御シナリオ評価用のプロンプトを構築"""
        
        # 設定からテンプレートを取得（必須）
        if self.config_manager:
            try:
                template = self.config_manager.get_control_prompt_template()
                # テンプレート内の変数を置換
                prompt = template.format(
                    scenario_name=scenario.name,
                    user_request=scenario.user_request,
                    expected_behavior=scenario.expected_behavior,
                    response=response
                )
                return prompt
            except ValueError as e:
                # 設定エラーの場合はそのままエラーを上げる
                raise e
        else:
            # ConfigManagerがない場合はエラー
            raise ValueError("ConfigManager is required for prompt templates")