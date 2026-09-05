#!/usr/bin/env python3
"""
Script to analyze the mapping between reference object folders and actual object names
Reference object: folder name (e.g., alarmclock)
Actual object: object_name field in NPZ files
"""

import numpy as np
from pathlib import Path
from collections import defaultdict
import json

def load_npz_file(file_path):
    """Load npz file and return data dictionary"""
    try:
        data = np.load(file_path, allow_pickle=True)
        return {key: data[key] for key in data.keys()}
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def analyze_reference_actual_mapping():
    """Analyze the mapping between reference object folders and actual object names"""
    
    # Define the base path
    base_path = Path(r"C:\Users\Researcher\grasping-unity\model\session_npz_files\unity_data_collection_20250805\unity_data_collection_20250805")
    
    if not base_path.exists():
        print(f"Base path not found: {base_path}")
        return
    
    print(f"Analyzing reference object vs actual object mapping in: {base_path}")
    print("=" * 80)
    
    # Data structure to store mappings
    mapping_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    all_reference_objects = set()
    all_actual_objects = set()
    
    # Get all subject folders
    subject_folders = [f for f in base_path.iterdir() if f.is_dir() and f.name.startswith('s')]
    subject_folders.sort(key=lambda x: int(x.name[1:]) if x.name[1:].isdigit() else 0)
    
    print(f"Found {len(subject_folders)} subject folders: {[f.name for f in subject_folders]}")
    
    # Analyze each subject
    for subject_folder in subject_folders:
        subject_id = subject_folder.name
        print(f"\nAnalyzing subject {subject_id}...")
        
        # Get all reference object folders in this subject
        reference_object_folders = [f for f in subject_folder.iterdir() if f.is_dir()]
        
        for ref_obj_folder in reference_object_folders:
            reference_object = ref_obj_folder.name.split("_")[0]
            all_reference_objects.add(reference_object)
            
            print(f"  Reference object: {reference_object}")
            
            # Get all t folders (t_0, t_1, t_2, t_3, t_4, t_5)
            t_folders = [f for f in ref_obj_folder.iterdir() if f.is_dir() and f.name.startswith('t_')]
            t_folders.sort(key=lambda x: int(x.name.split('_')[1]))
            
            for t_folder in t_folders:
                t_name = t_folder.name
                
                # Find NPZ files in t folder
                npz_files = list(t_folder.glob("*.npz"))
                
                for npz_file in npz_files:
                    # Load NPZ file to get actual object name
                    data = load_npz_file(npz_file)
                    
                    if data is not None and 'object_name' in data:
                        actual_object = data['object_name'].item()
                        all_actual_objects.add(actual_object)
                        
                        # Determine if this is a negative sample based on filename
                        is_negative = 'ir_0_oor_0' in npz_file.name
                        
                        # Store the mapping with negative sample information
                        mapping_data[subject_id][reference_object][actual_object].append({
                            't_folder': t_name,
                            'npz_file': npz_file.name,
                            'full_path': str(npz_file),
                            'is_negative': is_negative
                        })
                        
    
    # Print summary
    print(f"\n" + "=" * 80)
    print("MAPPING ANALYSIS SUMMARY")
    print("=" * 80)
    
    print(f"Total subjects: {len(subject_folders)}")
    print(f"Total reference objects: {len(all_reference_objects)}")
    print(f"Total actual objects: {len(all_actual_objects)}")
    
    print(f"\nReference objects: {sorted(all_reference_objects)}")
    print(f"Actual objects: {sorted(all_actual_objects)}")
    
    # Analyze mapping patterns
    print(f"\n" + "=" * 80)
    print("MAPPING PATTERNS ANALYSIS")
    print("=" * 80)
    
    # Count mappings for each reference object
    reference_mapping_counts = {}
    for ref_obj in sorted(all_reference_objects):
        total_mappings = 0
        negative_mappings = 0
        actual_objects_used = set()
        
        for subject_id in mapping_data:
            if ref_obj in mapping_data[subject_id]:
                for actual_obj in mapping_data[subject_id][ref_obj]:
                    mappings = mapping_data[subject_id][ref_obj][actual_obj]
                    total_mappings += len(mappings)
                    negative_mappings += sum(1 for m in mappings if m['is_negative'])
                    actual_objects_used.add(actual_obj)
        
        reference_mapping_counts[ref_obj] = {
            'total_mappings': total_mappings,
            'negative_mappings': negative_mappings,
            'negative_percentage': (negative_mappings / total_mappings * 100) if total_mappings > 0 else 0,
            'unique_actual_objects': len(actual_objects_used),
            'actual_objects': sorted(actual_objects_used)
        }
    
    # Sort by negative percentage (highest first)
    sorted_reference_counts = sorted(reference_mapping_counts.items(), 
                                   key=lambda x: x[1]['negative_percentage'], reverse=True)
    
    print(f"{'Reference':<15} {'Total':<8} {'Neg':<6} {'Neg%':<8} {'Unique':<8} {'Actual Objects':<50}")
    print("-" * 100)
    
    for ref_obj, counts in sorted_reference_counts:
        actual_objects_str = ', '.join(counts['actual_objects'])
        neg_percent_str = f"{counts['negative_percentage']:.1f}%"
        print(f"{ref_obj:<15} {counts['total_mappings']:<8} {counts['negative_mappings']:<6} "
              f"{neg_percent_str:<8} {counts['unique_actual_objects']:<8} {actual_objects_str}")
    
    # Analyze reference-actual object pairs with negative sample counts
    print(f"\n" + "=" * 80)
    print("REFERENCE-ACTUAL OBJECT PAIR ANALYSIS (Sorted by Negative %)")
    print("=" * 80)
    
    pair_analysis = defaultdict(lambda: {'total': 0, 'negative': 0, 'subjects': set()})
    
    for subject_id in mapping_data:
        for ref_obj in mapping_data[subject_id]:
            for actual_obj in mapping_data[subject_id][ref_obj]:
                mappings = mapping_data[subject_id][ref_obj][actual_obj]
                pair_key = f"{ref_obj} -> {actual_obj}"
                
                pair_analysis[pair_key]['total'] += len(mappings)
                pair_analysis[pair_key]['negative'] += sum(1 for m in mappings if m['is_negative'])
                pair_analysis[pair_key]['subjects'].add(subject_id)
    
    # Sort pairs by negative percentage (highest first)
    sorted_pairs = sorted(pair_analysis.items(), key=lambda x: (x[1]['negative'] / x[1]['total'] * 100) if x[1]['total'] > 0 else 0, reverse=True)
    
    print(f"{'Reference->Actual':<25} {'Total':<8} {'Neg':<6} {'Neg%':<8} {'Subjects':<15}")
    print("-" * 70)
    
    for pair_key, counts in sorted_pairs:
        negative_percentage = (counts['negative'] / counts['total'] * 100) if counts['total'] > 0 else 0
        neg_percent_str = f"{negative_percentage:.1f}%"
        subjects_str = ', '.join(sorted(counts['subjects']))
        print(f"{pair_key:<25} {counts['total']:<8} {counts['negative']:<6} "
              f"{neg_percent_str:<8} {subjects_str}")
    
    # Analyze actual object usage
    print(f"\n" + "=" * 80)
    print("ACTUAL OBJECT USAGE ANALYSIS (Sorted by Negative %)")
    print("=" * 80)
    
    actual_object_counts = defaultdict(lambda: {'total': 0, 'negative': 0})
    actual_object_references = defaultdict(set)
    
    for subject_id in mapping_data:
        for ref_obj in mapping_data[subject_id]:
            for actual_obj in mapping_data[subject_id][ref_obj]:
                mappings = mapping_data[subject_id][ref_obj][actual_obj]
                count = len(mappings)
                negative_count = sum(1 for m in mappings if m['is_negative'])
                
                actual_object_counts[actual_obj]['total'] += count
                actual_object_counts[actual_obj]['negative'] += negative_count
                actual_object_references[actual_obj].add(ref_obj)
    
    # Sort by negative percentage (highest first)
    sorted_actual_counts = sorted(actual_object_counts.items(), 
                                key=lambda x: (x[1]['negative'] / x[1]['total'] * 100) if x[1]['total'] > 0 else 0, reverse=True)
    
    print(f"{'Actual Object':<15} {'Total':<8} {'Neg':<6} {'Neg%':<8} {'References':<50}")
    print("-" * 90)
    
    for actual_obj, counts in sorted_actual_counts:
        references_str = ', '.join(sorted(actual_object_references[actual_obj]))
        negative_percentage = (counts['negative'] / counts['total'] * 100) if counts['total'] > 0 else 0
        neg_percent_str = f"{negative_percentage:.1f}%"
        print(f"{actual_obj:<15} {counts['total']:<8} {counts['negative']:<6} "
              f"{neg_percent_str:<8} {references_str}")
    
    # Add summary of negative sample distribution
    print(f"\n" + "=" * 80)
    print("NEGATIVE SAMPLE DISTRIBUTION SUMMARY")
    print("=" * 80)
    
    total_files = sum(counts['total_mappings'] for counts in reference_mapping_counts.values())
    total_negative = sum(counts['negative_mappings'] for counts in reference_mapping_counts.values())
    overall_negative_percentage = (total_negative / total_files * 100) if total_files > 0 else 0
    
    print(f"Overall negative sample percentage: {overall_negative_percentage:.1f}% ({total_negative}/{total_files})")
    
    # Find objects with highest and lowest negative percentages
    high_neg_objects = [(ref_obj, counts['negative_percentage']) for ref_obj, counts in reference_mapping_counts.items() 
                        if counts['negative_percentage'] > 50]
    low_neg_objects = [(ref_obj, counts['negative_percentage']) for ref_obj, counts in reference_mapping_counts.items() 
                       if counts['negative_percentage'] < 20]
    
    if high_neg_objects:
        high_neg_objects.sort(key=lambda x: x[1], reverse=True)
        print(f"\nHigh negative percentage objects (>50%):")
        for ref_obj, neg_percent in high_neg_objects:
            print(f"  {ref_obj}: {neg_percent:.1f}%")
    
    if low_neg_objects:
        low_neg_objects.sort(key=lambda x: x[1])
        print(f"\nLow negative percentage objects (<20%):")
        for ref_obj, neg_percent in low_neg_objects:
            print(f"  {ref_obj}: {neg_percent:.1f}%")
    
    # Add detailed summary of reference-actual pair negative sample distribution
    print(f"\n" + "=" * 80)
    print("REFERENCE-ACTUAL PAIR NEGATIVE SAMPLE DETAILED SUMMARY")
    print("=" * 80)
    
    total_pairs = len(pair_analysis)
    pairs_with_high_neg = sum(1 for counts in pair_analysis.values() if (counts['negative'] / counts['total'] * 100) > 50)
    pairs_with_low_neg = sum(1 for counts in pair_analysis.values() if (counts['negative'] / counts['total'] * 100) < 20)
    
    print(f"Total reference-actual pairs: {total_pairs}")
    print(f"Pairs with >50% negative samples: {pairs_with_high_neg} ({pairs_with_high_neg/total_pairs*100:.1f}%)")
    print(f"Pairs with <20% negative samples: {pairs_with_low_neg} ({pairs_with_low_neg/total_pairs*100:.1f}%)")
    
    # Show pairs with highest negative percentages
    high_neg_pairs = [(pair_key, (counts['negative'] / counts['total'] * 100)) for pair_key, counts in pair_analysis.items() 
                      if (counts['negative'] / counts['total'] * 100) > 50]
    if high_neg_pairs:
        high_neg_pairs.sort(key=lambda x: x[1], reverse=True)
        print(f"\nPairs with highest negative percentages (>50%):")
        for pair_key, neg_percent in high_neg_pairs:
            print(f"  {pair_key}: {neg_percent:.1f}%")
    
    # Show pairs with lowest negative percentages
    low_neg_pairs = [(pair_key, (counts['negative'] / counts['total'] * 100)) for pair_key, counts in pair_analysis.items() 
                     if (counts['negative'] / counts['total'] * 100) < 20]
    if low_neg_pairs:
        low_neg_pairs.sort(key=lambda x: x[1])
        print(f"\nPairs with lowest negative percentages (<20%):")
        for pair_key, neg_percent in low_neg_pairs:
            print(f"  {pair_key}: {neg_percent:.1f}%")
    
    # Show consistency analysis (how well reference matches actual)
    print(f"\n" + "=" * 80)
    print("REFERENCE-ACTUAL CONSISTENCY ANALYSIS")
    print("=" * 80)
    
    consistent_pairs = []
    inconsistent_pairs = []
    
    for pair_key, counts in pair_analysis.items():
        ref_obj, actual_obj = pair_key.split(" -> ")
        if ref_obj == actual_obj:  # Same name
            consistent_pairs.append((pair_key, counts))
        else:  # Different name
            inconsistent_pairs.append((pair_key, counts))
    
    print(f"Consistent pairs (reference = actual): {len(consistent_pairs)}")
    print(f"Inconsistent pairs (reference ≠ actual): {len(inconsistent_pairs)}")
    
    if consistent_pairs:
        print(f"\nConsistent pairs negative sample percentages:")
        consistent_neg_percentages = [(pair_key, (counts['negative'] / counts['total'] * 100)) 
                                    for pair_key, counts in consistent_pairs]
        consistent_neg_percentages.sort(key=lambda x: x[1], reverse=True)
        for pair_key, neg_percent in consistent_neg_percentages[:10]:  # Show top 10
            print(f"  {pair_key}: {neg_percent:.1f}%")
    
    if inconsistent_pairs:
        print(f"\nInconsistent pairs negative sample percentages:")
        inconsistent_neg_percentages = [(pair_key, (counts['negative'] / counts['total'] * 100)) 
                                      for pair_key, counts in inconsistent_pairs]
        inconsistent_neg_percentages.sort(key=lambda x: x[1], reverse=True)
        for pair_key, neg_percent in inconsistent_neg_percentages[:10]:  # Show top 10
            print(f"  {pair_key}: {neg_percent:.1f}%")

    
    return mapping_data, all_reference_objects, all_actual_objects

