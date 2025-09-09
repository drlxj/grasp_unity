#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze average graspingDuration and standard deviation for OPCG methods
"""

import json
import os
import numpy as np
from pathlib import Path
import pandas as pd # Added for CSV saving
import matplotlib.pyplot as plt
import seaborn as sns

# =============================================================================
# CONFIGURATION - 统一配置区域，修改时只需要改这里
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

# 要分析的OPCG方法     
OPCG_METHODS = ['P', 'G', 'C']  # 可选: ['O', 'P', 'C', 'G'] 或任何子集

# 方法描述
METHOD_DESCRIPTIONS = {
    'P': '',
    'G': '', 
    'C': '',
}

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
METHOD_COLORS = {'P': '#ff7f0e', 'G': '#1f77b4', 'C': '#2ca02c', 'O': '#d62728'}

# =============================================================================

def load_trial_data(file_path):
    """Load trial data file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def calculate_intersection(hand_position, hand_direction, center_position):
    plane_z = center_position[2]
    lambda_val = (plane_z - hand_position[2]) / hand_direction[2]

    x = hand_position[0] + lambda_val * hand_direction[0]
    y = hand_position[1] + lambda_val * hand_direction[1]
    z = plane_z 

    return np.array([x, y, z])

def calculate_hand_movement_distance(method_folder_path, trial_idx):
    """Calculate cumulative hand movement distance from record_continual_data"""

    trial_folder = Path(method_folder_path) / "record_continual_data" / str(trial_idx)
    if not trial_folder.exists():
        return None
    
    # Get all JSON files and sort by name
    trial_files = sorted([f for f in trial_folder.iterdir() if f.suffix == '.json'])
    if not trial_files:
        return None
    
    total_distance = 0.0
    previous_position = None
    
    for frame_file in trial_files:

        with open(frame_file, 'r') as f:
            frame_data = json.load(f)
        
        if 'gestureData' in frame_data and 'rootPosition' in frame_data['gestureData']:
            current_position = np.array(frame_data['gestureData']['rootPosition'])
            
            if previous_position is not None:
                total_distance += np.linalg.norm(current_position - previous_position)
            
            previous_position = current_position

    
    return total_distance


def extract_grasping_durations(data, object_init_data, method_folder_path=None):
    """Extract graspingDuration, graspCount, isSuccessful and hand movement distance from trial data"""
    durations = []
    grasp_counts = []
    is_successful = []
    hand_movement_distances = []
    
    # Cache for movement distances to avoid duplicate calculations
    movement_cache = {}
    
    if not data:
        return durations, grasp_counts, is_successful, hand_movement_distances
    
    # Group data by trial_id to get the last duration for each trial
    trial_data = {}
    for trial in data:
        if not isinstance(trial, dict):
            continue
        
        trial_id = trial.get('trialIndex', trial.get('trialId', 0))
        if trial_id > 4:
            continue
        if trial_id not in trial_data:
            trial_data[trial_id] = []
        trial_data[trial_id].append(trial)
    
    # For each trial_id, take the last duration and other data
    for trial_id in sorted(trial_data.keys()):
        trials_for_id = trial_data[trial_id]
        # Take the last trial data for this trial_id
        last_trial = trials_for_id[-1]
        
        # Extract basic data from the last trial
        durations.append(last_trial.get('duration', 0))
        grasp_counts.append(last_trial.get('graspCount', 0))
        is_successful.append(last_trial.get('isSuccessful', False))
        
        # Calculate hand movement distance (only for trials 0-4)
        if method_folder_path and trial_id < 5:
            if trial_id not in movement_cache:
                movement_cache[trial_id] = calculate_hand_movement_distance(method_folder_path, trial_id)
            hand_movement_distances.append(movement_cache[trial_id])
        else:
            hand_movement_distances.append(None)
    
    return durations, grasp_counts, is_successful, hand_movement_distances




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

