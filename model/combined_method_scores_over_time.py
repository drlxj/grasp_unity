#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Position, Gesture, and Final Scores over Time plots for Combined Method
Each trial plots separate curves for position scores, gesture scores, and final scores over time
"""

import json
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd

# =============================================================================
# CONFIGURATION - 统一配置区域，修改时只需要改这里
# =============================================================================

# 数据目录路径列表
DATA_DIRECTORY = [
    r"C:\Users\Researcher\grasping-unity\user_study_data\2",
    # 可以添加更多路径，例如：
    # r"C:\Users\Researcher\grasping-unity\user_study_data\3",
    # r"C:\Users\Researcher\grasping-unity\user_study_data\4",
]

# 歧义条件分类
AMBIGUITY_CONDITIONS = {
    'high_spatial_high_semantic': 'high_xxxx_angle1.0',      # high spatial + high semantic
    'high_spatial_low_semantic': 'low_xxxx_angle1.0',        # high spatial + low semantic
    'low_spatial_high_semantic': 'high_xxxx_angle5.0',       # low spatial + high semantic  
    'low_spatial_low_semantic': 'low_xxxx_angle5.0'          # low spatial + low semantic
}

# 歧义条件标题
CONDITION_TITLES = {
    'high_spatial_high_semantic': 'High Spatial + High Semantic',
    'high_spatial_low_semantic': 'High Spatial + Low Semantic', 
    'low_spatial_high_semantic': 'Low Spatial + High Semantic',
    'low_spatial_low_semantic': 'Low Spatial + Low Semantic'
}

# 分数类型配置
SCORE_TYPES = {
    'position': {'key': 'positionScores', 'color': '#ff7f0e', 'label': 'Position Score'},
    'gesture': {'key': 'gestureScores', 'color': '#1f77b4', 'label': 'Gesture Score'},
    'final': {'key': 'finalScores', 'color': '#2ca02c', 'label': 'Final Score'}
}

# =============================================================================

def classify_ambiguity_conditions(folder_name):
    """Classify folder based on ambiguity conditions"""
    if 'high_' in folder_name and 'angle1.0' in folder_name:
        return 'high_spatial_high_semantic'
    elif 'high_' in folder_name and 'angle5.0' in folder_name:
        return 'low_spatial_high_semantic'
    elif 'low_' in folder_name and 'angle1.0' in folder_name:
        return 'high_spatial_low_semantic'
    elif 'low_' in folder_name and 'angle5.0' in folder_name:
        return 'low_spatial_low_semantic'
    else:
        return None

def load_trial_data(file_path):
    """Load trial data file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def load_continual_data(method_folder_path, trial_idx):
    """Load continual data from record_continual_data for a specific trial"""
    try:
        trial_folder = Path(method_folder_path) / "record_continual_data" / str(trial_idx)
        if not trial_folder.exists():
            return None
        
        # Get all JSON files and sort by name (time order)
        trial_files = sorted([f for f in trial_folder.iterdir() if f.suffix == '.json'])
        if not trial_files:
            return None
        
        continual_data = []
        for frame_file in trial_files:
            try:
                with open(frame_file, 'r') as f:
                    frame_data = json.load(f)
                
                if 'gestureData' in frame_data and 'rootPosition' in frame_data['gestureData']:
                    continual_data.append(frame_data)
                    
            except:
                continue
        
        return continual_data
        
    except:
        return None

def get_trial_info(trial_data, trial_idx):
    """Get target object name and success status for a specific trial"""
    if not trial_data or not isinstance(trial_data, list):
        return None, None
    
    # Group data by trial_id to get the last result for each trial
    trial_data_grouped = {}
    for trial in trial_data:
        if not isinstance(trial, dict):
            continue
        
        trial_id = trial.get('trialIndex', trial.get('trialId', 0))
        if trial_id not in trial_data_grouped:
            trial_data_grouped[trial_id] = []
        trial_data_grouped[trial_id].append(trial)
    
    # Get the last trial data for the specific trial_idx
    if trial_idx in trial_data_grouped:
        trials_for_id = trial_data_grouped[trial_idx]
        last_trial = trials_for_id[-1]
        
        target_object = last_trial.get('targetObjectName')
        success_status = last_trial.get('isSuccessful', False)
        
        return target_object, success_status
    
    return None, None

