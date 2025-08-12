"""
LLMファクトリーモジュール
各プロバイダーのLLMインスタンスを生成
"""

import os
import sys
from typing import Dict, Any, Optional
from langchain_core.language_models import BaseChatModel


class LLMFactory:
    """LLMインスタンスを生成するファクトリークラス"""
    
    @staticmethod
    def create_llm(config: Dict[str, Any]) -> BaseChatModel:
        """
        設定に基づいてLLMインスタンスを生成
        
        Args:
            config: LLM設定辞書（provider, model, max_tokens等を含む）
            
        Returns:
            BaseChatModel: 生成されたLLMインスタンス
            
        Raises:
            ValueError: サポートされていないプロバイダーの場合
            SystemExit: 必要なAPIキーが設定されていない場合
        """
        provider = config.get("provider", "anthropic").lower()
        
        if provider == "anthropic":
            return LLMFactory._create_anthropic(config)
        elif provider == "openai":
            return LLMFactory._create_openai(config)
        elif provider == "google" or provider == "gemini":
            return LLMFactory._create_google(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    def _create_anthropic(config: Dict[str, Any]) -> BaseChatModel:
        """Anthropic Claude LLMを作成"""
        from langchain_anthropic import ChatAnthropic
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY environment variable not set")
            sys.exit(1)
        
        return ChatAnthropic(
            model=config.get("model", "claude-3-haiku-20240307"),
            anthropic_api_key=api_key,
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.5),
            timeout=config.get("timeout"),
            max_retries=config.get("max_retries", 2)
        )
    
    @staticmethod
    def _create_openai(config: Dict[str, Any]) -> BaseChatModel:
        """OpenAI GPT LLMを作成"""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            print("Error: langchain-openai is not installed. Run: pip install langchain-openai")
            sys.exit(1)
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable not set")
            sys.exit(1)
        
        # OpenAI用のパラメータマッピング
        model_name = config.get("model", "gpt-4")
        
        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.5),
            timeout=config.get("timeout"),
            max_retries=config.get("max_retries", 2)
        )
    
    @staticmethod
    def _create_google(config: Dict[str, Any]) -> BaseChatModel:
        """Google Gemini LLMを作成"""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            print("Error: langchain-google-genai is not installed. Run: pip install langchain-google-genai")
            sys.exit(1)
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Error: GOOGLE_API_KEY environment variable not set")
            sys.exit(1)
        
        model_name = config.get("model", "gemini-pro")
        
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            max_output_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.5),
            timeout=config.get("timeout"),
            max_retries=config.get("max_retries", 2)
        )
    
    @staticmethod
    def detect_provider_from_model(model_name: str) -> str:
        """
        モデル名からプロバイダーを自動検出
        
        Args:
            model_name: モデル名
            
        Returns:
            str: 検出されたプロバイダー名
        """
        model_lower = model_name.lower()
        
        if "claude" in model_lower:
            return "anthropic"
        elif "gpt" in model_lower:
            return "openai"
        elif "gemini" in model_lower:
            return "google"
        else:
            # デフォルトはanthropic
            return "anthropic"