def analyze_opcg_methods_by_ambiguity(data_directories):
    """Analyze data for OPCG methods by ambiguity conditions from multiple directories"""
    if isinstance(data_directories, str):
        data_directories = [data_directories]
    
    method_data = {}
    
    # Initialize data structure
    for condition in AMBIGUITY_CONDITIONS.keys():
        method_data[condition] = {method: {'durations': [], 'grasp_counts': [], 'is_successful': [], 
            'hand_movement_distances': [], 'subject_id': []} for method in OPCG_METHODS}
    
    count = 0
    for data_dir in data_directories:
        data_dir = Path(data_dir)
        if not data_dir.exists():
            print(f"Warning: Directory '{data_dir}' not found, skipping...")
            continue
            
        print(f"\nProcessing directory: {data_dir}")

        subject_id = data_dir.name
    
        for experiment_folder in data_dir.iterdir():
            if not experiment_folder.is_dir():
                continue
                
            # Classify ambiguity condition
            condition = classify_ambiguity_conditions(experiment_folder.name)
            
            for method_folder in experiment_folder.iterdir():
                if not method_folder.is_dir() or method_folder.name not in OPCG_METHODS:
                    continue
            
                method_name = method_folder.name
                trial_data_path = method_folder / "GraspResults.json"
                
                if not trial_data_path.exists():
                    continue
                    
                data = load_trial_data(trial_data_path)
                if not data:
                    continue
            
                durations, grasp_counts, is_successful, hand_movement_distances = extract_grasping_durations(
                    data, None, method_folder
                )
                
                method_data[condition][method_name]['durations'].extend(durations)
                method_data[condition][method_name]['grasp_counts'].extend(grasp_counts)
                method_data[condition][method_name]['is_successful'].extend(is_successful)
                method_data[condition][method_name]['hand_movement_distances'].extend(hand_movement_distances)
                method_data[condition][method_name]['subject_id'].extend([subject_id] * len(durations))

                count += 1
    print(f"Total trials: {count}")
    
    return method_data

