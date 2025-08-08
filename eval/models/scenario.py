"""シナリオのデータ構造定義"""

from typing import Dict, Any, Optional, List


class Scenario:
    """シナリオデータ"""
    
    def __init__(self, data: Dict[str, Any]):
        self.name: str = data['name']
        self.user_request: str = data['user_request']
        self.expected_behavior: str = data['expected_behavior']
        self.attack_case: bool = data.get('attack_case', False)
        self.attack_goal: Optional[str] = data.get('attack_goal')
        self.attack_success_criteria: Optional[Dict[str, Any]] = data.get('attack_success_criteria')
        self.raw_data: Dict[str, Any] = data
    
    def to_dict(self) -> Dict[str, Any]:
        return self.raw_data


class RequestResponse:
    """インタラクション履歴の単一エントリ"""
    
    def __init__(self, text: str, timestamp: float, 
                 interaction_type: str = "unknown"):
        """
        Args:
            text: テキスト内容
            timestamp: タイムスタンプ
            interaction_type: インタラクションタイプ
                - "user": ユーザーリクエスト
                - "tool_call": ツール呼び出し
                - "tool_response": ツールレスポンス
                - "ai_response": AI応答
        """
        self.text = text
        self.timestamp = timestamp
        self.interaction_type = interaction_type
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.interaction_type,
            'text': self.text,
            'timestamp': self.timestamp
        }


class Result:
    """
    実行結果データ
    
    シナリオ実行の結果を保持するクラス。
    実行履歴、最終回答、成功/失敗の判定結果を含む。
    
    Attributes:
        name: シナリオ名
        attack_case: 攻撃シナリオかどうか
        meets_expected_behavior: 期待される動作を満たしたかどうか
        execution_time: 実行時間（秒）
        request_response_history: リクエスト/レスポンスの履歴
        error: エラーが発生したか
        error_message: エラーメッセージ
        final_answer: AIの最終回答（Final Answer部分のみ）
        evaluation_details: 評価の詳細情報（理由、判定基準など）
    """
    
    def __init__(self, name: str, attack_case: bool, meets_expected_behavior: bool = False, 
                 execution_time: float = 0.0):
        self.name = name
        self.attack_case = attack_case
        self.meets_expected_behavior = meets_expected_behavior
        self.execution_time = execution_time
        self.request_response_history: List[RequestResponse] = []
        self.error = False
        self.error_message: Optional[str] = None
        self.final_answer: Optional[str] = None
        self.evaluation_details: Optional[Dict[str, Any]] = None
    
    def add_interaction(self, text: str, timestamp: float,
                       interaction_type: str = "unknown"):
        """インタラクションを履歴に追加"""
        self.request_response_history.append(
            RequestResponse(text, timestamp, interaction_type)
        )
    
    def set_error(self, error_message: str):
        """エラー状態を設定"""
        self.error = True
        self.error_message = error_message
    
    def get_final_response(self) -> str:
        """履歴から最終レスポンスを取得"""
        if self.request_response_history:
            # AI応答を探す（逆順で検索）
            for interaction in reversed(self.request_response_history):
                if interaction.interaction_type == "ai_response":
                    return interaction.text
            # 互換性のため、最後のエントリを返す
            return self.request_response_history[-1].text
        return ""
    
    def get_final_answer(self) -> Optional[str]:
        """
        履歴からFinal Answerのみを抽出
        
        AI応答から"Final Answer:"以降の部分を抽出する。
        LangChainのReActパターンで生成される最終回答を取得。
        
        Returns:
            Final Answer部分の文字列、見つからない場合はNone
        """
        final_response = self.get_final_response()
        if final_response:
            # "Final Answer:"以降のテキストを抽出
            if "Final Answer:" in final_response:
                answer_start = final_response.find("Final Answer:") + len("Final Answer:")
                return final_response[answer_start:].strip()
        return None
    
    def has_tool_calls(self) -> bool:
        """
        ツール呼び出しがあるかチェック
        
        Returns:
            ツール呼び出しがある場合True
        """
        for interaction in self.request_response_history:
            if interaction.interaction_type == "tool_call":
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        result_dict = {
            'name': self.name,
            'attack_case': self.attack_case,
            'meets_expected_behavior': self.meets_expected_behavior,
            'execution_time': self.execution_time,
            'error': self.error,
            'request_response_history': [
                interaction.to_dict() for interaction in self.request_response_history
            ]
        }
        
        # エラーメッセージがある場合のみ追加
        if self.error_message:
            result_dict['error_message'] = self.error_message
        
        # Final Answerがある場合のみ追加
        final_answer = self.get_final_answer()
        if final_answer:
            result_dict['final_answer'] = final_answer
        
        # 評価詳細がある場合のみ追加
        if self.evaluation_details:
            result_dict['evaluation_details'] = self.evaluation_details
        
        return result_dict