def extract_scores_over_time(method_folder_path, trial_idx):
    """Extract position, gesture, and final scores over time for all objects from continual data"""
    continual_data = load_continual_data(method_folder_path, trial_idx)
    if not continual_data:
        return None
    
    # Get all unique objects from all frames and all score types
    all_objects = set()
    for frame_data in continual_data:
        for score_type in SCORE_TYPES.values():
            scores = frame_data.get(score_type['key'], {})
            all_objects.update(scores.keys())
    
    if not all_objects:
        return None
    
    # Initialize data structure for all objects and score types
    time_data = []
    scores_data = {}
    
    for score_type_name, score_config in SCORE_TYPES.items():
        scores_data[score_type_name] = {obj: [] for obj in all_objects}
    
    for frame_idx, frame_data in enumerate(continual_data):
        time_data.append(frame_idx)  # Use frame index as time
        
        # Extract scores for each type
        for score_type_name, score_config in SCORE_TYPES.items():
            scores = frame_data.get(score_config['key'], {})
            
            for obj in all_objects:
                score = scores.get(obj, 0.0)
                scores_data[score_type_name][obj].append(score)

    # Get target object and success status for this specific trial
    trial_data_path = method_folder_path / "GraspResults.json"
    trial_data = load_trial_data(trial_data_path)
    target_object, success_status = get_trial_info(trial_data, trial_idx)
    
    return {
        'time': time_data,
        'scores_data': scores_data,
        'all_objects': list(all_objects),
        'target_object': target_object,
        'success_status': success_status
    }

def normalize_scores(scores_list):
    """Normalize scores to probability distribution"""
    total = sum(scores_list)
    if total > 0:
        return [score/total for score in scores_list]
    else:
        return scores_list

