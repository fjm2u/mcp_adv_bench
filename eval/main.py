#!/usr/bin/env python3
"""
MCP Adversarial Benchmark Evaluator
メインエントリーポイント
"""

import os
import sys
import json
import argparse
import time
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from core.loader import load_scenarios, validate_dataset
from core.executor import Executor
from core.reporter import Reporter
import logging

# Load environment variables from .env file
load_dotenv()


def main():
    """メイン関数"""
    # コマンドライン引数のパース
    parser = argparse.ArgumentParser(description="MCP Adversarial Benchmark Evaluator")
    parser.add_argument("dataset_name", help="Name of the dataset to evaluate")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-i", type=int, default=1, help="Number of iterations to run each scenario (default: 1)")
    
    args = parser.parse_args()
    
    dataset_name = args.dataset_name
    verbose = args.verbose
    iterations = args.i

    if not verbose:
        logging.getLogger("mcp_use").setLevel(logging.WARNING)

    # LangChain Anthropicクライアントの初期化
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)
    
    # 実行用モデル（Haiku）
    execution_llm = ChatAnthropic(
        model="claude-3-haiku-20240307",
        anthropic_api_key=api_key,
        max_tokens=4096,
        temperature=0.5,
    )
    
    # 評価用モデル（Sonnet）- より高精度な判定のため
    evaluation_llm = ChatAnthropic(
        model="claude-sonnet-4-20250514", # claude-sonnet-4-20250514
        anthropic_api_key=api_key,
        max_tokens=1000,
        temperature=0.0,  # 評価の一貫性のため低温度
    )
    
    # データセット検証
    if not validate_dataset(dataset_name):
        print(f"Error: Invalid dataset '{dataset_name}'")
        sys.exit(1)
    
    print(f"Evaluating dataset: {dataset_name}")
    if verbose:
        print(f"Verbose mode: enabled")
    if iterations > 1:
        print(f"Running {iterations} iterations per scenario")
    
    # シナリオ読み込み
    scenarios = load_scenarios(dataset_name)
    if not scenarios:
        print("No scenarios found")
        sys.exit(1)
    
    # MCP設定を読み込む
    mcp_config_path = os.path.join(os.path.dirname(__file__), "mcp_config.json")
    if not os.path.exists(mcp_config_path):
        print(f"Error: MCP config file not found at {mcp_config_path}")
        sys.exit(1)
    
    with open(mcp_config_path, "r") as f:
        mcp_config = json.load(f)
    
    print("Initializing MCP servers...")
    print(f"  Execution model: {execution_llm.model}")
    print(f"  Evaluation model: {evaluation_llm.model}")
    
    # 結果を格納する変数
    results = []
    scenario_stats = {}  # 各シナリオの統計情報を保存
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"  [{i}/{len(scenarios)}] {scenario.name}...", end=' ')
        if verbose or iterations > 1:
            print()  # 改行して詳細を表示
        
        # 各シナリオをN回実行
        scenario_results = []
        success_count = 0
        execution_times = []
        
        for iter_num in range(iterations):
            if iterations > 1 and verbose:
                print(f"    Iteration {iter_num + 1}/{iterations}...", end=' ')
            
            # 各実行ごとに新しいExecutorを作成（独立性を確保）
            try:
                executor = Executor(mcp_config=mcp_config, llm=execution_llm, verbose=verbose, evaluation_llm=evaluation_llm)
            except Exception as e:
                print(f"Error initializing executor: {e}")
                print("Failed to initialize MCP. Check your MCP server configuration.")
                sys.exit(1)
            
            start_time = time.time()
            result = executor.execute(scenario)
            execution_time = time.time() - start_time
            
            # 実行後にクリーンアップ（リソースの解放）
            if hasattr(executor, 'cleanup'):
                executor.cleanup()
            
            scenario_results.append(result)
            execution_times.append(execution_time)
            if result.meets_expected_behavior:
                success_count += 1
            
            if iterations > 1 and verbose:
                print("✓" if result.meets_expected_behavior else "✗")
        
        # 統計情報を計算
        success_rate = success_count / iterations
        avg_time = sum(execution_times) / len(execution_times)
        
        # 最初の結果を代表として保存（後方互換性のため）
        results.append(scenario_results[0])
        
        # 統計情報を保存
        scenario_stats[scenario.name] = {
            "iterations": iterations,
            "success_count": success_count,
            "success_rate": success_rate,
            "avg_execution_time": avg_time,
            "execution_times": execution_times,
            "results": scenario_results
        }
        
        if not verbose and iterations == 1:
            print("✓" if scenario_results[0].meets_expected_behavior else "✗")
        elif iterations > 1:
            print(f"    Success rate: {success_count}/{iterations} ({success_rate:.1%})")
            if verbose:
                print(f"    Average execution time: {avg_time:.2f}s")
    
    # LLMメタデータを作成
    execution_llm_info = {
        "model": execution_llm.model,
        "temperature": execution_llm.temperature,
        "max_tokens": execution_llm.max_tokens
    }
    
    evaluation_llm_info = {
        "model": evaluation_llm.model,
        "temperature": evaluation_llm.temperature,
        "max_tokens": evaluation_llm.max_tokens
    }
    
    # レポート生成・保存
    reporter = Reporter(dataset_name)
    # 統計情報がある場合（iterations > 1）は渡す
    if iterations > 1:
        report = reporter.generate_report(results, scenario_stats, execution_llm_info, evaluation_llm_info)
    else:
        report = reporter.generate_report(results, execution_llm_info=execution_llm_info, evaluation_llm_info=evaluation_llm_info)
    output_file = reporter.save_report(report)
    
    print(f"\nReport saved: {output_file}")
    reporter.print_summary(report)


if __name__ == "__main__":
    main()