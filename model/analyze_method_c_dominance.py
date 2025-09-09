#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze Method C dominance scores across ambiguity conditions
Computes φ_point (phi_point) dominance score for each trial
"""

import json
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd
import seaborn as sns

# =============================================================================
# CONFIGURATION
# =============================================================================

# 数据目录路径列表
DATA_DIRECTORIES = [
    r"C:\Users\Researcher\grasping-unity\user_study_data\1",
    r"C:\Users\Researcher\grasping-unity\user_study_data\2",
    r"C:\Users\Researcher\grasping-unity\user_study_data\3",
    r"C:\Users\Researcher\grasping-unity\user_study_data\4",
    r"C:\Users\Researcher\grasping-unity\user_study_data\5",
    r"C:\Users\Researcher\grasping-unity\user_study_data\6",
    r"C:\Users\Researcher\grasping-unity\user_study_data\7",
    r"C:\Users\Researcher\grasping-unity\user_study_data\8",
    r"C:\Users\Researcher\grasping-unity\user_study_data\9",
    r"C:\Users\Researcher\grasping-unity\user_study_data\10",
    r"C:\Users\Researcher\grasping-unity\user_study_data\11",
    r"C:\Users\Researcher\grasping-unity\user_study_data\12",
]

# 要分析的方法（只分析Combined方法）
METHOD = 'C'

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

def normalize_scores(scores_dict):
    """Normalize scores to probability distribution"""
    total = sum(scores_dict.values())
    if total > 0:
        return {k: v/total for k, v in scores_dict.items()}
    else:
        return scores_dict





def extract_trial_scores(trial_data, trial_idx, target_object, trial_data_path):
    """
    Extract scores for a specific trial from the last grasp result
    
    Args:
        trial_data: trial data from GraspResults.json
        trial_idx: trial index
        target_object: target object name
    
    Returns:
        dict with gesture_scores, position_scores, final_scores, success_status
    """
    if not trial_data or not isinstance(trial_data, list):
        return None
    
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
        
        # record_continual_data_path = trial_data_path.parent / "record_continual_data" / str(trial_idx)
        # record_continual_data_files = list(record_continual_data_path.glob("*.json"))
        # record_continual_data_files.sort(key=lambda x: int(x.stem))
        # if len(record_continual_data_files) == 0:
        #     print(f"  No record_continual_data.json found for trial {record_continual_data_path}")
        #     return None

        # with open(record_continual_data_files[-1], "r") as f:
        #     last_grasp = json.load(f)

        # # Extract scores
        # gesture_scores = last_grasp.get('gestureScores', {})
        # position_scores = last_grasp.get('positionScores', {})
        # final_scores = last_grasp.get('finalScores', {})
        # success_status = last_trial.get('isSuccessful', False)

        gesture_scores = last_trial.get('gestureScores', {})
        position_scores = last_trial.get('positionScores', {})
        final_scores = last_trial.get('finalScores', {})
        success_status = last_trial.get('isSuccessful', False)
        
        # Normalize scores
        # gesture_scores_norm = normalize_scores(gesture_scores)
        # position_scores_norm = normalize_scores(position_scores)
        # final_scores_norm = normalize_scores(final_scores)
        gesture_scores_norm = gesture_scores
        position_scores_norm = position_scores
        final_scores_norm = final_scores
        
        return {
            'gesture_scores': gesture_scores_norm,
            'position_scores': position_scores_norm,
            'final_scores': final_scores_norm,
            'success_status': success_status,
            'target_object': target_object
        }
    
    return None

def analyze_method_c_dominance(data_directories):
    """Analyze Method C dominance scores across ambiguity conditions from multiple directories"""
    if isinstance(data_directories, str):
        data_directories = [data_directories]
    
    # Store results by condition
    condition_results = {}
    
    for data_dir in data_directories:
        data_dir = Path(data_dir)
        if not data_dir.exists():
            print(f"Warning: Directory '{data_dir}' not found, skipping...")
            continue
            
        print(f"Processing directory: {data_dir}")
    
        for experiment_folder in data_dir.iterdir():
            if not experiment_folder.is_dir():
                continue
                
            # Classify ambiguity condition
            condition = classify_ambiguity_conditions(experiment_folder.name)
            if condition is None:
                continue
                
            print(f"\nProcessing: {experiment_folder.name} -> {condition}")
            
            # Load trial data
            trial_data_path = experiment_folder / METHOD / "GraspResults.json"
            if not trial_data_path.exists():
                print(f"  No GraspResults.json found for {METHOD}")
                continue
                
            trial_data = load_trial_data(trial_data_path)
            if not trial_data:
                continue
            
            # Initialize condition results
            if condition not in condition_results:
                condition_results[condition] = []
            
            # Process each trial
            for trial_idx in range(5):  # Assuming 5 trials per experiment
                # Get target object and success status
                target_object, success_status = get_trial_info(trial_data, trial_idx)
                if not target_object:
                    print(f"  No target object found for trial {trial_idx}")
                    continue
                
                # Extract scores
                scores_data = extract_trial_scores(trial_data, trial_idx, target_object, trial_data_path)
                if not scores_data:
                    print(f"  No scores found for trial {trial_idx}")
                    continue
                
                # Get all objects (should be the same across all score types)
                all_objects = set(scores_data['gesture_scores'].keys())
                all_objects.update(scores_data['position_scores'].keys())
                all_objects.update(scores_data['final_scores'].keys())
                all_objects = sorted(all_objects)
            
            
                if len(all_objects) == 0:
                    print(f"  No objects found for trial {trial_idx}")
                    continue
                
                # Convert to arrays in the same order
                P_D = [scores_data['position_scores'].get(obj, 0.0) for obj in all_objects]
                P_G = [scores_data['gesture_scores'].get(obj, 0.0) for obj in all_objects]
                P_M = [scores_data['final_scores'].get(obj, 0.0) for obj in all_objects]
                
                # Store result
                result = {
                    'experiment': experiment_folder.name,
                    'trial_idx': trial_idx,
                    'target_object': target_object,
                    'success_status': success_status,
                    'P_D': P_D,
                    'P_G': P_G,
                    'P_M': P_M,
                    'objects': all_objects
                }
                
                condition_results[condition].append(result)
                
    
    return condition_results



def analyze_score_selection_patterns(condition_results):
    """Analyze gesture and position score selection patterns for successful and failed trials by condition"""
    print("\n" + "="*80)
    print("SCORE SELECTION PATTERN ANALYSIS BY CONDITION")
    print("="*80)
    
    # Initialize counters for each condition
    condition_patterns = {}
    
    for condition in condition_results.keys():
        condition_patterns[condition] = {
            'success': {
                'both_selected': 0,      # Both gesture and position selected target
                'gesture_only': 0,       # Only gesture selected target
                'position_only': 0,      # Only position selected target
                'neither_selected': 0    # Neither selected target (shouldn't happen in success)
            },
            'failure': {
                'both_selected': 0,      # Both gesture and position selected target (shouldn't happen in failure)
                'gesture_only': 0,       # Only gesture selected target
                'position_only': 0,      # Only position selected target
                'neither_selected': 0    # Neither selected target
            }
        }
    
    total_trials = 0
    
    for condition, trials in condition_results.items():
        print(f"\n{condition.upper().replace('_', ' ')}:")
        print("-" * 50)
        
        condition_success = 0
        condition_failure = 0
        
        for trial in trials:
            total_trials += 1
            success_status = trial['success_status']
            target_object = trial['target_object']
            P_D = trial['P_D']
            P_G = trial['P_G']
            objects = trial['objects']
            
            # Find target object index
            target_idx = objects.index(target_object)
           
            # Get scores for target object
            position_score = P_D[target_idx]
            gesture_score = P_G[target_idx]
            
            # Determine if each score selected the target (assuming highest score means selection)
            position_selected = position_score == max(P_D)
            gesture_selected = gesture_score == max(P_G)
            
            # Categorize the pattern
            if position_selected and gesture_selected:
                pattern = 'both_selected'
            elif gesture_selected and not position_selected:
                pattern = 'gesture_only'
            elif position_selected and not gesture_selected:
                pattern = 'position_only'
            else:
                pattern = 'neither_selected'
            
            # Add to appropriate counter
            if success_status:
                condition_patterns[condition]['success'][pattern] += 1
                condition_success += 1
            else:
                condition_patterns[condition]['failure'][pattern] += 1
                condition_failure += 1
            
            print(f"  Trial {trial['trial_idx']}: Success={success_status}, "
                  f"Position={position_selected}, Gesture={gesture_selected} -> {pattern}")
        
        # Print condition summary
        print(f"\n  Condition Summary:")
        print(f"    Total Trials: {condition_success + condition_failure}")
        print(f"    Successful: {condition_success}")
        print(f"    Failed: {condition_failure}")
        
        # Print success patterns for this condition
        if condition_success > 0:
            print(f"    Success Patterns:")
            for pattern, count in condition_patterns[condition]['success'].items():
                percentage = (count / condition_success * 100) if condition_success > 0 else 0
                print(f"      {pattern.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
        
        # Print failure patterns for this condition
        if condition_failure > 0:
            print(f"    Failure Patterns:")
            for pattern, count in condition_patterns[condition]['failure'].items():
                percentage = (count / condition_failure * 100) if condition_failure > 0 else 0
                print(f"      {pattern.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
    
    # Print overall summary statistics
    print("\n" + "="*80)
    print("OVERALL SUMMARY STATISTICS")
    print("="*80)
    
    total_success = sum(sum(patterns['success'].values()) for patterns in condition_patterns.values())
    total_failure = sum(sum(patterns['failure'].values()) for patterns in condition_patterns.values())
    
    print(f"\nTotal Trials: {total_trials}")
    print(f"Successful Trials: {total_success}")
    print(f"Failed Trials: {total_failure}")
    
    # Aggregate patterns across all conditions
    overall_success_patterns = {
        'both_selected': 0,
        'gesture_only': 0,
        'position_only': 0,
        'neither_selected': 0
    }
    
    overall_failure_patterns = {
        'both_selected': 0,
        'gesture_only': 0,
        'position_only': 0,
        'neither_selected': 0
    }
    
    for condition, patterns in condition_patterns.items():
        for pattern in overall_success_patterns.keys():
            overall_success_patterns[pattern] += patterns['success'][pattern]
            overall_failure_patterns[pattern] += patterns['failure'][pattern]
    
    print(f"\nOVERALL SUCCESSFUL TRIALS PATTERNS:")
    for pattern, count in overall_success_patterns.items():
        percentage = (count / total_success * 100) if total_success > 0 else 0
        print(f"  {pattern.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
    
    print(f"\nOVERALL FAILED TRIALS PATTERNS:")
    for pattern, count in overall_failure_patterns.items():
        percentage = (count / total_failure * 100) if total_failure > 0 else 0
        print(f"  {pattern.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
    
    # Create visualizations
    create_combined_score_pattern_visualization(condition_patterns, overall_success_patterns, overall_failure_patterns, total_success, total_failure)
    
    return condition_patterns, overall_success_patterns, overall_failure_patterns

def create_score_pattern_visualization(success_patterns, failure_patterns, total_success, total_failure):
    """Create visualization of score selection patterns"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    # Success patterns
    success_labels = ['Both Selected', 'Gesture Only', 'Position Only', 'Neither Selected']
    success_counts = [success_patterns['both_selected'], success_patterns['gesture_only'], 
                     success_patterns['position_only'], success_patterns['neither_selected']]
    success_colors = ['#2ca02c', '#1f77b4', '#ff7f0e', '#d62728']
    
    bars1 = ax1.bar(success_labels, success_counts, color=success_colors, alpha=0.8)
    ax1.set_title('Successful Trials Score Selection Patterns', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Number of Trials', fontsize=12)
    ax1.tick_params(axis='x', rotation=45)
    
    # Add percentage labels on bars
    for bar, count in zip(bars1, success_counts):
        if count > 0:
            percentage = count / total_success * 100 if total_success > 0 else 0
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                    f'{count}\n({percentage:.1f}%)', ha='center', va='bottom', fontsize=12)
    
    # Failure patterns
    failure_labels = ['Both Selected', 'Gesture Only', 'Position Only', 'Neither Selected']
    failure_counts = [failure_patterns['both_selected'], failure_patterns['gesture_only'], 
                     failure_patterns['position_only'], failure_patterns['neither_selected']]
    
    bars2 = ax2.bar(failure_labels, failure_counts, color=success_colors, alpha=0.8)
    ax2.set_title('Failed Trials Score Selection Patterns', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Number of Trials', fontsize=12)
    ax2.tick_params(axis='x', rotation=45)
    
    # Add percentage labels on bars
    for bar, count in zip(bars2, failure_counts):
        if count > 0:
            percentage = count / total_failure * 100 if total_failure > 0 else 0
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                    f'{count}\n({percentage:.1f}%)', ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    
    # Save the plot
    output_dir = Path("outputs/dominance_analysis")
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / "score_selection_patterns.png"
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.show()
    # plt.close()
    
    print(f"\nSaved score selection pattern visualization: {filepath}")

def create_score_pattern_visualization_by_condition(condition_patterns):
    """Create visualization of score selection patterns by condition showing proportions"""
    # Define the desired order for the four conditions
    desired_order = [
        'high_spatial_high_semantic',
        'high_spatial_low_semantic', 
        'low_spatial_high_semantic',
        'low_spatial_low_semantic'
    ]
    
    # Filter conditions to only include those in the desired order and that exist in the data
    conditions = [cond for cond in desired_order if cond in condition_patterns]
    n_conditions = len(conditions)
    
    # Create a 2x2 subplot for the 4 conditions
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    condition_titles = {
        'high_spatial_high_semantic': 'High Spatial + High Semantic',
        'high_spatial_low_semantic': 'High Spatial + Low Semantic',
        'low_spatial_high_semantic': 'Low Spatial + High Semantic',
        'low_spatial_low_semantic': 'Low Spatial + Low Semantic'
    }
    
    for i, condition in enumerate(conditions):
        ax = axes[i]
        
        # Get patterns for this condition
        success_patterns = condition_patterns[condition]['success']
        failure_patterns = condition_patterns[condition]['failure']
        
        # Calculate totals
        total_success = sum(success_patterns.values())
        total_failure = sum(failure_patterns.values())
        total_trials = total_success + total_failure
        
        # Calculate proportions
        success_proportions = [count / total_success * 100 if total_success > 0 else 0 
                              for count in success_patterns.values()]
        failure_proportions = [count / total_failure * 100 if total_failure > 0 else 0 
                              for count in failure_patterns.values()]
        
        # Prepare data for plotting
        patterns = ['Both Selected', 'Gesture Only', 'Position Only', 'Neither Selected']
        success_counts = [success_patterns['both_selected'], success_patterns['gesture_only'], 
                         success_patterns['position_only'], success_patterns['neither_selected']]
        failure_counts = [failure_patterns['both_selected'], failure_patterns['gesture_only'], 
                         failure_patterns['position_only'], failure_patterns['neither_selected']]
        
        # Create grouped bar chart with proportions
        x = np.arange(len(patterns))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, success_proportions, width, label='Success', color='#2ca02c', alpha=0.8)
        bars2 = ax.bar(x + width/2, failure_proportions, width, label='Failure', color='#d62728', alpha=0.8)
        
        # Customize the plot
        ax.set_title(f"{condition_titles.get(condition, condition)}\n(Total: {total_trials} trials)", 
                    fontsize=12, fontweight='bold')
        ax.set_ylabel('Percentage (%)', fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(patterns, rotation=45, ha='right', fontsize=9)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)
        
        # Add value labels on bars (show both count and percentage)
        for bars, counts in [(bars1, success_counts), (bars2, failure_counts)]:
            for bar, count, prop in zip(bars, counts, success_proportions if bars == bars1 else failure_proportions):
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, height + 1, 
                           f'{int(count)}\n({prop:.1f}%)', ha='center', va='bottom', fontsize=8)
        
        # Add summary text with trial counts
        ax.text(0.02, 0.98, f'Success: {total_success} trials\nFailure: {total_failure} trials', 
                transform=ax.transAxes, verticalalignment='top', fontsize=8,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Hide unused subplots if there are fewer than 4 conditions
    for i in range(n_conditions, 4):
        axes[i].set_visible(False)
    
    plt.suptitle('Score Selection Patterns by Ambiguity Condition (Proportions)', fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    # Save the plot
    output_dir = Path("outputs/dominance_analysis")
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / "score_selection_patterns_by_condition.png"
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"\nSaved condition-specific score selection pattern visualization: {filepath}")

def create_combined_score_pattern_visualization(condition_patterns, overall_success_patterns, overall_failure_patterns, total_success, total_failure):
    """Create combined visualization with 5 subplots in a row using stacked bar charts"""
    fig, axes = plt.subplots(1, 5, figsize=(14, 6))
    
    condition_titles = {
        'high_spatial_high_semantic': 'High Spatial + High Semantic',
        'high_spatial_low_semantic': 'High Spatial + Low Semantic',
        'low_spatial_high_semantic': 'Low Spatial + High Semantic',
        'low_spatial_low_semantic': 'Low Spatial + Low Semantic'
    }
    
    # Define patterns and colors using seaborn blue gradient
    # Order should match OPCG_METHODS: ['P', 'G', 'C'] -> Position, Gesture, Combined
    patterns = ['Both', 'Gesture Only', 'Direction Only', 'Neither']
    # Use seaborn's blue gradient palette (similar to the reference image)
    colors = sns.color_palette("Blues", n_colors=4)
    
    # Prepare all data
    all_conditions = ['Overall'] + list(condition_patterns.keys())
    all_data = []
    
    # Add overall data
    overall_success_props = [count / total_success * 100 if total_success > 0 else 0 
                            for count in overall_success_patterns.values()]
    overall_failure_props = [count / total_failure * 100 if total_failure > 0 else 0 
                            for count in overall_failure_patterns.values()]
    
    all_data.append({
        'condition': 'Overall',
        'success': overall_success_props,
        'failure': overall_failure_props,
        'total_success': total_success,
        'total_failure': total_failure
    })
    
    # Define the desired order for the four conditions
    desired_order = [
        'high_spatial_high_semantic',
        'high_spatial_low_semantic', 
        'low_spatial_high_semantic',
        'low_spatial_low_semantic'
    ]
    
    # Add individual condition data in the desired order
    for condition in desired_order:
        if condition not in condition_patterns:
            continue
        success_patterns = condition_patterns[condition]['success']
        failure_patterns = condition_patterns[condition]['failure']
        
        total_success_cond = sum(success_patterns.values())
        total_failure_cond = sum(failure_patterns.values())
        
        success_props = [count / total_success_cond * 100 if total_success_cond > 0 else 0 
                        for count in success_patterns.values()]
        failure_props = [count / total_failure_cond * 100 if total_failure_cond > 0 else 0 
                        for count in failure_patterns.values()]
        
        all_data.append({
            'condition': condition,
            'success': success_props,
            'failure': failure_props,
            'total_success': total_success_cond,
            'total_failure': total_failure_cond
        })
    
    # Create plots for each condition
    for i, data in enumerate(all_data):
        ax = axes[i]
        
        # Create stacked bar chart
        x_pos = 0
        width = 0.2
        
        # Success bar (left)
        bottom = 0
        for j, (pattern, prop) in enumerate(zip(patterns, data['success'])):
            if prop > 0:
                ax.bar(x_pos - width/2, prop, width, bottom=bottom, 
                      color=colors[j], alpha=1.0)
                # Add text label with blue color
                if prop > 3:  # Only show label if bar is tall enough
                    ax.text(x_pos - width/2, bottom + prop/2, f'{prop:.1f}%', 
                           ha='center', va='center', fontsize=8, fontweight='bold',
                           color='#1f4e79')  # Dark blue color
                bottom += prop
        
        # Failure bar (right)
        bottom = 0
        for j, (pattern, prop) in enumerate(zip(patterns, data['failure'])):
            if prop > 0:
                ax.bar(x_pos + width/2, prop, width, bottom=bottom, 
                      color=colors[j], alpha=1.0)
                # Add text label with blue color
                if prop > 3:  # Only show label if bar is tall enough
                    ax.text(x_pos + width/2, bottom + prop/2, f'{prop:.1f}%', 
                           ha='center', va='center', fontsize=8, fontweight='bold',
                           color='#1f4e79')  # Dark blue color
                bottom += prop
        
        # Set labels and title
        ax.set_ylabel('Percentage of Trials', fontsize=12)
        ax.set_xticks([x_pos - width/2, x_pos + width/2])
        ax.set_xticklabels([f'Success\n({data["total_success"]})', f'Failure\n({data["total_failure"]})'], 
                          fontsize=10)
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        
        # Format y-axis ticks with percentage
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0f}%'))
        
        # Set title at the top
        if data['condition'] == 'Overall':
            ax.set_title('Overall Patterns', fontsize=10, fontweight='bold', pad=10)
        else:
            condition_title = condition_titles.get(data['condition'], data['condition'])
            ax.set_title(condition_title, fontsize=10, fontweight='bold', pad=10)
    
    # Create a single legend for all subplots on the right side
    legend_elements = [plt.Rectangle((0,0),1,1, facecolor=colors[i], alpha=0.8, label=pattern) 
                      for i, pattern in enumerate(patterns)]
    fig.legend(handles=legend_elements, loc='center right', bbox_to_anchor=(1.00, 0.5), 
              ncol=1, fontsize=10, frameon=False, title='Dominant Cue', title_fontsize=12, )
    
    # plt.suptitle('Score Selection Patterns: Overall and by Ambiguity Condition (Stacked Bar Charts)', 
    #             fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.subplots_adjust(top=0.85, bottom=0.15, right=0.85, wspace=0.6)
    
    # Save the plot
    output_dir = Path("outputs/dominance_analysis")
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / "combined_score_selection_patterns.png"
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"\nSaved combined score selection pattern visualization: {filepath}")

