"""レポート生成・保存モジュール"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from models.scenario import Result


class Reporter:
    """レポート生成クラス"""
    
    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name
        self.output_dir = Path(f"results/{dataset_name}")
    
    def generate_report(self, results: List[Result], scenario_stats: Dict[str, Any] = None, 
                       execution_llm_info: Dict[str, str] = None, evaluation_llm_info: Dict[str, str] = None) -> Dict[str, Any]:
        """
        レポートを生成
        
        Args:
            results: 実行結果のリスト
            scenario_stats: 各シナリオの統計情報（オプション）
            execution_llm_info: 実行LLMのモデル情報（オプション）
            evaluation_llm_info: 評価LLMのモデル情報（オプション）
        
        Returns:
            レポート辞書
        """
        # エラーが発生した結果をカウント
        error_results = [r for r in results if hasattr(r, 'error') and r.error]
        
        # 基本レポート構造
        report = {
            'dataset': self.dataset_name,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_scenarios': len(results),
                'errors': len(error_results)
            }
        }
        
        # LLMメタデータを追加
        if execution_llm_info or evaluation_llm_info:
            report['metadata'] = {}
            if execution_llm_info:
                report['metadata']['execution_llm'] = execution_llm_info
            if evaluation_llm_info:
                report['metadata']['evaluation_llm'] = evaluation_llm_info
        
        # 統計情報がある場合は追加
        if scenario_stats:
            # statisticsをコピーしてresultsをシリアライズ可能な形式に変換
            serializable_stats = {}
            attack_scenarios = []
            control_scenarios = []
            
            for scenario_name, stats in scenario_stats.items():
                stat_copy = stats.copy()
                # resultsフィールドがある場合はResultオブジェクトをdictに変換し、名前を変更
                if 'results' in stat_copy:
                    stat_copy['iterations_detail'] = [r.to_dict() for r in stat_copy['results']]
                    
                    # エラーケースを除外して統計を計算
                    valid_results = [r for r in stat_copy['results'] if not r.error]
                    error_results = [r for r in stat_copy['results'] if r.error]
                    
                    # エラー情報を追加
                    stat_copy['error_count'] = len(error_results)
                    stat_copy['valid_iterations'] = len(valid_results)
                    
                    # シナリオタイプを判定（エラー以外で判定）
                    is_attack = any(r.attack_case for r in valid_results) if valid_results else any(r['attack_case'] for r in stat_copy['iterations_detail'])
                    
                    # 成功率を計算（エラーを除外）
                    if len(valid_results) > 0:
                        success_count = sum(1 for r in valid_results if r.meets_expected_behavior)
                        success_rate = success_count / len(valid_results)
                        stat_copy['success_rate'] = f"{success_rate:.1%}"
                        stat_copy['success_count'] = success_count
                        
                        # confidenceの平均を計算
                        confidences = []
                        for r in valid_results:
                            if hasattr(r, 'evaluation_details') and r.evaluation_details:
                                if 'confidence' in r.evaluation_details:
                                    confidences.append(r.evaluation_details['confidence'])
                        if confidences:
                            stat_copy['avg_confidence'] = sum(confidences) / len(confidences)
                    else:
                        stat_copy['success_rate'] = "N/A (all errors)"
                        stat_copy['success_count'] = 0
                        success_rate = 0
                    
                    # シナリオ毎の統計を分類
                    if is_attack:
                        attack_scenarios.append({
                            'name': scenario_name,
                            'success_count': stat_copy['success_count'],
                            'iterations': stat_copy['iterations'],
                            'valid_iterations': stat_copy['valid_iterations'],
                            'error_count': stat_copy['error_count'],
                            'success_rate': success_rate,
                            'avg_confidence': stat_copy.get('avg_confidence')
                        })
                    else:
                        control_scenarios.append({
                            'name': scenario_name,
                            'success_count': stat_copy['success_count'],
                            'iterations': stat_copy['iterations'],
                            'valid_iterations': stat_copy['valid_iterations'],
                            'error_count': stat_copy['error_count'],
                            'success_rate': success_rate,
                            'avg_confidence': stat_copy.get('avg_confidence')
                        })
                    
                    del stat_copy['results']  # 元のresultsフィールドを削除
                serializable_stats[scenario_name] = stat_copy
            
            report['results'] = serializable_stats
            
            # サマリー情報を更新
            report['summary']['iterations_per_scenario'] = next(iter(scenario_stats.values()))['iterations']
            
            # 攻撃シナリオの統計
            if attack_scenarios:
                total_attack_iterations = sum(s['iterations'] for s in attack_scenarios)
                total_valid_attack_iterations = sum(s['valid_iterations'] for s in attack_scenarios)
                total_attack_successes = sum(s['success_count'] for s in attack_scenarios)
                total_attack_errors = sum(s.get('error_count', 0) for s in attack_scenarios)
                
                if total_valid_attack_iterations > 0:
                    attack_block_rate = total_attack_successes / total_valid_attack_iterations
                    # 全体の平均confidenceを計算
                    avg_confidences = [s['avg_confidence'] for s in attack_scenarios if s.get('avg_confidence') is not None]
                    overall_avg_confidence = sum(avg_confidences) / len(avg_confidences) if avg_confidences else None
                else:
                    attack_block_rate = 0
                    overall_avg_confidence = None
                
                report['summary']['attack_scenarios'] = {
                    'count': len(attack_scenarios),
                    'total_iterations': total_attack_iterations,
                    'valid_iterations': total_valid_attack_iterations,
                    'error_count': total_attack_errors,
                    'overall_block_rate': f"{attack_block_rate:.1%}",
                    'avg_confidence': overall_avg_confidence,
                    'details': [
                        {
                            'name': s['name'],
                            'block_rate': f"{s['success_rate']:.1%}",
                            'blocked': f"{s['success_count']}/{s['valid_iterations']}",
                            'errors': s.get('error_count', 0),
                            'total': s['iterations'],
                            'avg_confidence': s.get('avg_confidence')
                        }
                        for s in attack_scenarios
                    ]
                }
            
            # 制御シナリオの統計
            if control_scenarios:
                total_control_iterations = sum(s['iterations'] for s in control_scenarios)
                total_valid_control_iterations = sum(s['valid_iterations'] for s in control_scenarios)
                total_control_successes = sum(s['success_count'] for s in control_scenarios)
                total_control_errors = sum(s.get('error_count', 0) for s in control_scenarios)
                
                if total_valid_control_iterations > 0:
                    control_pass_rate = total_control_successes / total_valid_control_iterations
                    # 全体の平均confidenceを計算
                    avg_confidences = [s['avg_confidence'] for s in control_scenarios if s.get('avg_confidence') is not None]
                    overall_avg_confidence = sum(avg_confidences) / len(avg_confidences) if avg_confidences else None
                else:
                    control_pass_rate = 0
                    overall_avg_confidence = None
                
                report['summary']['control_scenarios'] = {
                    'count': len(control_scenarios),
                    'total_iterations': total_control_iterations,
                    'valid_iterations': total_valid_control_iterations,
                    'error_count': total_control_errors,
                    'overall_pass_rate': f"{control_pass_rate:.1%}",
                    'avg_confidence': overall_avg_confidence,
                    'details': [
                        {
                            'name': s['name'],
                            'pass_rate': f"{s['success_rate']:.1%}",
                            'passed': f"{s['success_count']}/{s['valid_iterations']}",
                            'errors': s.get('error_count', 0),
                            'total': s['iterations'],
                            'avg_confidence': s.get('avg_confidence')
                        }
                        for s in control_scenarios
                    ]
                }
            
            # 全体の成功率（エラーを除外）
            total_iterations = sum(stats['iterations'] for stats in scenario_stats.values())
            total_valid_iterations = sum(s['valid_iterations'] for s in list(attack_scenarios) + list(control_scenarios))
            total_successes = sum(s['success_count'] for s in list(attack_scenarios) + list(control_scenarios))
            total_errors = sum(s.get('error_count', 0) for s in list(attack_scenarios) + list(control_scenarios))
            
            if total_valid_iterations > 0:
                overall_success_rate = total_successes / total_valid_iterations
            else:
                overall_success_rate = 0
            
            report['summary']['overall_success_rate'] = f"{overall_success_rate:.1%}"
            report['summary']['total_valid_iterations'] = total_valid_iterations
            report['summary']['total_errors'] = total_errors
            
        else:
            # 統計情報がない場合は、単一実行の結果を処理
            # エラーを除外した結果を分類
            valid_results = [r for r in results if not r.error]
            attack_results = [r for r in valid_results if r.attack_case]
            control_results = [r for r in valid_results if not r.attack_case]
            total_errors = len([r for r in results if r.error])
            
            report['summary']['total_errors'] = total_errors
            report['summary']['total_valid_results'] = len(valid_results)
            
            if attack_results:
                attack_blocked = sum(1 for r in attack_results if r.meets_expected_behavior)
                attack_block_rate = attack_blocked / len(attack_results) if attack_results else 0
                report['summary']['attack_scenarios'] = {
                    'count': len(attack_results),
                    'overall_block_rate': f"{attack_block_rate:.1%}",
                    'blocked_count': attack_blocked
                }
            
            if control_results:
                control_passed = sum(1 for r in control_results if r.meets_expected_behavior)
                control_pass_rate = control_passed / len(control_results) if control_results else 0
                report['summary']['control_scenarios'] = {
                    'count': len(control_results),
                    'overall_pass_rate': f"{control_pass_rate:.1%}",
                    'passed_count': control_passed
                }
            
            report['results'] = [r.to_dict() for r in results]
        
        return report
    
    def save_report(self, report: Dict[str, Any]) -> Path:
        """
        レポートを保存
        
        Args:
            report: レポート辞書
        
        Returns:
            保存したファイルパス
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"report_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return output_file
    
    def print_summary(self, report: Dict[str, Any]):
        """
        サマリーを表示
        
        Args:
            report: レポート辞書
        """
        print("\n" + "="*60)
        print(f"Dataset: {report['dataset']}")
        print(f"Time: {report['timestamp']}")
        print("-"*60)
        print(f"Total scenarios: {report['summary']['total_scenarios']}")
        
        # エラー情報を表示
        if 'errors' in report['summary'] and report['summary']['errors'] > 0:
            print(f"⚠️  Evaluation errors: {report['summary']['errors']}")
        
        # 新しいエラー情報を表示（統計情報がある場合）
        if 'total_errors' in report['summary'] and report['summary']['total_errors'] > 0:
            total_scenarios = report['summary']['total_scenarios']
            iterations_per = report['summary'].get('iterations_per_scenario', 1)
            total_iterations = total_scenarios * iterations_per
            error_rate = report['summary']['total_errors'] / total_iterations * 100
            print(f"⚠️  Errors: {report['summary']['total_errors']} ({error_rate:.1f}% of total iterations)")
            if 'total_valid_iterations' in report['summary']:
                print(f"   Valid evaluations: {report['summary']['total_valid_iterations']}")
        
        # イテレーション情報がある場合
        if 'iterations_per_scenario' in report['summary']:
            print(f"Iterations per scenario: {report['summary']['iterations_per_scenario']}")
            print(f"Overall success rate: {report['summary']['overall_success_rate']} (excluding errors)")
        
        # 攻撃シナリオの結果を表示
        if 'attack_scenarios' in report['summary']:
            attack_info = report['summary']['attack_scenarios']
            print("\n" + "-"*60)
            print(f"🛡️  Attack Scenarios ({attack_info['count']} scenarios)")
            if 'error_count' in attack_info and attack_info['error_count'] > 0:
                print(f"   Overall block rate: {attack_info['overall_block_rate']} (excluding {attack_info['error_count']} errors)")
            else:
                print(f"   Overall block rate: {attack_info['overall_block_rate']}")
            if 'avg_confidence' in attack_info and attack_info['avg_confidence'] is not None:
                print(f"   Average confidence: {attack_info['avg_confidence']:.2f}")
            if 'details' in attack_info:
                print("   Per-scenario block rates:")
                for detail in attack_info['details']:
                    if detail.get('errors', 0) > 0:
                        print(f"     • {detail['name']}: {detail['block_rate']} ({detail['blocked']}, {detail['errors']} errors)")
                    else:
                        print(f"     • {detail['name']}: {detail['block_rate']} ({detail['blocked']})")
            elif 'blocked_count' in attack_info:
                print(f"   Blocked: {attack_info['blocked_count']}/{attack_info['count']}")
        
        # 制御シナリオの結果を表示
        if 'control_scenarios' in report['summary']:
            control_info = report['summary']['control_scenarios']
            print("\n" + "-"*60)
            print(f"✅ Control Scenarios ({control_info['count']} scenarios)")
            if 'error_count' in control_info and control_info['error_count'] > 0:
                print(f"   Overall pass rate: {control_info['overall_pass_rate']} (excluding {control_info['error_count']} errors)")
            else:
                print(f"   Overall pass rate: {control_info['overall_pass_rate']}")
            if 'avg_confidence' in control_info and control_info['avg_confidence'] is not None:
                print(f"   Average confidence: {control_info['avg_confidence']:.2f}")
            if 'details' in control_info:
                print("   Per-scenario pass rates:")
                for detail in control_info['details']:
                    if detail.get('errors', 0) > 0:
                        print(f"     • {detail['name']}: {detail['pass_rate']} ({detail['passed']}, {detail['errors']} errors)")
                    else:
                        print(f"     • {detail['name']}: {detail['pass_rate']} ({detail['passed']})")
            elif 'passed_count' in control_info:
                print(f"   Passed: {control_info['passed_count']}/{control_info['count']}")
        
        # エラーの詳細を表示
        display_errors = False
        if 'errors' in report['summary'] and report['summary']['errors'] > 0:
            display_errors = True
        elif 'total_errors' in report['summary'] and report['summary']['total_errors'] > 0:
            display_errors = True
        
        if display_errors:
            print("\n" + "-"*60)
            print("⚠️  Error details:")
            # resultsが辞書の場合（統計情報）とリストの場合（単一実行）の両方に対応
            if isinstance(report['results'], dict):
                # 統計情報から各シナリオのエラーを確認
                for scenario_name, stats in report['results'].items():
                    if 'iterations_detail' in stats:
                        for detail in stats['iterations_detail']:
                            if 'error' in detail and detail['error']:
                                print(f"  • {detail['name']}: {detail.get('error_message', 'Unknown error')}")
                                break  # 同じシナリオの複数エラーは最初の1つだけ表示
            elif isinstance(report['results'], list):
                # 単一実行の結果を確認
                for result in report['results']:
                    if 'error' in result and result['error']:
                        print(f"  • {result['name']}: {result.get('error_message', 'Unknown error')}")
        
        print("="*60)