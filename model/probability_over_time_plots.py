#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Probability-over-time plots for PGC methods
Each trial plots probability curves for target object over time
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
    r"C:\Users\Researcher\grasping-unity\user_study_data\3",
    r"C:\Users\Researcher\grasping-unity\user_study_data\4",
]

# 要分析的PGC方法
PGC_METHODS = ['P', 'G', 'C']  # Pointing, Grasping, Combined

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

# 方法颜色方案
METHOD_COLORS = {'P': '#1f77b4', 'G': '#ff7f0e', 'C': '#2ca02c'}

# 方法描述
METHOD_DESCRIPTIONS = {
    'P': 'Pointing Method',
    'G': 'Grasping Method', 
    'C': 'Combined Method'
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

def extract_probability_over_time(method_folder_path, trial_idx):
    """Extract probability over time for all objects from continual data"""
    continual_data = load_continual_data(method_folder_path, trial_idx)
    if not continual_data:
        return None
    
    # Get all unique objects from all frames
    all_objects = set()
    for frame_data in continual_data:
        final_scores = frame_data.get('finalScores', {})
        all_objects.update(final_scores.keys())
    
    if not all_objects:
        return None
    
    # Initialize data structure for all objects
    time_data = []
    all_objects_scores = {obj: [] for obj in all_objects}
    
    for frame_idx, frame_data in enumerate(continual_data):
        time_data.append(frame_idx)  # Use frame index as time
        
        # Extract final scores for all objects
        final_scores = frame_data.get('finalScores', {})
        
        for obj in all_objects:
            score = final_scores.get(obj, 0.0)
            all_objects_scores[obj].append(score)

    # Get target object and success status for this specific trial
    trial_data_path = method_folder_path / "GraspResults.json"
    trial_data = load_trial_data(trial_data_path)
    target_object, success_status = get_trial_info(trial_data, trial_idx)
    
    return {
        'time': time_data,
        'all_objects_scores': all_objects_scores,
        'all_objects': list(all_objects),
        'target_object': target_object,
        'success_status': success_status
    }

def get_final_scores_from_trial_data(trial_data, target_object):
    """Get final scores from trial data for normalization"""
    if not trial_data or not isinstance(trial_data, list):
        return None, None, None
    
    # Group data by trial_id to get the last result for each trial
    trial_data_grouped = {}
    for trial in trial_data:
        if not isinstance(trial, dict):
            continue
        
        trial_id = trial.get('trialIndex', trial.get('trialId', 0))
        if trial_id not in trial_data_grouped:
            trial_data_grouped[trial_id] = []
        trial_data_grouped[trial_id].append(trial)
    
    # For each trial_id, take the last trial data
    for trial_id in sorted(trial_data_grouped.keys()):
        trials_for_id = trial_data_grouped[trial_id]
        # Take the last trial data for this trial_id
        last_trial = trials_for_id[-1]
        
        # Extract final scores from grasps
        grasps = last_trial.get('grasps', [])
        if not grasps:
            continue
        
        # Get the last grasp for final scores
        last_grasp = grasps[-1] if grasps else {}
        
        # Normalize scores
        gesture_scores = normalize_scores(last_grasp.get('gestureScores', {}))
        position_scores = normalize_scores(last_grasp.get('positionScores', {}))
        
        final_gesture_score = gesture_scores.get(target_object, 0.0)
        final_directional_score = position_scores.get(target_object, 0.0)
        final_combined_score = final_gesture_score + final_directional_score
        
        return final_gesture_score, final_directional_score, final_combined_score
    
    return None, None, None

def normalize_scores(scores_dict):
    """Normalize scores to probability distribution"""
    total = sum(scores_dict.values())
    if total > 0:
        return {k: v/total for k, v in scores_dict.items()}
    else:
        return scores_dict

def get_trial_success_status(method_folder_path, trial_idx):
    """Get is_successful status for a specific trial from GraspResults.json"""
    try:
        grasp_results_path = method_folder_path / "GraspResults.json"
        if not grasp_results_path.exists():
            return None
            
        with open(grasp_results_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data or not isinstance(data, list):
            return None
        
        # Group data by trial_id to get the last result for each trial
        trial_data_grouped = {}
        for trial in data:
            if not isinstance(trial, dict):
                continue
            
            trial_id = trial.get('trialIndex', trial.get('trialId', 0))
            if trial_id not in trial_data_grouped:
                trial_data_grouped[trial_id] = []
            trial_data_grouped[trial_id].append(trial)
        
        # Get the last result for the specific trial
        if trial_idx in trial_data_grouped:
            trials_for_id = trial_data_grouped[trial_idx]
            last_trial = trials_for_id[-1]
            return last_trial.get('isSuccessful', False)
        
        return None
        
    except Exception as e:
        print(f"Error reading GraspResults.json from {method_folder_path}: {e}")
        return None

def plot_probability_over_time_for_trial(experiment_name, trial_idx, method_data_dict, 
                                       condition, subject_id, output_dir="probability_plots"):
    """Plot probability over time for a specific trial across all methods"""
    output_dir = Path(output_dir)
    
    # Create condition-specific folder
    condition_folder = output_dir / condition
    condition_folder.mkdir(parents=True, exist_ok=True)
    
    # Create figure with subplots for each method
    if len(PGC_METHODS) == 1:
        fig, axes = plt.subplots(1, 1, figsize=(8, 6))
        axes = [axes]
    else:
        fig, axes = plt.subplots(1, len(PGC_METHODS), figsize=(20, 6))
    
    # Get target object from the first available method
    target_object = None
    for method_data in method_data_dict.values():
        if method_data and method_data.get('target_object'):
            target_object = method_data['target_object']
            break
    
    # Create main title
    title = f'Final Scores over Time - {experiment_name} Trial {trial_idx}'
    if target_object:
        title += f'\nTarget: {target_object}'
    
    fig.suptitle(title, fontsize=16, fontweight='bold')
    
    # Store legend handles and labels for shared legend
    legend_handles = []
    legend_labels = []
    
    # Define colors for different objects
    colors = ['blue', 'green', 'orange', 'purple', 'brown', 'pink', 'cyan', 'magenta']
    
    # Find the maximum value across all methods and objects for dynamic y-axis
    max_value = 0.0
    
    for i, method in enumerate(PGC_METHODS):
        ax = axes[i]
        
        if method not in method_data_dict or method_data_dict[method] is None:
            ax.text(0.5, 0.5, f'No data for {method}', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12, style='italic')
            ax.set_title(f'{METHOD_DESCRIPTIONS.get(method, method)}', fontsize=14, fontweight='bold')
            continue
        
        continual_data = method_data_dict[method]
        
        if continual_data:
            # Get all objects and their scores from the extracted data
            all_objects = continual_data.get('all_objects', [])
            all_objects_scores = continual_data.get('all_objects_scores', {})
            time_axis = continual_data.get('time', [])
            method_target_object = continual_data.get('target_object')
            success_status = continual_data.get('success_status')
            
            # Find maximum value in this method's data
            for obj in all_objects:
                obj_scores = all_objects_scores.get(obj, [])
                if obj_scores:
                    # Normalize scores to find max
                    total_score = sum(obj_scores)
                    if total_score > 0:
                        normalized_scores = [score / total_score for score in obj_scores]
                        method_max = max(normalized_scores)
                        max_value = max(max_value, method_max)
            
            # Plot curves for each object
            for j, obj in enumerate(all_objects):
                obj_final_scores = all_objects_scores.get(obj, [])
                if not obj_final_scores:
                    continue
                
                # Normalize scores
                total_score = sum(obj_final_scores)
                if total_score > 0:
                    normalized_obj_final_scores = [score / total_score for score in obj_final_scores]
                else:
                    normalized_obj_final_scores = obj_final_scores
                
                # Plot with different styles based on whether it's target object
                if obj == method_target_object:
                    # Target object: bold, thick line, bright red color
                    line, = ax.plot(time_axis, normalized_obj_final_scores, 
                           linestyle='-', linewidth=2, alpha=1.0,
                           color='red', marker='o', markersize=5, markevery=8)
                    # Only add to legend once (from first subplot)
                    if i == 0:
                        legend_handles.append(line)
                        legend_labels.append(f'{obj} (Target)')
                else:
                    # Other objects: medium thickness, distinct colors, good visibility
                    color = colors[j % len(colors)]
                    line, = ax.plot(time_axis, normalized_obj_final_scores, 
                           linestyle='-', linewidth=2, alpha=0.8,
                           color=color, marker='s', markersize=5, markevery=8)
                    # Only add to legend once (from first subplot)
                    if i == 0:
                        legend_handles.append(line)
                        legend_labels.append(f'{obj}')
        
        # Create title with success status
        method_title = f'{METHOD_DESCRIPTIONS.get(method, method)}'
        if continual_data and continual_data.get('success_status') is not None:
            success_status = continual_data.get('success_status')
            status_text = "✓ Success" if success_status else "✗ Failed"
            status_color = "green" if success_status else "red"
            method_title += f'\n{status_text}'
            ax.set_title(method_title, fontsize=14, fontweight='bold', color=status_color)
        else:
            ax.set_title(method_title, fontsize=14, fontweight='bold')
        
        ax.set_xlabel('Time (Frame Index)', fontsize=12)
        ax.set_ylabel('Final Score', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Set dynamic y-axis limit based on actual data maximum
        if max_value > 0:
            # Add 10% padding above the maximum value, with a minimum of 0.1
            y_max = max(max_value * 1.1, 0.1)
            ax.set_ylim(0, y_max)
        else:
            # Fallback to 0.4 if no data
            ax.set_ylim(0, 0.4)
    
    # Add shared legend to the figure
    if len(PGC_METHODS) == 1:
        # For single method, use a more compact legend
        fig.legend(legend_handles, legend_labels, loc='upper center', bbox_to_anchor=(0.5, 0.02), 
                   ncol=min(4, len(legend_labels)), fontsize=10)
    else:
        # For multiple methods, use full width legend
        fig.legend(legend_handles, legend_labels, loc='upper center', bbox_to_anchor=(0.5, 0.02), 
                   ncol=len(legend_labels), fontsize=10)
    
    # Save plot in condition-specific folder
    filename = f"{experiment_name}_trial_{trial_idx}"
    if target_object:
        filename += f"_{target_object.replace(' ', '_')}"
    filename += ".png"
    
    filepath = condition_folder / f"{subject_id}_{filename}"
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)  # Make room for shared legend
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Saved plot: {filepath}")

def analyze_probability_over_time_by_ambiguity(data_dir):
    """Analyze probability over time data by ambiguity conditions"""
    data_dir = Path(data_dir)
    subject_id = data_dir.name
    
    for experiment_folder in data_dir.iterdir():
        if not experiment_folder.is_dir():
            continue
            
        # Classify ambiguity condition
        condition = classify_ambiguity_conditions(experiment_folder.name)
        if condition is None:
            continue
            
        print(f"\nProcessing: {experiment_folder.name} -> {condition}")
        
        # Process each trial
        for trial_idx in range(5):  # Assuming 5 trials per experiment
            method_data_dict = {}
            
            # Extract data for each method
            for method in PGC_METHODS:
                method_folder = experiment_folder / method
                if method_folder.exists() and method_folder.is_dir():
                    # Get continual data for all objects
                    continual_data = extract_probability_over_time(method_folder, trial_idx)
                    if continual_data:
                        method_data_dict[method] = continual_data
                        print(f"    Method {method} Trial {trial_idx}: {len(continual_data['time'])} frames, {len(continual_data['all_objects'])} objects")
            
            # Plot if we have data for at least one method
            if method_data_dict:
                plot_probability_over_time_for_trial(experiment_folder.name, trial_idx, 
                                                   method_data_dict, condition, subject_id)


def main():
    """Main function"""
    print("Generating Probability-over-time Plots")
    print(f"Data directories: {DATA_DIRECTORY}")
    
    # Check if all directories exist
    for data_dir in DATA_DIRECTORY:
        if not os.path.exists(data_dir):
            print(f"Error: Data directory does not exist: {data_dir}")
            return
    
    # Create output directory
    output_dir = Path("outputs/probability_plots")
    output_dir.mkdir(exist_ok=True)
    
    # Generate individual trial plots for each directory
    print("\nGenerating individual trial plots...")
    for i, data_dir in enumerate(DATA_DIRECTORY):
        print(f"\nProcessing directory {i+1}/{len(DATA_DIRECTORY)}: {data_dir}")
        analyze_probability_over_time_by_ambiguity(data_dir)
    
    print(f"\nAll plots saved to: {output_dir.absolute()}")
    print("Analysis completed!")

if __name__ == "__main__":
    main()