def calculate_statistics_by_ambiguity(method_data_by_ambiguity):
    """Calculate statistics for each method by ambiguity condition"""
    stats_by_ambiguity = {}
    
    # Collect all data for overall statistics
    overall_data = {method: {'durations': [], 'completion_rates': [], 'subject_ids': []} for method in OPCG_METHODS}
    
    for condition, method_data in method_data_by_ambiguity.items():
        stats = {}
        
        for method, data in method_data.items():
            durations = data['durations']
            grasp_counts = data['grasp_counts']
            is_successful = data['is_successful']
            hand_movement_distances = data['hand_movement_distances']
            subject_ids = data['subject_id']
            
            if not durations:
                stats[method] = {'count': 0, 'total_grasps': 0, 'mean_duration': None, 'std_duration': None, 
                               'trial_completion_rate': None, 'mean_hand_movement_distance': None, 
                               'std_hand_movement_distance': None, 'valid_distance_count': 0,
                               'subject_std_duration': None, 'subject_std_completion_rate': None}
                continue
            
            # Calculate trial completion rate: percentage of successful trials
            # Trial completion rate = number of successful trials / total trials
            successful_trials = sum(is_successful)
            total_trials = len(is_successful)
            trial_completion_rate = successful_trials / total_trials if total_trials > 0 else 0.0
            
            # Calculate hand movement distance statistics
            valid_distances = [d for d in hand_movement_distances if d is not None]
            
            # Calculate total number of grasps across all trials
            total_grasps = sum(grasp_counts)
            
            # Calculate subject-level statistics for this condition
            subject_stats = {}
            for i, subject_id in enumerate(subject_ids):
                if subject_id not in subject_stats:
                    subject_stats[subject_id] = {'durations': [], 'completion_rates': []}
                subject_stats[subject_id]['durations'].append(durations[i])
                subject_stats[subject_id]['completion_rates'].append(is_successful[i])
            
            # Calculate mean duration and completion rate per subject
            subject_mean_durations = [np.mean(data['durations']) for data in subject_stats.values()]
            subject_completion_rates = [np.mean(data['completion_rates']) for data in subject_stats.values()]
            
            # Calculate standard deviation across subjects
            subject_std_duration = np.std(subject_mean_durations) if len(subject_mean_durations) > 1 else 0.0
            subject_std_completion_rate = np.std(subject_completion_rates) if len(subject_completion_rates) > 1 else 0.0
            
            stats[method] = {
                'count': len(durations),  # Number of trials
                'total_grasps': total_grasps,  # Total number of grasp attempts
                'mean_duration': np.mean(durations),
                'std_duration': np.std(durations),
                'trial_completion_rate': trial_completion_rate,
                'mean_hand_movement_distance': np.mean(valid_distances) if valid_distances else None,
                'std_hand_movement_distance': np.std(valid_distances) if valid_distances else None,
                'valid_distance_count': len(valid_distances),
                'subject_std_duration': subject_std_duration,
                'subject_std_completion_rate': subject_std_completion_rate
            }
            
            # Accumulate data for overall statistics
            overall_data[method]['durations'].extend(durations)
            overall_data[method]['completion_rates'].extend(is_successful)
            overall_data[method]['subject_ids'].extend(subject_ids)
        
        stats_by_ambiguity[condition] = stats
    
    # Calculate overall performance statistics
    overall_stats = {}
    for method, data in overall_data.items():
        if data['durations']:
            # Calculate subject-level means for overall statistics
            subject_stats = {}
            for i, subject_id in enumerate(data['subject_ids']):
                if subject_id not in subject_stats:
                    subject_stats[subject_id] = {'durations': [], 'completion_rates': []}
                subject_stats[subject_id]['durations'].append(data['durations'][i])
                subject_stats[subject_id]['completion_rates'].append(data['completion_rates'][i])
            
            subject_mean_durations = [np.mean(data['durations']) for data in subject_stats.values()]
            subject_completion_rates = [np.mean(data['completion_rates']) for data in subject_stats.values()]
            
            overall_stats[method] = {
                'count': len(data['durations']),
                'total_grasps': 0,  # Not available in overall data
                'mean_duration': np.mean(data['durations']),
                'std_duration': np.std(data['durations']),
                'subject_std_duration': np.std(subject_mean_durations) if len(subject_mean_durations) > 1 else 0.0,
                'trial_completion_rate': np.mean(data['completion_rates']),
                'subject_std_completion_rate': np.std(subject_completion_rates) if len(subject_completion_rates) > 1 else 0.0,
                'mean_hand_movement_distance': None,  # Not available in overall data
                'std_hand_movement_distance': None,  # Not available in overall data
                'valid_distance_count': 0  # Not available in overall data
            }
    
    # Add overall statistics to the results
    stats_by_ambiguity['overall'] = overall_stats
    
    return stats_by_ambiguity

def print_statistics_by_ambiguity(stats_by_ambiguity):
    """Print statistics results by ambiguity condition"""
    print("\n" + "="*60)
    print("OPCG METHODS PERFORMANCE ANALYSIS BY AMBIGUITY CONDITIONS")
    print("="*60)
    
    for condition, stats in stats_by_ambiguity.items():
        print(f"\n{condition.upper().replace('_', ' ')}:")
        
        for method in OPCG_METHODS:
            if method not in stats:
                continue
                
            stat = stats[method]
            print(f"  Method {method}:")
            
            if stat['count'] == 0:
                print("    No data")
                continue
                
            print(f"    Trials: {stat['count']}")
            print(f"    Total Grasps: {stat['total_grasps']}")
            print(f"    Duration: {stat['mean_duration']:.3f}±{stat['std_duration']:.3f}s")
            print(f"    Trial Completion Rate: {stat['trial_completion_rate']:.3f}")
            
            if stat['mean_hand_movement_distance'] is not None:
                print(f"    Movement: {stat['mean_hand_movement_distance']:.3f}±{stat['std_hand_movement_distance']:.3f} units")
            else:
                print("    Movement: No data")