def create_mapping_visualization(mapping_data, all_reference_objects, all_actual_objects):
    """Create visualization of the mapping relationships"""
    
    try:
        import matplotlib.pyplot as plt
        
        # Create a heatmap of reference vs actual object usage
        ref_objects = sorted(all_reference_objects)
        actual_objects = sorted(all_actual_objects)
        
        # Create usage matrix
        usage_matrix = np.zeros((len(ref_objects), len(actual_objects)))
        negative_matrix = np.zeros((len(ref_objects), len(actual_objects)))
        negative_percentage_matrix = np.zeros((len(ref_objects), len(actual_objects)))
        
        for i, ref_obj in enumerate(ref_objects):
            for j, actual_obj in enumerate(actual_objects):
                total_usage = 0
                negative_usage = 0
                for subject_id in mapping_data:
                    if ref_obj in mapping_data[subject_id] and actual_obj in mapping_data[subject_id][ref_obj]:
                        mappings = mapping_data[subject_id][ref_obj][actual_obj]
                        total_usage += len(mappings)
                        negative_usage += sum(1 for m in mappings if m['is_negative'])
                usage_matrix[i, j] = total_usage
                negative_matrix[i, j] = negative_usage
                # Calculate negative percentage
                if total_usage > 0:
                    negative_percentage_matrix[i, j] = (negative_usage / total_usage * 100)
                else:
                    negative_percentage_matrix[i, j] = 0
        
        # Create subplots
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(30, 8))
        
        # Plot 1: Total usage heatmap
        im1 = ax1.imshow(usage_matrix, cmap='YlOrRd', aspect='auto')
        cbar1 = plt.colorbar(im1, ax=ax1)
        cbar1.set_label('Total Number of Files')
        ax1.set_xlabel('Actual Object Names')
        ax1.set_ylabel('Reference Object Folders')
        ax1.set_title('Total Usage Heatmap')
        ax1.set_xticks(range(len(actual_objects)))
        ax1.set_xticklabels(actual_objects, rotation=45, ha='right')
        ax1.set_yticks(range(len(ref_objects)))
        ax1.set_yticklabels(ref_objects)
        
        # Add text annotations for total usage
        for i in range(len(ref_objects)):
            for j in range(len(actual_objects)):
                if usage_matrix[i, j] > 0:
                    ax1.text(j, i, int(usage_matrix[i, j]), 
                            ha='center', va='center', fontsize=8, color='black')
        
        # Plot 2: Negative sample count heatmap
        im2 = ax2.imshow(negative_matrix, cmap='Blues', aspect='auto')
        cbar2 = plt.colorbar(im2, ax=ax2)
        cbar2.set_label('Number of Negative Samples')
        ax2.set_xlabel('Actual Object Names')
        ax2.set_ylabel('Reference Object Folders')
        ax2.set_title('Negative Sample Count Heatmap')
        ax2.set_xticks(range(len(actual_objects)))
        ax2.set_xticklabels(actual_objects, rotation=45, ha='right')
        ax2.set_yticks(range(len(ref_objects)))
        ax2.set_yticklabels(ref_objects)
        
        # Add text annotations for negative sample counts
        for i in range(len(ref_objects)):
            for j in range(len(actual_objects)):
                if negative_matrix[i, j] > 0:
                    ax2.text(j, i, int(negative_matrix[i, j]), 
                            ha='center', va='center', fontsize=8, color='black')
        
        # Plot 3: Negative sample percentage heatmap
        im3 = ax3.imshow(negative_percentage_matrix, cmap='Reds', aspect='auto', vmin=0, vmax=100)
        cbar3 = plt.colorbar(im3, ax=ax3)
        cbar3.set_label('Negative Sample Percentage (%)')
        ax3.set_xlabel('Actual Object Names')
        ax3.set_ylabel('Reference Object Folders')
        ax3.set_title('Negative Sample Percentage Heatmap')
        ax3.set_xticks(range(len(actual_objects)))
        ax3.set_xticklabels(actual_objects, rotation=45, ha='right')
        ax3.set_yticks(range(len(ref_objects)))
        ax3.set_yticklabels(ref_objects)
        
        # Add text annotations for negative sample percentages
        for i in range(len(ref_objects)):
            for j in range(len(actual_objects)):
                if negative_percentage_matrix[i, j] > 0:
                    # Format percentage with 1 decimal place
                    percentage_text = f"{negative_percentage_matrix[i, j]:.1f}%"
                    ax3.text(j, i, percentage_text, 
                            ha='center', va='center', fontsize=7, color='black', weight='bold')
        
        plt.tight_layout()
        
        # Save the plot
        output_file = 'reference_actual_object_mapping_heatmap.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Mapping heatmap saved to: {output_file}")
        
        # Show the plot
        plt.show()
        
    except Exception as e:
        print(f"Warning: Could not create mapping visualization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Reference Object vs Actual Object Mapping Analysis")
    print("=" * 60)
    print("This script analyzes the relationship between reference object")
    print("folder names and actual object names in NPZ files")
    print("=" * 60)
    
    # Perform the analysis
    mapping_data, ref_objects, actual_objects = analyze_reference_actual_mapping()
    
    # Create visualization
    create_mapping_visualization(mapping_data, ref_objects, actual_objects)
    
    print("\n✓ Analysis completed successfully!")
