"""シナリオ読み込みモジュール"""

import sys
import yaml
from pathlib import Path
from typing import List, Dict, Any
from models.scenario import Scenario


def load_scenarios(dataset_name: str) -> List[Scenario]:
    """
    シナリオファイルを読み込む
    
    Args:
        dataset_name: データセット名
    
    Returns:
        シナリオのリスト
    """
    scenarios_path = Path(f"../datasets/{dataset_name}/scenarios.yml")
    
    if not scenarios_path.exists():
        print(f"Error: {scenarios_path} not found")
        sys.exit(1)
    
    with open(scenarios_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    scenarios_data = data.get('scenarios', [])
    
    if not scenarios_data:
        print("No scenarios found in scenarios.yml")
        return []
    
    return [Scenario(s) for s in scenarios_data]


def validate_dataset(dataset_name: str) -> bool:
    """
    データセットの存在を確認
    
    Args:
        dataset_name: データセット名
    
    Returns:
        有効な場合True
    """
    dataset_path = Path(f"../datasets/{dataset_name}")
    scenarios_path = dataset_path / "scenarios.yml"
    
    return dataset_path.exists() and scenarios_path.exists()