def save_ambiguity_analysis_to_csv(stats_by_ambiguity, output_dir="outputs"):
    """Save ambiguity analysis results to CSV"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Create summary DataFrame
    summary_data = []
    for condition, stats in stats_by_ambiguity.items():
        for method, stat in stats.items():
            summary_data.append({
                'ambiguity_condition': condition,
                'method': method,
                'trial_count': stat['count'],
                'total_grasps': stat['total_grasps'],
                'mean_duration': stat['mean_duration'],
                'std_duration': stat['std_duration'],
                'trial_completion_rate': stat['trial_completion_rate'],
                'mean_hand_movement_distance': stat['mean_hand_movement_distance'],
                'std_hand_movement_distance': stat['std_hand_movement_distance'],
                'valid_distance_count': stat['valid_distance_count']
            })
    
    summary_df = pd.DataFrame(summary_data)
    summary_file = output_dir / "ambiguity_analysis_summary.csv"
    summary_df.to_csv(summary_file, index=False)
    print(f"Saved: {summary_file}")

def save_method_data_to_csv(method_data_by_ambiguity, output_dir="outputs"):
    """Convert method_data_by_ambiguity to DataFrame and save to CSV"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Create detailed DataFrame with all raw data
    detailed_data = []
    for condition, method_data in method_data_by_ambiguity.items():
        for method, data in method_data.items():
            # Get all the raw data lists
            subject_id = data['subject_id']
            durations = data['durations']
            grasp_counts = data['grasp_counts']
            is_successful = data['is_successful']
            hand_movement_distances = data['hand_movement_distances']
            
            # Create one row for each trial
            max_trials = max(len(durations), len(grasp_counts), len(is_successful), len(hand_movement_distances))
            
            # Extract spatial and semantic ambiguity from condition
            spatial_ambiguity = 'High' if 'high_spatial' in condition else 'Low'
            semantic_ambiguity = 'High' if 'high_semantic' in condition else 'Low'
            
            for i in range(max_trials):
                row = {
                    'subject_id': subject_id[i],
                    'condition': condition,
                    'spatial_ambiguity': spatial_ambiguity,
                    'semantic_ambiguity': semantic_ambiguity,
                    'method': method,
                    'trial_index': i,
                    'duration': durations[i] if i < len(durations) else None,
                    'grasp_count': grasp_counts[i] if i < len(grasp_counts) else None,
                    'is_successful': is_successful[i] if i < len(is_successful) else None,
                    'hand_movement_distance': hand_movement_distances[i] if i < len(hand_movement_distances) else None
                }
                detailed_data.append(row)
    
    detailed_df = pd.DataFrame(detailed_data)
    detailed_file = output_dir / "method_data_detailed.csv"
    detailed_df.to_csv(detailed_file, index=False)
    print(f"Saved detailed data: {detailed_file}")
    
    return detailed_df

    
