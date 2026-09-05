#!/usr/bin/env python3
"""
Script to analyze positive/negative sample distribution
Analyzes the ratio of positive vs negative samples for each object type
"""

import numpy as np
from pathlib import Path
from collections import defaultdict

def get_object_type_from_filename(filename):
    """Extract object type from filename like 'features_ir_1_oor_1_bowl.npz' or 'features_ir_0_oor_0_bowl.npz'"""
    # Remove .npz extension
    name = filename.replace('.npz', '')
    # Split by underscore and get the last part (object name)
    parts = name.split('_')
    if len(parts) >= 4:
        return parts[-1]  # Last part should be the object name
    return "unknown"

def get_sample_type(filename):
    """Get the sample type: positive (ir_1_oor_1) or negative (ir_0_oor_0)"""
    if 'ir_1_oor_1' in filename:
        return 'positive'
    elif 'ir_0_oor_0' in filename:
        return 'negative'
    else:
        return 'unknown'

def analyze_sample_distribution():
    """Analyze the distribution of positive vs negative samples"""
    
    # Define reference folder
    reference_folder = Path(r"C:\Users\Researcher\grasping-unity\model\session_npz_files\unity_data_collection_20250805\unity_data_collection_20250805")
    
    if not reference_folder.exists():
        print(f"Reference folder not found: {reference_folder}")
        return
    
    print(f"Searching for features files in: {reference_folder}")
    
    # Find all features files (both types)
    positive_files = list(reference_folder.glob("**/features_ir_1_oor_1*.npz"))
    negative_files = list(reference_folder.glob("**/features_ir_0_oor_0*.npz"))
    
    all_features_files = positive_files + negative_files
    
    if not all_features_files:
        print("No features files found")
        return
    
    print(f"Found {len(all_features_files)} features files:")
    print(f"  Positive samples (ir_1_oor_1): {len(positive_files)} files")
    print(f"  Negative samples (ir_0_oor_0): {len(negative_files)} files")
    print("=" * 60)
    
    # Group files by object type and sample type
    object_sample_groups = defaultdict(lambda: defaultdict(list))
    for file_path in all_features_files:
        object_type = get_object_type_from_filename(file_path.name)
        sample_type = get_sample_type(file_path.name)
        object_sample_groups[object_type][sample_type].append(file_path)
    
    print(f"Found {len(object_sample_groups)} different object types:")
    for obj_type, sample_types in object_sample_groups.items():
        print(f"  {obj_type}:")
        for sample_type, files in sample_types.items():
            print(f"    {sample_type}: {len(files)} files")
    
    print("\n" + "=" * 60)
    print("OVERALL SAMPLE DISTRIBUTION")
    print("=" * 60)
    
    # Calculate overall statistics
    total_all_samples = len(all_features_files)
    total_positive_samples = len(positive_files)
    total_negative_samples = len(negative_files)
    
    print(f"Total samples: {total_all_samples}")
    print(f"Total positive samples (ir_1_oor_1): {total_positive_samples} ({total_positive_samples/total_all_samples*100:.1f}%)")
    print(f"Total negative samples (ir_0_oor_0): {total_negative_samples} ({total_negative_samples/total_all_samples*100:.1f}%)")
    
    # Calculate positive/negative ratio
    if total_negative_samples > 0:
        pos_neg_ratio = total_positive_samples / total_negative_samples
        print(f"Positive/Negative ratio: {pos_neg_ratio:.2f} (1:{pos_neg_ratio:.2f})")
    else:
        print("Positive/Negative ratio: N/A (no negative samples)")
    
    print("\n" + "=" * 60)
    print("OBJECT-WISE SAMPLE DISTRIBUTION (Sorted by Pos% - Smallest to Largest)")
    print("=" * 60)
    
    # Create detailed object analysis
    object_stats = []
    
    for obj_type, sample_types in object_sample_groups.items():
        obj_positive_count = len(sample_types.get('positive', []))
        obj_negative_count = len(sample_types.get('negative', []))
        obj_total_count = obj_positive_count + obj_negative_count
        
        if obj_total_count > 0:
            obj_pos_percentage = (obj_positive_count / obj_total_count) * 100
            obj_neg_percentage = (obj_negative_count / obj_total_count) * 100
            
            # Calculate ratio for this object
            obj_ratio = obj_positive_count / obj_negative_count if obj_negative_count > 0 else float('inf')
            
            object_stats.append({
                'object': obj_type,
                'total': obj_total_count,
                'positive': obj_positive_count,
                'negative': obj_negative_count,
                'pos_percentage': obj_pos_percentage,
                'neg_percentage': obj_neg_percentage,
                'ratio': obj_ratio
            })
    
    # Sort objects by positive percentage (ascending - from smallest to largest)
    object_stats.sort(key=lambda x: x['pos_percentage'])
    
    # Print header
    print(f"{'Object':<15} {'Total':<8} {'Positive':<10} {'Negative':<10} {'Pos%':<8} {'Neg%':<8} {'Ratio':<10}")
    print("-" * 80)
    
    # Print each object's statistics
    for stats in object_stats:
        ratio_str = f"{stats['ratio']:.2f}" if stats['ratio'] != float('inf') else "∞"
        print(f"{stats['object']:<15} {stats['total']:<8} {stats['positive']:<10} {stats['negative']:<10} "
              f"{stats['pos_percentage']:<8.1f} {stats['neg_percentage']:<8.1f} {ratio_str:<10}")
    
    # Summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)
    
    # Objects with balanced samples (close to 50/50)
    balanced_objects = [stats for stats in object_stats if 40 <= stats['pos_percentage'] <= 60]
    print(f"Objects with balanced samples (40-60% positive): {len(balanced_objects)}")
    if balanced_objects:
        print("  Balanced objects:")
        for stats in balanced_objects:
            print(f"    {stats['object']}: {stats['pos_percentage']:.1f}% positive, {stats['neg_percentage']:.1f}% negative")
    
    # Objects with more positive samples (>60%)
    more_positive = [stats for stats in object_stats if stats['pos_percentage'] > 60]
    print(f"\nObjects with more positive samples (>60%): {len(more_positive)}")
    if more_positive:
        print("  More positive objects:")
        for stats in more_positive:
            print(f"    {stats['object']}: {stats['pos_percentage']:.1f}% positive, {stats['neg_percentage']:.1f}% negative")
    
    # Objects with more negative samples (<40%)
    more_negative = [stats for stats in object_stats if stats['pos_percentage'] < 40]
    print(f"\nObjects with more negative samples (<40%): {len(more_negative)}")
    if more_negative:
        print("  More negative objects:")
        for stats in more_negative:
            print(f"    {stats['object']}: {stats['pos_percentage']:.1f}% positive, {stats['neg_percentage']:.1f}% negative")
    
    # Objects with extreme ratios
    extreme_positive = [stats for stats in object_stats if stats['ratio'] > 3.0]
    extreme_negative = [stats for stats in object_stats if stats['ratio'] < 0.33]
    
    print(f"\nObjects with extreme positive bias (ratio > 3:1): {len(extreme_positive)}")
    if extreme_positive:
        for stats in extreme_positive:
            print(f"    {stats['object']}: {stats['ratio']:.2f}:1 ratio")
    
    print(f"Objects with extreme negative bias (ratio < 1:3): {len(extreme_negative)}")
    if extreme_negative:
        for stats in extreme_negative:
            print(f"    {stats['object']}: 1:{1/stats['ratio']:.2f} ratio")
    
    # Save results to file
    output_file = Path("sample_distribution_analysis.txt")
    with open(output_file, 'w') as f:
        f.write("Sample Distribution Analysis Results\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Reference folder: {reference_folder}\n")
        f.write(f"Total features files found: {len(all_features_files)}\n")
        f.write(f"  Positive samples (ir_1_oor_1): {len(positive_files)} files\n")
        f.write(f"  Negative samples (ir_0_oor_0): {len(negative_files)} files\n")
        f.write(f"Object types analyzed: {len(object_stats)}\n\n")
        
        f.write("OVERALL SAMPLE DISTRIBUTION\n")
        f.write("=" * 40 + "\n")
        f.write(f"Total samples: {total_all_samples}\n")
        f.write(f"Total positive samples: {total_positive_samples} ({total_positive_samples/total_all_samples*100:.1f}%)\n")
        f.write(f"Total negative samples: {total_negative_samples} ({total_negative_samples/total_all_samples*100:.1f}%)\n")
        if total_negative_samples > 0:
            pos_neg_ratio = total_positive_samples / total_negative_samples
            f.write(f"Positive/Negative ratio: {pos_neg_ratio:.2f}\n")
        
        f.write("\nOBJECT-WISE SAMPLE DISTRIBUTION\n")
        f.write("=" * 40 + "\n")
        f.write(f"{'Object':<15} {'Total':<8} {'Positive':<10} {'Negative':<10} {'Pos%':<8} {'Neg%':<8} {'Ratio':<10}\n")
        f.write("-" * 80 + "\n")
        
        for stats in object_stats:
            ratio_str = f"{stats['ratio']:.2f}" if stats['ratio'] != float('inf') else "∞"
            f.write(f"{stats['object']:<15} {stats['total']:<8} {stats['positive']:<10} {stats['negative']:<10} "
                   f"{stats['pos_percentage']:<8.1f} {stats['neg_percentage']:<8.1f} {ratio_str:<10}\n")
    
    print(f"\n✓ Detailed results saved to: {output_file}")
    
    # Save CSV format for easy analysis
    csv_file = Path("sample_distribution_analysis.csv")
    with open(csv_file, 'w') as f:
        f.write("Object,Total_Samples,Positive_Samples,Negative_Samples,Positive_Percentage,Negative_Percentage,Positive_Negative_Ratio\n")
        
        for stats in object_stats:
            ratio_str = f"{stats['ratio']:.2f}" if stats['ratio'] != float('inf') else "inf"
            f.write(f"{stats['object']},{stats['total']},{stats['positive']},{stats['negative']},"
                   f"{stats['pos_percentage']:.2f},{stats['neg_percentage']:.2f},{ratio_str}\n")
    
    print(f"✓ CSV results saved to: {csv_file}")

if __name__ == "__main__":
    print("Sample Distribution Analysis Script")
    print("=" * 50)
    print("This script analyzes the distribution of positive vs negative samples")
    print("for each object type in the dataset")
    print("=" * 50)
    
    analyze_sample_distribution()
