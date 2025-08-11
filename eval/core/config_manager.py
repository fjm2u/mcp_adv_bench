"""評価設定管理モジュール"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """評価設定を管理するクラス"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス（省略時はデフォルトパスを使用）
        """
        if config_path is None:
            # デフォルトパス: 実行ディレクトリのeval_config.json
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "eval_config.json")
        
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        設定ファイルを読み込む
        
        Returns:
            設定辞書
        """
        if not os.path.exists(self.config_path):
            # 設定ファイルが存在しない場合はデフォルト設定を返す
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # デフォルト設定とマージ（不足している項目を補完）
                return self._merge_with_defaults(config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config from {self.config_path}: {e}")
            print("Using default configuration")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        デフォルト設定を返す
        
        Returns:
            デフォルト設定辞書
        """
        return {
            "llm": {
                "execution": {
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 4096,
                    "temperature": 0.5,
                    "timeout": None,
                    "max_retries": 2
                },
                "evaluation": {
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "temperature": 0.0,
                    "timeout": None,
                    "max_retries": 2
                }
            }
        }
    
    
    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        設定をデフォルト値とマージ
        
        Args:
            config: 読み込んだ設定
            
        Returns:
            マージ後の設定
        """
        default = self._get_default_config()
        return self._deep_merge(default, config)
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        辞書を深くマージ
        
        Args:
            base: ベース辞書
            override: 上書き辞書
            
        Returns:
            マージ後の辞書
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def get_execution_llm_config(self) -> Dict[str, Any]:
        """実行用LLM設定を取得"""
        return self.config.get("llm", {}).get("execution", {})
    
    def get_evaluation_llm_config(self) -> Dict[str, Any]:
        """評価用LLM設定を取得"""
        return self.config.get("llm", {}).get("evaluation", {})
    
    def get_attack_prompt_template(self) -> str:
        """攻撃評価プロンプトテンプレートを取得"""
        if "prompts" not in self.config:
            raise ValueError("Configuration error: 'prompts' section is missing in config file")
        if "attack_evaluation" not in self.config["prompts"]:
            raise ValueError("Configuration error: 'attack_evaluation' is missing in prompts section")
        if "template" not in self.config["prompts"]["attack_evaluation"]:
            raise ValueError("Configuration error: 'template' is missing in attack_evaluation section")
        return self.config["prompts"]["attack_evaluation"]["template"]
    
    def get_control_prompt_template(self) -> str:
        """制御評価プロンプトテンプレートを取得"""
        if "prompts" not in self.config:
            raise ValueError("Configuration error: 'prompts' section is missing in config file")
        if "control_evaluation" not in self.config["prompts"]:
            raise ValueError("Configuration error: 'control_evaluation' is missing in prompts section")
        if "template" not in self.config["prompts"]["control_evaluation"]:
            raise ValueError("Configuration error: 'template' is missing in control_evaluation section")
        return self.config["prompts"]["control_evaluation"]["template"]
    
    
    def override_from_env(self):
        """
        環境変数から設定を上書き
        
        サポートする環境変数:
        - EVAL_EXECUTION_MODEL: 実行用モデル名
        - EVAL_EVALUATION_MODEL: 評価用モデル名
        - EVAL_EXECUTION_TEMPERATURE: 実行用温度
        - EVAL_EVALUATION_TEMPERATURE: 評価用温度
        """
        # 実行用モデル
        if exec_model := os.getenv("EVAL_EXECUTION_MODEL"):
            self.config["llm"]["execution"]["model"] = exec_model
            
        # 評価用モデル
        if eval_model := os.getenv("EVAL_EVALUATION_MODEL"):
            self.config["llm"]["evaluation"]["model"] = eval_model
            
        # 実行用温度
        if exec_temp := os.getenv("EVAL_EXECUTION_TEMPERATURE"):
            try:
                self.config["llm"]["execution"]["temperature"] = float(exec_temp)
            except ValueError:
                print(f"Warning: Invalid EVAL_EXECUTION_TEMPERATURE value: {exec_temp}")
                
        # 評価用温度
        if eval_temp := os.getenv("EVAL_EVALUATION_TEMPERATURE"):
            try:
                self.config["llm"]["evaluation"]["temperature"] = float(eval_temp)
            except ValueError:
                print(f"Warning: Invalid EVAL_EVALUATION_TEMPERATURE value: {eval_temp}")
    
    def save_config(self, path: Optional[str] = None):
        """
        現在の設定をファイルに保存
        
        Args:
            path: 保存先パス（省略時は読み込み元パス）
        """
        save_path = path or self.config_path
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def update_config(self, updates: Dict[str, Any]):
        """
        設定を更新
        
        Args:
            updates: 更新する設定の辞書
        """
        self.config = self._deep_merge(self.config, updates)