def plot_methods_comparison_by_ambiguity(stats_by_ambiguity):
    """Plot METHOD x SPATIAL AMBIGUITY x SEMANTIC AMBIGUITY interaction plots using seaborn catplot"""
    # Prepare data for seaborn
    data_list = []
    for condition, stats in stats_by_ambiguity.items():
        spatial = 'High' if 'high_spatial' in condition else 'Low'
        semantic = 'High' if 'high_semantic' in condition else 'Low'
        
        for method in OPCG_METHODS:
            if method in stats and stats[method]['count'] > 0:
                data_list.append({
                    'method': method,
                    'spatial_ambiguity': spatial,
                    'semantic_ambiguity': semantic,
                    'duration': stats[method]['mean_duration'],
                    'duration_std': stats[method]['std_duration'],
                    'completion_rate': stats[method]['trial_completion_rate'],
                    'movement_distance': stats[method]['mean_hand_movement_distance'] or 0,
                    'movement_std': stats[method]['std_hand_movement_distance'] or 0
                })
    
    df = pd.DataFrame(data_list)
    df.to_csv('opcg_ambiguity_data.csv', index=False)
    # df = pd.read_csv('opcg_ambiguity_data.csv')
    
    # # Set seaborn style
    # sns.set_style("whitegrid")
    
    # Create three separate catplots for each metric
    metrics = [
        ('duration', 'Duration (seconds)', ''),
        ('completion_rate', 'Trial Completion Rate (%)', ''),
        # ('movement_distance', 'Hand Trajectory Length (meters)', 'Hand Trajectory Length')
    ]
    
    # Create separate figures for each metric
    for idx, (metric, ylabel, title) in enumerate(metrics):
        # Create figure with larger size and better spacing
        fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(12, 4), 
                                               gridspec_kw={'width_ratios': [1, 4]})
        
        # Add more space between subplots and leave room for legend
        plt.subplots_adjust(wspace=0.3, left=0.08, right=0.88, top=0.85, bottom=0.15)
        
        # Left subplot: Overall performance across all conditions
        ax_left.set_title('Overall Performance', fontsize=14, fontweight='bold', pad=5)
        
        # Get overall performance statistics from stats_by_ambiguity
        overall_stats = stats_by_ambiguity.get('overall', {})
        
        # Create bar plot for overall performance - use OPCG_METHODS order
        methods = [method for method in OPCG_METHODS if method in overall_stats]
        means = []
        stds = []
        
        for method in methods:
            means.append(overall_stats[method]['mean_duration'])
            stds.append(overall_stats[method]['subject_std_duration'])
        colors = [METHOD_COLORS[method] for method in methods]
        
        # Create bars without error bars first
        bars = ax_left.bar(range(len(methods)), means, color=colors, alpha=0.8)
        
        # Add error bars with matching colors
        for i, (bar, std, color) in enumerate(zip(bars, stds, colors)):
            ax_left.errorbar(bar.get_x() + bar.get_width()/2, bar.get_height(), 
                            yerr=std, fmt='none', color=color, capsize=5, capthick=2)
        
        # Customize left subplot
        ax_left.set_xlabel('Method', fontsize=14, fontweight='bold')
        ax_left.set_ylabel(ylabel, fontsize=14, fontweight='bold')
        ax_left.set_xticks(range(len(methods)))
        # Create labels with 'P' changed to 'D'
        method_labels = ['D' if method == 'P' else method for method in methods]
        ax_left.set_xticklabels(method_labels, fontsize=12)
        ax_left.grid(True, alpha=0.3)
        ax_left.tick_params(axis='y', labelsize=12)
        
        # Expand Y-axis for overall performance chart
        y_max = ax_left.get_ylim()[1]
        ax_left.set_ylim(ax_left.get_ylim()[0], y_max * 1.2)
        
        # Use the right subplot for the original interaction plot
        ax = ax_right
        
        # Create catplot for this metric with both spatial and semantic facets
        g = sns.catplot(data=df, x='semantic_ambiguity', y=metric, hue='method', 
                       col='spatial_ambiguity', kind='bar', 
                       palette=[METHOD_COLORS[m] for m in OPCG_METHODS],
                       capsize=0.1, errwidth=2, height=4, aspect=0.6, width=0.6)
        
        # Get the catplot axes
        catplot_axes = g.axes.flatten()
        
        # Clear the current subplot
        ax.clear()

        # Set background colors for spatial ambiguity groups (behind bars)
        # High Spatial: covers groups 1 and 2 (centers at 1.0 and 1.8)
        # Low Spatial: covers groups 3 and 4 (centers at 2.6 and 3.4)
        ax.axvspan(0.5, 2.2, alpha=0.15, color='lightgray', label='High Spatial', zorder=0)
        ax.axvspan(2.2, 3.8, alpha=0.15, color='dimgray', label='Low Spatial', zorder=0)
        
        # Copy content from catplot to our subplot
        for i, catplot_ax in enumerate(catplot_axes):
            # Get the bars from catplot
            for container_idx, container in enumerate(catplot_ax.containers):
                # Get method name from container index
                method = OPCG_METHODS[container_idx] if container_idx < len(OPCG_METHODS) else 'Unknown'
                
                for bar in container:
                    x = bar.get_x()
                    y = bar.get_height()
                    width = bar.get_width()
                    color = bar.get_facecolor()
                    
                    # Adjust x position based on spatial ambiguity and semantic ambiguity
                    # i=0: High Spatial, i=1: Low Spatial
                    # x=0: Low Semantic, x=1: High Semantic
                    if i == 0:  # High Spatial
                        base_x = 1.0 if x < 0.5 else 1.8  # Low Semantic=1.0, High Semantic=1.8
                    else:  # Low Spatial  
                        base_x = 2.6 if x < 0.5 else 3.4  # Low Semantic=2.6, High Semantic=3.4
                    
                    # Add offset for method grouping (P, G, C) - make bars touch each other
                    method_offset = {'P': -width, 'G': 0, 'C': width}.get(method, 0)
                    adjusted_x = base_x + method_offset
                    
                    # Create bar in our subplot (in front of background)
                    ax.bar(adjusted_x, y, width, color=color, alpha=0.8, zorder=2)
                    
                    # Determine spatial and semantic ambiguity based on position
                    if i == 0:  # High Spatial
                        if x < 0.5:  # Low Semantic
                            spatial_ambiguity = 'High'
                            semantic_ambiguity = 'High'
                        else:  # High Semantic
                            spatial_ambiguity = 'High'
                            semantic_ambiguity = 'Low'
                    else:  # Low Spatial
                        if x < 0.5:  # Low Semantic
                            spatial_ambiguity = 'Low'
                            semantic_ambiguity = 'High'
                        else:  # High Semantic
                            spatial_ambiguity = 'Low'
                            semantic_ambiguity = 'Low'
                    
                    # Add error bars using subject-level standard deviation
                    if metric == 'duration':
                        # Get the corresponding subject std value for this method and condition
                        condition_key = f"{spatial_ambiguity.lower()}_spatial_{semantic_ambiguity.lower()}_semantic"
                        if condition_key in stats_by_ambiguity and method in stats_by_ambiguity[condition_key]:
                            error_value = stats_by_ambiguity[condition_key][method]['subject_std_duration']
                            if error_value is not None:
                                ax.errorbar(adjusted_x, y, yerr=error_value, fmt='none', 
                                          color=color, capsize=3, capthick=1, zorder=3)
                    elif metric == 'completion_rate':
                        # Get the corresponding subject std value for this method and condition
                        condition_key = f"{spatial_ambiguity.lower()}_spatial_{semantic_ambiguity.lower()}_semantic"
                        if condition_key in stats_by_ambiguity and method in stats_by_ambiguity[condition_key]:
                            error_value = stats_by_ambiguity[condition_key][method]['subject_std_completion_rate']
                            if error_value is not None:
                                ax.errorbar(adjusted_x, y, yerr=error_value, fmt='none', 
                                          color=color, capsize=3, capthick=1, zorder=3)
                    elif metric == 'movement_distance':
                        # For movement_distance, use the original std since we don't have subject-level std for this metric
                        method_data = df[(df['method'] == method) & 
                                       (df['spatial_ambiguity'] == spatial_ambiguity) & 
                                       (df['semantic_ambiguity'] == semantic_ambiguity)]
                        if not method_data.empty:
                            error_value = method_data['movement_std'].iloc[0]
                            ax.errorbar(adjusted_x, y, yerr=error_value, fmt='none', 
                                      color=color, capsize=3, capthick=1, zorder=3)
        
        # Customize the subplot
        ax.set_title('Performance under 4 Ambiguity Conditions', fontsize=14, fontweight='bold', pad=5)
        if ylabel == 'Duration (seconds)':
            ylabel = 'Selection Time (seconds)'
        ax.set_ylabel(ylabel, fontsize=16, fontweight='bold')
        ax.set_xlabel('Semantic Ambiguity', fontsize=16, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Set x-axis labels - 4 ticks representing the 4 combinations
        # Calculate center positions for each group of 3 bars
        # High Spatial: Low Semantic (1.0), High Semantic (1.8)
        # Low Spatial: Low Semantic (2.6), High Semantic (3.4)
        ax.set_xticks([1.0, 1.8, 2.6, 3.4])  # Center positions for each group
        ax.set_xticklabels(['High Semantic', 'Low Semantic', 
                           'High Semantic', 'Low Semantic'], fontsize=14)
        
        # Set x-axis limits to be more compact
        ax.set_xlim(0.5, 3.8)
        
        # Set y-axis tick labels font size
        ax.tick_params(axis='y', labelsize=14)
        
        # Expand Y-axis to make room for labels at the top
        y_max = ax.get_ylim()[1]
        ax.set_ylim(ax.get_ylim()[0], y_max * 1.4)
        
        # For completion rate, set y-axis ticks to only show up to 1.0
        if metric == 'completion_rate':
            # Set y-axis ticks to show 0.0, 0.2, 0.4, 0.6, 0.8, 1.0
            ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
            ax.set_yticklabels(['0.0', '0.2', '0.4', '0.6', '0.8', '1.0'])
        
        # Add spatial ambiguity labels at the top of the chart (without boxes)
        ax.text(1.4, y_max * 1.25, 'High Spatial Ambiguity', 
                ha='center', va='bottom', fontsize=16, fontweight='bold')
        ax.text(3.0, y_max * 1.25, 'Low Spatial Ambiguity', 
                ha='center', va='bottom', fontsize=16, fontweight='bold')
        
        # Add shared legend outside the plot area, closer to the right plot
        legend_elements = [plt.Rectangle((0,0),1,1, facecolor=METHOD_COLORS[m], alpha=0.8, 
                               label=f"{'D' if m == 'P' else m}") 
                          for m in OPCG_METHODS]
        fig.legend(handles=legend_elements, loc='center right', bbox_to_anchor=(0.98, 0.5), 
                 fontsize=12, frameon=True, ncol=1)
        
        # Close the catplot to free memory
        plt.close(g.fig)
        
        # Save and show each individual plot
        filename = f"opcg_methods_interaction_effects_{metric}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Saved: {filename}")
        plt.show()

def analyze_ambiguity_performance(data_directories):
    """Main function for ambiguity analysis"""
    print("Starting ambiguity-based performance analysis...")
    
    # Analyze data by ambiguity conditions
    method_data_by_ambiguity = analyze_opcg_methods_by_ambiguity(data_directories)

    # Convert method_data_by_ambiguity to DataFrame and save
    detailed_df = save_method_data_to_csv(method_data_by_ambiguity)
    
    # Calculate statistics
    stats_by_ambiguity = calculate_statistics_by_ambiguity(method_data_by_ambiguity)
    
    # Print results
    print_statistics_by_ambiguity(stats_by_ambiguity)
    
    plot_methods_comparison_by_ambiguity(stats_by_ambiguity)
    
    # Save to CSV
    save_ambiguity_analysis_to_csv(stats_by_ambiguity)
    
    return stats_by_ambiguity

def main_ambiguity_analysis():
    """Main function for ambiguity analysis"""
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
    
    print(f"Starting ambiguity analysis with {len(valid_dirs)} directories...")
    
    # Run ambiguity analysis
    analyze_ambiguity_performance(valid_dirs)

if __name__ == "__main__":
    print("OPCG Performance Analysis Tool")
    main_ambiguity_analysis()