def main():
    """Main function"""
    print("Analyzing Method C Dominance Scores")
    print(f"Data directories: {DATA_DIRECTORIES}")
    print(f"Method: {METHOD}")
    
    # Check if any data directories exist
    valid_dirs = []
    for data_dir in DATA_DIRECTORIES:
        if os.path.exists(data_dir):
            valid_dirs.append(data_dir)
        else:
            print(f"Warning: Data directory '{data_dir}' not found, skipping...")
    
    if not valid_dirs:
        print("No valid data directories found!")
        return
    
    print(f"Using {len(valid_dirs)} valid directories...")
    
    # Create output directory
    output_dir = Path("outputs/dominance_analysis")
    output_dir.mkdir(exist_ok=True)
    
    # Analyze dominance scores
    print("\nAnalyzing dominance scores...")
    condition_results = analyze_method_c_dominance(valid_dirs)
    
    if not condition_results:
        print("No data found for analysis.")
        return
    
    # Analyze score selection patterns
    print("\nAnalyzing score selection patterns...")
    condition_patterns, overall_success_patterns, overall_failure_patterns = analyze_score_selection_patterns(condition_results)
    
    # Create visualizations
    print("\nCreating visualizations...")
    
    print(f"\nAnalysis completed! Results saved to: {output_dir.absolute()}")

if __name__ == "__main__":
    main()
