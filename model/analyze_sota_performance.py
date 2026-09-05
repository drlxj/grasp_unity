#!/usr/bin/https://accounts.google.com/SignOutOptions?hl=en&continue=https://docs.google.com/presentation/d/1_KrTyE3WFBsdZuhLSb1fuYhy1XPtLvz5vAz4n0i_Rzs/edit%3Fslide%3Did.g3a2d7d9a16e_0_0&ec=GBRAmQIenv python3
# -*- coding: utf-8 -*-
"""
Analyze average graspingDuration and standard deviation for SOTA methods (A: BubbleRay, E: Expand, C: Point & Grasp)
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

    r"C:\Users\Researcher\grasping-unity\user_study_data\new1",
    r"C:\Users\Researcher\grasping-unity\user_study_data\new2",
    r"C:\Users\Researcher\grasping-unity\user_study_data\new3",
    r"C:\Users\Researcher\grasping-unity\user_study_data\new4_Copy",
    r"C:\Users\Researcher\grasping-unity\user_study_data\new5",
    r"C:\Users\Researcher\grasping-unity\user_study_data\new6_Copy",
    r"C:\Users\Researcher\grasping-unity\user_study_data\new7",
    r"C:\Users\Researcher\grasping-unity\user_study_data\new8",
    r"C:\Users\Researcher\grasping-unity\user_study_data\new9",

    r"C:\Users\Researcher\grasping-unity\user_study_data\new10",

    r"C:\Users\Researcher\grasping-unity\user_study_data\new11_Copy",
    r"C:\Users\Researcher\grasping-unity\user_study_data\new12_Copy",
]

# 要分析的SOTA方法     
OPCG_METHODS = ['A', 'E', 'C']  # A: BubbleRay, E: Expand, C: Point & Grasp

# 方法描述
METHOD_DESCRIPTIONS = {
    'A': 'BubbleRay',
    'E': 'Expand', 
    'C': 'Point & Grasp',
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

# 方法颜色方案 - 使用协调的三色调色板（与绿色形成互补平衡，色盲友好）
METHOD_COLORS = {'A': '#A72703', 'E': '#FCB53B', 'C': '#2ca02c'}  # A: 深紫色, E: 粉红色, C: 绿色

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

def extract_grasping_durations(data, method_folder_path=None):
    """Extract graspingDuration, graspCount, isSuccessful, hand movement distance from trial data"""
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
    """Analyze data for SOTA methods by ambiguity conditions from multiple directories"""
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
                    data, method_folder
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
    print("SOTA METHODS PERFORMANCE ANALYSIS BY AMBIGUITY CONDITIONS")
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
    detailed_file = output_dir / "method_data_detailed_sota.csv"
    detailed_df.to_csv(detailed_file, index=False)
    print(f"Saved detailed data: {detailed_file}")
    
    return detailed_df

    
def plot_methods_comparison_by_ambiguity(stats_by_ambiguity):
    """Plot METHOD x SPATIAL AMBIGUITY x SEMANTIC AMBIGUITY interaction plots using seaborn catplot"""
    # Prepare data for seaborn
    data_list = []
    for condition, stats in stats_by_ambiguity.items():
        # Skip 'overall' condition - it's only for the left subplot, not for interaction plots
        if condition == 'overall':
            continue
            
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
    
    # # Set seaborn style
    # sns.set_style("whitegrid")
    
    # Create three separate catplots for each metric
    metrics = [
        ('duration', 'Selection Time [seconds]', ''),
        ('completion_rate', 'Trial Completion Rate', ''),
    ]
    
    # Create separate figures for each metric
    for idx, (metric, ylabel, title) in enumerate(metrics):
        # Create figure with larger size and better spacing
        fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(16, 4), 
                                               gridspec_kw={'width_ratios': [2, 4]})
        
        # Add more space between subplots and leave room for legend
        plt.subplots_adjust(wspace=0.3, left=0.08, right=0.8, top=0.85, bottom=0.2)
        
        # Left subplot: Overall performance across all conditions
        ax_left.set_title('Overall Performance', fontsize=14, fontweight='bold', pad=5)
        
        # Get overall performance statistics from stats_by_ambiguity
        overall_stats = stats_by_ambiguity.get('overall', {})
        
        # Create bar plot for overall performance - use OPCG_METHODS order
        methods = [method for method in OPCG_METHODS if method in overall_stats]
        means = []
        stds = []
        
        for method in methods:
            if metric == 'duration':
                means.append(overall_stats[method]['mean_duration'])
                stds.append(overall_stats[method]['subject_std_duration'])
            elif metric == 'completion_rate':
                means.append(overall_stats[method]['trial_completion_rate'])
                stds.append(overall_stats[method]['subject_std_completion_rate'])
            elif metric == 'movement_distance':
                means.append(overall_stats[method]['mean_hand_movement_distance'] or 0)
                stds.append(overall_stats[method]['std_hand_movement_distance'] or 0)
         
        colors = [METHOD_COLORS[method] for method in methods]
        
        # Check if we have data to plot
        if not means or not stds:
            print(f"Warning: No data available for metric '{metric}' in overall_stats")
            ax_left.text(0.5, 0.5, f'No data available for {metric}', 
                        ha='center', va='center', transform=ax_left.transAxes)
            continue
        
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
        # 定义方法标签映射（与图例保持一致）
        method_label_map = {'A': 'BubbleRay', 'E': 'Expand', 'C': 'Point & Grasp'}
        method_labels = [method_label_map.get(method, method) for method in methods]
        ax_left.set_xticklabels(method_labels, fontsize=12, rotation=0)
        ax_left.grid(True, alpha=0.3)
        ax_left.tick_params(axis='y', labelsize=12)
        
        # Format y-axis as percentage for completion_rate
        if metric == 'completion_rate':
            ax_left.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x*100:.0f}%'))
        
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
                    
                    # Determine spatial and semantic ambiguity based on position
                    # i=0: High Spatial, i=1: Low Spatial
                    # In seaborn catplot, categories are ordered alphabetically: 'High' < 'Low'
                    # So x=0 = 'High' (High Semantic), x=1 = 'Low' (Low Semantic)
                    if i == 0:  # High Spatial
                        if x < 0.5:  # x=0 = 'High' (High Semantic)
                            spatial_ambiguity = 'High'
                            semantic_ambiguity = 'High'
                        else:  # x=1 = 'Low' (Low Semantic)
                            spatial_ambiguity = 'High'
                            semantic_ambiguity = 'Low'
                    else:  # Low Spatial
                        if x < 0.5:  # x=0 = 'High' (High Semantic)
                            spatial_ambiguity = 'Low'
                            semantic_ambiguity = 'High'
                        else:  # x=1 = 'Low' (Low Semantic)
                            spatial_ambiguity = 'Low'
                            semantic_ambiguity = 'Low'
                    
                    # Adjust x position based on spatial ambiguity and semantic ambiguity
                    # High Spatial: High Semantic at 1.0, Low Semantic at 1.8
                    # Low Spatial: High Semantic at 2.6, Low Semantic at 3.4
                    if i == 0:  # High Spatial
                        base_x = 1.0 if semantic_ambiguity == 'High' else 1.8  # High Semantic=1.0, Low Semantic=1.8
                    else:  # Low Spatial  
                        base_x = 2.6 if semantic_ambiguity == 'High' else 3.4  # High Semantic=2.6, Low Semantic=3.4
                    
                    # Add offset for method grouping (A, E, C) - make bars touch each other
                    method_offset = {'A': -width, 'E': 0, 'C': width}.get(method, 0)
                    adjusted_x = base_x + method_offset
                    
                    # Create bar in our subplot (in front of background)
                    ax.bar(adjusted_x, y, width, color=color, alpha=0.8, zorder=2)
                    
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
        
        # Customize the subplot
        ax.set_title('Performance under 4 Ambiguity Conditions', fontsize=14, fontweight='bold', pad=5)
        
        ax.set_ylabel(ylabel, fontsize=16, fontweight='bold')
        ax.set_xlabel('Semantic Ambiguity', fontsize=16, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Format y-axis as percentage for completion_rate
        if metric == 'completion_rate':
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x*100:.0f}%'))
        
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
            # Format y-axis as percentage
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x*100:.0f}%'))
        
        # Add spatial ambiguity labels at the top of the chart (without boxes)
        ax.text(1.4, y_max * 1.25, 'High Spatial Ambiguity', 
                ha='center', va='bottom', fontsize=16, fontweight='bold')
        ax.text(3.0, y_max * 1.25, 'Low Spatial Ambiguity', 
                ha='center', va='bottom', fontsize=16, fontweight='bold')
        
        # Add shared legend outside the plot area, closer to the right plot
        # 定义方法标签映射
        method_labels = {'A': 'BubbleRay', 'E': 'Expand', 'C': 'Point & Grasp'}
        legend_elements = [plt.Rectangle((0,0),1,1, facecolor=METHOD_COLORS[m], alpha=0.8, 
                               label=method_labels.get(m, m)) 
                          for m in OPCG_METHODS]
        fig.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(0.82, 0.5), 
                 fontsize=10, frameon=True, ncol=1)
        
        # Close the catplot to free memory
        plt.close(g.fig)
        
        # Save and show each individual plot
        filename = f"sota_interaction_effects_{metric}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Saved: {filename}")
        plt.show()

def calculate_spatial_only_statistics(method_data_by_ambiguity):
    """Calculate statistics grouped only by spatial ambiguity (merging semantic conditions)"""
    spatial_only_data = {
        'high_spatial': {method: {'durations': [], 'grasp_counts': [], 'is_successful': [], 
            'hand_movement_distances': [], 'subject_id': []} for method in OPCG_METHODS},
        'low_spatial': {method: {'durations': [], 'grasp_counts': [], 'is_successful': [], 
            'hand_movement_distances': [], 'subject_id': []} for method in OPCG_METHODS}
    }
    
    # Merge data by spatial ambiguity
    for condition, method_data in method_data_by_ambiguity.items():
        if condition == 'overall':
            continue
            
        spatial = 'high_spatial' if 'high_spatial' in condition else 'low_spatial'
        
        for method in OPCG_METHODS:
            if method in method_data:
                spatial_only_data[spatial][method]['durations'].extend(method_data[method]['durations'])
                spatial_only_data[spatial][method]['grasp_counts'].extend(method_data[method]['grasp_counts'])
                spatial_only_data[spatial][method]['is_successful'].extend(method_data[method]['is_successful'])
                spatial_only_data[spatial][method]['hand_movement_distances'].extend(method_data[method]['hand_movement_distances'])
                spatial_only_data[spatial][method]['subject_id'].extend(method_data[method]['subject_id'])
    
    # Calculate statistics for each spatial condition
    spatial_stats = {}
    for spatial_condition, method_data in spatial_only_data.items():
        stats = {}
        
        for method, data in method_data.items():
            durations = data['durations']
            grasp_counts = data['grasp_counts']
            is_successful = data['is_successful']
            hand_movement_distances = data['hand_movement_distances']
            subject_ids = data['subject_id']
            
            if not durations:
                stats[method] = {'count': 0, 'mean_duration': None, 'std_duration': None, 
                               'trial_completion_rate': None, 'subject_std_duration': None, 
                               'subject_std_completion_rate': None}
                continue
            
            # Calculate trial completion rate
            successful_trials = sum(is_successful)
            total_trials = len(is_successful)
            trial_completion_rate = successful_trials / total_trials if total_trials > 0 else 0.0
            
            # Calculate subject-level statistics
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
                'count': len(durations),
                'mean_duration': np.mean(durations),
                'std_duration': np.std(durations),
                'trial_completion_rate': trial_completion_rate,
                'subject_std_duration': subject_std_duration,
                'subject_std_completion_rate': subject_std_completion_rate
            }
        
        spatial_stats[spatial_condition] = stats
    
    return spatial_stats

def plot_methods_comparison_by_spatial_only(stats_by_ambiguity, method_data_by_ambiguity):
    """Plot comparison of three interaction techniques under high spatial and low spatial conditions only"""
    # Calculate spatial-only statistics
    spatial_stats = calculate_spatial_only_statistics(method_data_by_ambiguity)
    
    # Prepare data for plotting
    data_list = []
    for spatial_condition, stats in spatial_stats.items():
        spatial_label = 'High Spatial' if spatial_condition == 'high_spatial' else 'Low Spatial'
        
        for method in OPCG_METHODS:
            if method in stats and stats[method]['count'] > 0:
                data_list.append({
                    'method': method,
                    'spatial_ambiguity': spatial_label,
                    'duration': stats[method]['mean_duration'],
                    'completion_rate': stats[method]['trial_completion_rate'],
                    'subject_std_duration': stats[method]['subject_std_duration'],
                    'subject_std_completion_rate': stats[method]['subject_std_completion_rate']
                })
    
    df = pd.DataFrame(data_list)
    
    # Create plots for each metric
    metrics = [
        ('duration', 'Selection Time [seconds]'),
        ('completion_rate', 'Trial Completion Rate'),
    ]
    
    for metric, ylabel in metrics:
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        # Set up x positions
        spatial_positions = {'High Spatial': 1.0, 'Low Spatial': 2.0}
        method_offsets = {'A': -0.25, 'E': 0.0, 'C': 0.25}
        bar_width = 0.25
        
        # Plot bars for each method and spatial condition
        for spatial_label in ['High Spatial', 'Low Spatial']:
            x_base = spatial_positions[spatial_label]
            
            for method in OPCG_METHODS:
                method_data = df[(df['method'] == method) & (df['spatial_ambiguity'] == spatial_label)]
                
                if not method_data.empty:
                    x_pos = x_base + method_offsets[method]
                    y_value = method_data[metric].values[0]
                    color = METHOD_COLORS[method]
                    
                    # Draw bar
                    ax.bar(x_pos, y_value, bar_width, color=color, alpha=0.8, label=method if spatial_label == 'High Spatial' else '')
                    
                    # Add error bars using subject-level standard deviation
                    if metric == 'duration':
                        error_value = method_data['subject_std_duration'].values[0]
                    else:  # completion_rate
                        error_value = method_data['subject_std_completion_rate'].values[0]
                    
                    if error_value is not None and not np.isnan(error_value):
                        ax.errorbar(x_pos, y_value, yerr=error_value, fmt='none', 
                                  color=color, capsize=5, capthick=2, zorder=3)
        
        # Customize plot
        ax.set_xlabel('Spatial Ambiguity', fontsize=16, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=16, fontweight='bold')
        ax.set_xticks([1.0, 2.0])
        ax.set_xticklabels(['High Spatial', 'Low Spatial'], fontsize=14)
        ax.grid(True, alpha=0.3, axis='y')
        ax.tick_params(axis='y', labelsize=12)
        
        # Format y-axis as percentage for completion_rate
        if metric == 'completion_rate':
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x*100:.0f}%'))
            ax.set_ylim(0, 1.0)
            ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        
        # Set x-axis limits
        ax.set_xlim(0.4, 2.6)
        
        # Add legend
        method_labels = {'A': 'BubbleRay', 'E': 'Expand', 'C': 'Point & Grasp'}
        legend_elements = [plt.Rectangle((0,0),1,1, facecolor=METHOD_COLORS[m], alpha=0.8, 
                               label=method_labels.get(m, m)) 
                          for m in OPCG_METHODS]
        ax.legend(handles=legend_elements, loc='best', fontsize=12, frameon=True)
        
        # Save and show
        filename = f"sota_spatial_comparison_{metric}.png"
        plt.tight_layout()
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
    
    # Plot spatial-only comparison
    plot_methods_comparison_by_spatial_only(stats_by_ambiguity, method_data_by_ambiguity)
    
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
    print("SOTA Performance Analysis Tool")
    main_ambiguity_analysis()