def plot_combined_scores_over_time_for_trial(experiment_name, trial_idx, scores_data_dict, 
                                           condition, output_dir="combined_scores_plots"):
    """Plot position, gesture, and final scores over time for Combined method"""
    output_dir = Path(output_dir)
    
    # Create condition-specific folder
    condition_folder = output_dir / condition
    condition_folder.mkdir(parents=True, exist_ok=True)
    
    if not scores_data_dict:
        print(f"No data available for {experiment_name} Trial {trial_idx}")
        return
    
    continual_data = scores_data_dict
    all_objects = continual_data.get('all_objects', [])
    scores_data = continual_data.get('scores_data', {})
    time_axis = continual_data.get('time', [])
    target_object = continual_data.get('target_object')
    success_status = continual_data.get('success_status')
    
    if not all_objects or not time_axis:
        print(f"No valid data for {experiment_name} Trial {trial_idx}")
        return
    
    # Create figure with subplots for each score type
    fig, axes = plt.subplots(1, 3, figsize=(24, 8))
    
    # Create main title
    title = f'Combined Method Scores over Time - {experiment_name} Trial {trial_idx}'
    if target_object:
        title += f'\nTarget: {target_object}'
    
    fig.suptitle(title, fontsize=16, fontweight='bold')
    
    # Define colors for different objects
    object_colors = ['blue', 'green', 'orange', 'purple', 'brown', 'pink', 'cyan', 'magenta']
    
    # Find the maximum value across all score types and objects for dynamic y-axis
    max_value = 0.0
    
    # Plot each score type
    for i, (score_type_name, score_config) in enumerate(SCORE_TYPES.items()):
        ax = axes[i]
        
        # Get scores for this type
        type_scores = scores_data.get(score_type_name, {})
        
        if not type_scores:
            ax.text(0.5, 0.5, f'No {score_type_name} data', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12, style='italic')
            ax.set_title(f'{score_config["label"]}', fontsize=14, fontweight='bold')
            continue
        
        # Plot curves for each object
        for j, obj in enumerate(all_objects):
            obj_scores = type_scores.get(obj, [])
            if not obj_scores:
                continue
            
            # Normalize scores
            normalized_scores = normalize_scores(obj_scores)
            
            # Find maximum value for y-axis scaling
            if normalized_scores:
                max_value = max(max_value, max(normalized_scores))
            
            # Plot with different styles based on whether it's target object
            color = object_colors[j % len(object_colors)]
            
            if obj == target_object:
                # Target object: bold, thick line, bright red color
                ax.plot(time_axis, normalized_scores, 
                       linestyle='-', linewidth=3, alpha=1.0,
                       color='red', marker='o', markersize=6, markevery=8,
                       label=f'{obj} (Target)')
            else:
                # Other objects: medium thickness, distinct colors
                ax.plot(time_axis, normalized_scores, 
                       linestyle='-', linewidth=2, alpha=0.8,
                       color=color, marker='s', markersize=4, markevery=8,
                       label=f'{obj}')
        
        # Set title with success status
        method_title = f'{score_config["label"]}'
        if success_status is not None:
            status_text = "✓ Success" if success_status else "✗ Failed"
            status_color = "green" if success_status else "red"
            method_title += f'\n{status_text}'
            ax.set_title(method_title, fontsize=14, fontweight='bold', color=status_color)
        else:
            ax.set_title(method_title, fontsize=14, fontweight='bold')
        
        ax.set_xlabel('Time (Frame Index)', fontsize=12)
        ax.set_ylabel('Normalized Score', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        
        # Set dynamic y-axis limit based on actual data maximum
        if max_value > 0:
            # Add 10% padding above the maximum value, with a minimum of 0.1
            y_max = max(max_value * 1.1, 0.1)
            ax.set_ylim(0, y_max)
        else:
            # Fallback to 0.4 if no data
            ax.set_ylim(0, 0.4)
    
    # Save plot in condition-specific folder
    filename = f"combined_{experiment_name}_trial_{trial_idx}"
    if target_object:
        filename += f"_{target_object.replace(' ', '_')}"
    filename += ".png"
    
    filepath = condition_folder / filename
    plt.tight_layout()
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Saved plot: {filepath}")

def analyze_combined_scores_over_time_by_ambiguity(data_dir):
    """Analyze combined scores over time data by ambiguity conditions"""
    data_dir = Path(data_dir)
    
    for experiment_folder in data_dir.iterdir():
        if not experiment_folder.is_dir():
            continue
            
        # Classify ambiguity condition
        condition = classify_ambiguity_conditions(experiment_folder.name)
        if condition is None:
            continue
            
        print(f"\nProcessing: {experiment_folder.name} -> {condition}")
        
        # Only process Combined method (C)
        method_folder = experiment_folder / "C"
        if not (method_folder.exists() and method_folder.is_dir()):
            print(f"    No Combined method data found")
            continue
        
        # Process each trial
        for trial_idx in range(5):  # Assuming 5 trials per experiment
            # Extract data for Combined method
            scores_data = extract_scores_over_time(method_folder, trial_idx)
            if scores_data:
                print(f"    Combined Trial {trial_idx}: {len(scores_data['time'])} frames, {len(scores_data['all_objects'])} objects")
                plot_combined_scores_over_time_for_trial(experiment_folder.name, trial_idx, 
                                                       scores_data, condition)
            else:
                print(f"    No data for Combined Trial {trial_idx}")

def main():
    """Main function"""
    print("Generating Combined Method Scores over Time Plots")
    print(f"Data directories: {DATA_DIRECTORY}")
    
    # Check if all directories exist
    for data_dir in DATA_DIRECTORY:
        if not os.path.exists(data_dir):
            print(f"Error: Data directory does not exist: {data_dir}")
            return
    
    # Create output directory
    output_dir = Path("outputs/combined_scores_plots")
    output_dir.mkdir(exist_ok=True)
    
    # Generate individual trial plots for each directory
    print("\nGenerating individual trial plots...")
    for i, data_dir in enumerate(DATA_DIRECTORY):
        print(f"\nProcessing directory {i+1}/{len(DATA_DIRECTORY)}: {data_dir}")
        analyze_combined_scores_over_time_by_ambiguity(data_dir)
    
    print(f"\nAll plots saved to: {output_dir.absolute()}")
    print("Analysis completed!")

if __name__ == "__main__":
    main()
