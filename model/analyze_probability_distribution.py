#!/usr/bin/env python3
"""
Script to analyze probability distribution for each object type
Separate analysis for positive samples (ir_1_oor_1) and negative samples (ir_0_oor_0)
"""

import numpy as np
import torch
from pathlib import Path
import sys
from collections import defaultdict
import matplotlib.pyplot as plt

# Add the current directory to Python path
sys.path.append('.')

from nets import InferenceNet
from config import model_config

def load_model():
    """Load the InferenceNet model"""
    print("Loading InferenceNet model...")
    
    try:
        # Initialize model
        model = InferenceNet(**model_config).to('cpu')
        
        # Load checkpoint
        # ckpt_path = Path('./files/0025_unityall_hand63_objects25_pos=neg.tar')
        ckpt_path = Path('./files/0025_unityall_hand63_object30_pos=neg.tar')
        if not ckpt_path.exists():
            print(f"Checkpoint not found: {ckpt_path}")
            print("Please make sure the checkpoint file exists in the files folder")
            return None
            
        ckpt = torch.load(ckpt_path, map_location=torch.device('cpu'))
        model.load_state_dict(ckpt['model_state_dict'])
        model.eval()
        
        print("✓ Model loaded successfully!")
        return model
        
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_npz_file(file_path):
    """Load npz file and return data dictionary"""
    try:
        data = np.load(file_path, allow_pickle=True)
        return {key: data[key] for key in data.keys()}
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

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

def calculate_ece(probabilities, labels, bins=15):
    """Calculate Expected Calibration Error (ECE)"""
    bin_boundaries = np.linspace(0, 1, bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]
    
    ece = 0.0
    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        # Find predictions in this bin
        in_bin = np.logical_and(probabilities > bin_lower, probabilities <= bin_upper)
        bin_size = np.sum(in_bin)
        
        if bin_size > 0:
            bin_acc = np.sum(labels[in_bin]) / bin_size
            bin_conf = np.mean(probabilities[in_bin])
            ece += bin_size * np.abs(bin_acc - bin_conf)
    
    return ece / len(probabilities)

def analyze_probability_for_file(file_path, model):
    """Analyze probability for a single NPZ file"""
    
    data = load_npz_file(file_path)
    if data is None:
        return None
    
    # Check if we have the required data
    if 'object_pointcloud' not in data or 'subject_joints_pos_rel2wrist' not in data:
        return None
    

    # Prepare data for the model
    obj_pcl = torch.tensor(data['object_pointcloud'], dtype=torch.float32).unsqueeze(0)  # (1, N, 3)
    hand_joints = torch.tensor(data['subject_joints_pos_rel2wrist'], dtype=torch.float32).unsqueeze(0)  # (1, M, 3)
    # hand_pos = torch.tensor(data['subject_joints_pos_rel2wrist'], dtype=torch.float32).unsqueeze(0)  # (1, M, 3)
    # hand_rot = torch.tensor(data["subject_joints_rot"], dtype=torch.float32).unsqueeze(0)  # (1, M, 6)
    # hand_joints = torch.cat([hand_pos, hand_rot], dim=2)  # (1, M, 9)

    # Run inference
    with torch.no_grad():
        prediction = model(hand_joints=hand_joints, obj_pcl=obj_pcl)
        obj_logit = prediction["obj_logit"]
        probability = torch.sigmoid(obj_logit).item()
        
        return {
            'probability': probability,
            'is_high': probability > 0.5,
            'is_low': probability <= 0.5
        }
            


def analyze_all_features_files():
    """Analyze all features files with separate positive/negative sample analysis"""
    
    # Define the specific objects to analyze
    target_objects = ['alarmclock', 'apple', 'banana', 'binoculars', 'bowl', 'camera', 'crackerbox', 
           'cup', 'disklid', 'eyeglasses', 'flashlight', 'fryingpan', 'gamecontroller', 'hammer', 'headphones', 
           'knife', 'mouse', 'mug', 'plate', 'pottedmeatcan', 'scissors', 'smartphone', 'spherelarge', 'spheresmall', 'stapler', 
           'teapot', 'toothpaste', 'watch', 'waterbottle', 'wineglass']
    
    print(f"Target objects to analyze: {len(target_objects)} objects")
    print(f"Objects: {', '.join(target_objects)}")
    print("=" * 60)
    
    # Load model
    model = load_model()
    
    # Define reference folder
    reference_folder = Path(r"C:\Users\Researcher\grasping-unity\model\session_npz_files\unity_data_collection_20250805\unity_data_collection_20250805")
    
    if not reference_folder.exists():
        print(f"Reference folder not found: {reference_folder}")
        return
    
    print(f"Searching for features files in: {reference_folder}")
    
    # Find all features files (both types) for target objects only
    positive_files = []
    negative_files = []
    
    for obj in target_objects:
        # Find positive samples for this object
        obj_pos_files = list(reference_folder.glob(f"**/features_ir_1_oor_1_{obj}.npz"))
        positive_files.extend(obj_pos_files)
        
        # Find negative samples for this object
        obj_neg_files = list(reference_folder.glob(f"**/features_ir_0_oor_0_{obj}.npz"))
        negative_files.extend(obj_neg_files)
    
    all_features_files = positive_files + negative_files
    
    if not all_features_files:
        print("No features files found for target objects")
        return
    
    print(f"Found {len(all_features_files)} features files for target objects:")
    print(f"  Positive samples (ir_1_oor_1): {len(positive_files)} files")
    print(f"  Negative samples (ir_0_oor_0): {len(negative_files)} files")
    print("=" * 60)
    
    # Group files by object type and sample type (only for target objects)
    object_sample_groups = defaultdict(lambda: defaultdict(list))
    for file_path in all_features_files:
        object_type = get_object_type_from_filename(file_path.name)
        # Only include if it's one of our target objects
        if object_type in target_objects:
            sample_type = get_sample_type(file_path.name)
            object_sample_groups[object_type][sample_type].append(file_path)
    
    # Ensure all target objects are present (even if no files found)
    for obj in target_objects:
        if obj not in object_sample_groups:
            object_sample_groups[obj] = {}
    
    print(f"Analysis will cover {len(target_objects)} target object types:")
    for obj_type in target_objects:
        if obj_type in object_sample_groups:
            sample_types = object_sample_groups[obj_type]
            print(f"  {obj_type}:")
            if sample_types:
                for sample_type, files in sample_types.items():
                    print(f"    {sample_type}: {len(files)} files")
            else:
                print(f"    No files found")
        else:
            print(f"  {obj_type}: No files found")
    
    print("\n" + "=" * 60)
    print("ANALYZING PROBABILITY DISTRIBUTION")
    print("=" * 60)
    
    # Analyze each object type and sample type separately
    results = {}
    
    # Analyze in the order of target objects
    for obj_type in target_objects:
        print(f"\nAnalyzing {obj_type}...")
        results[obj_type] = {}
        
        if obj_type in object_sample_groups:
            sample_types = object_sample_groups[obj_type]
            for sample_type, files in sample_types.items():
                print(f"  Sample type: {sample_type} ({len(files)} files)...")
                
                high_prob_count = 0
                low_prob_count = 0
                total_processed = 0
                probabilities = []
                
                for i, file_path in enumerate(files, 1):
                    result = analyze_probability_for_file(file_path, model)
                    
                    if result is not None:
                        total_processed += 1
                        probabilities.append(result['probability'])
                        
                        if result['is_high']:
                            high_prob_count += 1
                        else:
                            low_prob_count += 1
                
                # Calculate statistics for this sample type
                if total_processed > 0:
                    avg_probability = np.mean(probabilities)
                    std_probability = np.std(probabilities)
                    min_probability = np.min(probabilities)
                    max_probability = np.max(probabilities)
                    
                    results[obj_type][sample_type] = {
                        'total_files': len(files),
                        'processed_files': total_processed,
                        'high_prob_count': high_prob_count,
                        'low_prob_count': low_prob_count,
                        'high_prob_percentage': (high_prob_count / total_processed) * 100,
                        'low_prob_percentage': (low_prob_count / total_processed) * 100,
                        'avg_probability': avg_probability,
                        'std_probability': std_probability,
                        'min_probability': min_probability,
                        'max_probability': max_probability,
                        'probabilities': probabilities  # Store raw probabilities for ECE calculation
                    }
                    
                    print(f"    ✓ Completed: {total_processed}/{len(files)} files processed")
                    print(f"    High probability (>0.5): {high_prob_count} ({results[obj_type][sample_type]['high_prob_percentage']:.1f}%)")
                    print(f"    Low probability (≤0.5): {low_prob_count} ({results[obj_type][sample_type]['low_prob_percentage']:.1f}%)")
                    print(f"    Average probability: {avg_probability:.4f} ± {std_probability:.4f}")
                    print(f"    Range: [{min_probability:.4f}, {max_probability:.4f}]")
                else:
                    print(f"    ✗ No files could be processed for {obj_type} - {sample_type}")
        else:
            print(f"  No files found for {obj_type}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY BY OBJECT TYPE AND SAMPLE TYPE")
    print("=" * 60)
    
    if results:
        # Create summary table
        print(f"\nDetailed Summary by Object Type and Sample Type:")
        print("=" * 80)
        
        for obj_type in target_objects:
            if obj_type in results:
                sample_types = results[obj_type]
                print(f"\n{obj_type}:")
                print("-" * 40)
                
                if sample_types:
                    for sample_type, stats in sample_types.items():
                        print(f"  {sample_type}:")
                        print(f"    Files: {stats['processed_files']}/{stats['total_files']}")
                        print(f"    High prob: {stats['high_prob_count']} ({stats['high_prob_percentage']:.1f}%)")
                        print(f"    Low prob: {stats['low_prob_count']} ({stats['low_prob_percentage']:.1f}%)")
                        print(f"    Avg: {stats['avg_probability']:.4f} ± {stats['std_probability']:.4f}")
                        print(f"    Range: [{stats['min_probability']:.3f}, {stats['max_probability']:.3f}]")
                else:
                    print(f"  No data available")
            else:
                print(f"\n{obj_type}:")
                print("-" * 40)
                print(f"  No data available")
        
        # Generate separate ranking tables for positive and negative samples
        print(f"\n" + "=" * 60)
        print("RANKING TABLES")
        print("=" * 60)
        
        # Positive samples ranking table
        positive_results = {}
        for obj_type, sample_types in results.items():
            if 'positive' in sample_types:
                positive_results[obj_type] = sample_types['positive']
        
        if positive_results:
            print(f"\nPOSITIVE SAMPLES (ir_1_oor_1) - Ranked by High Probability %")
            print("=" * 90)
            print(f"{'Object':<15} {'Total':<8} {'High':<8} {'Low':<8} {'High%':<8} {'Avg':<8} {'Range':<15} {'Pos%':<8}")
            print("-" * 90)
            
            # Sort by high probability percentage (descending)
            sorted_positive = sorted(positive_results.items(), key=lambda x: x[1]['high_prob_percentage'], reverse=True)
            
            for obj_type, stats in sorted_positive:
                # Calculate positive samples percentage for this object
                obj_total_samples = len(results[obj_type].get('positive', [])) + len(results[obj_type].get('negative', []))
                obj_pos_percentage = (len(results[obj_type].get('positive', [])) / obj_total_samples * 100) if obj_total_samples > 0 else 0
                
                print(f"{obj_type:<15} {stats['total_files']:<8} {stats['high_prob_count']:<8} "
                      f"{stats['low_prob_count']:<8} {stats['high_prob_percentage']:<8.1f} "
                      f"{stats['avg_probability']:<8.4f} [{stats['min_probability']:.3f},{stats['max_probability']:.3f}] {obj_pos_percentage:<8.1f}")
        
        # Negative samples ranking table
        negative_results = {}
        for obj_type, sample_types in results.items():
            if 'negative' in sample_types:
                negative_results[obj_type] = sample_types['negative']
        
        if negative_results:
            print(f"\nNEGATIVE SAMPLES (ir_0_oor_0) - Ranked by Low Probability %")
            print("=" * 90)
            print(f"{'Object':<15} {'Total':<8} {'High':<8} {'Low':<8} {'Low%':<8} {'Avg':<8} {'Range':<15} {'Neg%':<8}")
            print("-" * 90)
            
            # Sort by low probability percentage (descending) - for negative samples, higher low% is better
            sorted_negative = sorted(negative_results.items(), key=lambda x: x[1]['low_prob_percentage'], reverse=True)
            
            for obj_type, stats in sorted_negative:
                # Calculate negative samples percentage for this object
                obj_total_samples = len(results[obj_type].get('positive', [])) + len(results[obj_type].get('negative', []))
                obj_neg_percentage = (len(results[obj_type].get('negative', [])) / obj_total_samples * 100) if obj_total_samples > 0 else 0
                
                print(f"{obj_type:<15} {stats['total_files']:<8} {stats['high_prob_count']:<8} "
                      f"{stats['low_prob_count']:<8} {stats['low_prob_percentage']:<8.1f} "
                      f"{stats['avg_probability']:<8.4f} [{stats['min_probability']:.3f},{stats['max_probability']:.3f}] {obj_neg_percentage:<8.1f}")
        
            # Calculate Youden's J score for each object type
        print(f"\n" + "=" * 60)
        print("CATEGORY SEPARABILITY SCORE (Youden's J)")
        print("=" * 60)
        print("J = High% + Low% - 100%")
        print("J > 0: Good separability (both positive and negative samples well classified)")
        print("J < 0: Poor separability (model struggles with this object type)")
        print("-" * 60)
        
        youden_scores = []
        for obj_type, sample_types in results.items():
            if 'positive' in sample_types and 'negative' in sample_types:
                pos_stats = sample_types['positive']
                neg_stats = sample_types['negative']
                
                # Calculate Youden's J score
                high_pct = pos_stats['high_prob_percentage']
                low_pct = neg_stats['low_prob_percentage']
                youden_j = high_pct + low_pct - 100.0
                
                youden_scores.append({
                    'object': obj_type,
                    'high_pct': high_pct,
                    'low_pct': low_pct,
                    'youden_j': youden_j,
                    'pos_count': pos_stats['processed_files'],
                    'neg_count': neg_stats['processed_files']
                })
        
        if youden_scores:
            # Sort by Youden's J score (descending - best to worst)
            youden_scores.sort(key=lambda x: x['youden_j'], reverse=True)
            
            print(f"{'Object':<15} {'High%':<8} {'Low%':<8} {'J Score':<10} {'Pos':<6} {'Neg':<6} {'Status':<12}")
            print("-" * 70)
            
            for score in youden_scores:
                # Determine status based on J score
                if score['youden_j'] >= 60:
                    status = "Excellent"
                elif score['youden_j'] >= 40:
                    status = "Good"
                elif score['youden_j'] >= 20:
                    status = "Fair"
                elif score['youden_j'] >= 0:
                    status = "Poor"
                else:
                    status = "Very Poor"
                
                print(f"{score['object']:<15} {score['high_pct']:<8.1f} {score['low_pct']:<8.1f} "
                      f"{score['youden_j']:<10.1f} {score['pos_count']:<6} {score['neg_count']:<6} {status:<12}")
            
        else:
            print("No objects with both positive and negative samples found for Youden's J calculation")
        
        # Calculate ECE for each object type
        print(f"\n" + "=" * 60)
        print("EXPECTED CALIBRATION ERROR (ECE) ANALYSIS")
        print("=" * 60)
        print("ECE measures how well calibrated the model probabilities are")
        print("Lower ECE = Better calibration")
        print("-" * 60)
        
        ece_results = []
        for obj_type in target_objects:
            if obj_type in results and 'positive' in results[obj_type] and 'negative' in results[obj_type]:
                pos_stats = results[obj_type]['positive']
                neg_stats = results[obj_type]['negative']
                
                # Combine probabilities and labels for ECE calculation
                pos_probs = pos_stats['probabilities']
                neg_probs = neg_stats['probabilities']
                
                all_probs = np.concatenate([pos_probs, neg_probs])
                all_labels = np.concatenate([np.ones(len(pos_probs)), np.zeros(len(neg_probs))])
                
                # Calculate ECE
                ece_score = calculate_ece(all_probs, all_labels)
                
                ece_results.append({
                    'object': obj_type,
                    'ece': ece_score,
                    'pos_count': len(pos_probs),
                    'neg_count': len(neg_probs),
                    'total_count': len(all_probs)
                })
            else:
                # Add object with no ECE data for completeness
                ece_results.append({
                    'object': obj_type,
                    'ece': float('inf'),  # Use infinity to indicate no data
                    'pos_count': 0,
                    'neg_count': 0,
                    'total_count': 0
                })
        
        if ece_results:
            # Separate valid ECE results from those with no data
            valid_ece_results = [r for r in ece_results if r['ece'] != float('inf')]
            no_data_results = [r for r in ece_results if r['ece'] == float('inf')]
            
            if valid_ece_results:
                # Sort by ECE (ascending - best to worst)
                valid_ece_results.sort(key=lambda x: x['ece'])
                
                print(f"{'Object':<15} {'ECE':<10} {'Pos':<6} {'Neg':<6} {'Total':<8} {'Status':<12}")
                print("-" * 70)
                
                for result in valid_ece_results:
                    # Determine status based on ECE
                    if result['ece'] <= 0.05:
                        status = "Excellent"
                    elif result['ece'] <= 0.10:
                        status = "Good"
                    elif result['ece'] <= 0.15:
                        status = "Fair"
                    elif result['ece'] <= 0.20:
                        status = "Poor"
                    else:
                        status = "Very Poor"
                    
                    print(f"{result['object']:<15} {result['ece']:<10.4f} {result['pos_count']:<6} "
                          f"{result['neg_count']:<6} {result['total_count']:<8} {status:<12}")
                
                # Show objects with no data
                if no_data_results:
                    print(f"\nObjects with insufficient data for ECE calculation:")
                    for result in no_data_results:
                        print(f"  {result['object']}: No positive/negative samples found")
            else:
                print("No objects have sufficient data for ECE calculation")
            
            # Summary statistics
            print(f"\n" + "=" * 60)
            print("ECE SUMMARY STATISTICS")
            print("=" * 60)
            
            excellent_ece = len([r for r in ece_results if r['ece'] <= 0.05])
            good_ece = len([r for r in ece_results if 0.05 < r['ece'] <= 0.10])
            fair_ece = len([r for r in ece_results if 0.10 < r['ece'] <= 0.15])
            poor_ece = len([r for r in ece_results if 0.15 < r['ece'] <= 0.20])
            very_poor_ece = len([r for r in ece_results if r['ece'] > 0.20])
            
            print(f"Excellent (ECE ≤ 0.05): {excellent_ece} objects")
            print(f"Good (0.05 < ECE ≤ 0.10): {good_ece} objects")
            print(f"Fair (0.10 < ECE ≤ 0.15): {fair_ece} objects")
            print(f"Poor (0.15 < ECE ≤ 0.20): {poor_ece} objects")
            print(f"Very Poor (ECE > 0.20): {very_poor_ece} objects")
            
            # Top performers (lowest ECE)
            if ece_results:
                print(f"\n🏆 TOP 5 CALIBRATION PERFORMERS (Lowest ECE):")
                for i, result in enumerate(ece_results[:5], 1):
                    print(f"  {i}. {result['object']}: ECE = {result['ece']:.4f}")
            
            # Bottom performers (highest ECE)
            if ece_results:
                print(f"\n⚠ BOTTOM 5 CALIBRATION PERFORMERS (Highest ECE):")
                for i, result in enumerate(ece_results[-5:], 1):
                    print(f"  {len(ece_results)-5+i}. {result['object']}: ECE = {result['ece']:.4f}")
            
            # Create ECE visualization (only for valid results)
            if valid_ece_results:
                create_ece_visualization(valid_ece_results)

            create_probability_distribution_plots(results, target_objects)
            
            # Save ECE analysis to file
            ece_file = 'ece_calibration_analysis.txt'
            with open(ece_file, 'w', encoding='utf-8') as f:
                f.write("Expected Calibration Error (ECE) Analysis\n")
                f.write("=" * 50 + "\n\n")
                f.write("ECE measures probability calibration quality\n")
                f.write("Lower ECE = Better calibration\n")
                f.write(f"Analysis covers {len(target_objects)} target objects\n\n")
                
                f.write("DETAILED ECE SCORES (Ranked by ECE - Best to Worst)\n")
                f.write("-" * 60 + "\n")
                f.write(f"{'Object':<15} {'ECE':<10} {'Pos':<6} {'Neg':<6} {'Total':<8} {'Status':<12}\n")
                f.write("-" * 60 + "\n")
                
                for result in valid_ece_results:
                    if result['ece'] <= 0.05:
                        status = "Excellent"
                    elif result['ece'] <= 0.10:
                        status = "Good"
                    elif result['ece'] <= 0.15:
                        status = "Fair"
                    elif result['ece'] <= 0.20:
                        status = "Poor"
                    else:
                        status = "Very Poor"
                    
                    f.write(f"{result['object']:<15} {result['ece']:<10.4f} {result['pos_count']:<6} "
                           f"{result['neg_count']:<6} {result['total_count']:<8} {status:<12}\n")
                
                # Add objects with no data
                if no_data_results:
                    f.write(f"\nOBJECTS WITH INSUFFICIENT DATA FOR ECE CALCULATION\n")
                    f.write("-" * 60 + "\n")
                    for result in no_data_results:
                        f.write(f"{result['object']}: No positive/negative samples found\n")
                
                f.write(f"\nSUMMARY STATISTICS\n")
                f.write("-" * 25 + "\n")
                f.write(f"Excellent (ECE ≤ 0.05): {excellent_ece}\n")
                f.write(f"Good (0.05 < ECE ≤ 0.10): {good_ece}\n")
                f.write(f"Fair (0.10 < ECE ≤ 0.15): {fair_ece}\n")
                f.write(f"Poor (0.15 < ECE ≤ 0.20): {poor_ece}\n")
                f.write(f"Very Poor (ECE > 0.20): {very_poor_ece}\n")
                f.write(f"Objects with no data: {len(no_data_results)}\n")
            
            print(f"\n✓ ECE analysis saved to: {ece_file}")
        else:
            print("No objects with both positive and negative samples found for ECE calculation")
        
    else:
        print("No results to display")

def create_ece_visualization(ece_results):
    """Create ECE visualization plots"""
    
    try:
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Extract data for plotting
        objects = [result['object'] for result in ece_results]
        ece_scores = [result['ece'] for result in ece_results]
        total_counts = [result['total_count'] for result in ece_results]
        
        # Plot 1: ECE Bar Chart (sorted by ECE)
        bars1 = ax1.bar(range(len(objects)), ece_scores, 
                        color=['green' if ece <= 0.05 else 'lightgreen' if ece <= 0.10 else 
                               'yellow' if ece <= 0.15 else 'orange' if ece <= 0.20 else 'red' 
                               for ece in ece_scores],
                        alpha=0.7, edgecolor='black')
        
        ax1.set_xlabel('Object Type')
        ax1.set_ylabel('Expected Calibration Error (ECE)')
        ax1.set_title('ECE Scores by Object Type (Lower is Better)')
        ax1.set_xticks(range(len(objects)))
        ax1.set_xticklabels(objects, rotation=45, ha='right')
        ax1.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for i, (bar, ece) in enumerate(zip(bars1, ece_scores)):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.001,
                    f'{ece:.3f}', ha='center', va='bottom', fontsize=9)
        
        # Add horizontal lines for ECE thresholds
        ax1.axhline(y=0.05, color='green', linestyle='--', alpha=0.7, label='Excellent (≤0.05)')
        ax1.axhline(y=0.10, color='lightgreen', linestyle='--', alpha=0.7, label='Good (≤0.10)')
        ax1.axhline(y=0.15, color='yellow', linestyle='--', alpha=0.7, label='Fair (≤0.15)')
        ax1.axhline(y=0.20, color='orange', linestyle='--', alpha=0.7, label='Poor (≤0.20)')
        ax1.legend()
        
        # Plot 2: ECE vs Sample Count Scatter Plot
        scatter = ax2.scatter(total_counts, ece_scores, 
                             c=ece_scores, cmap='RdYlGn_r', 
                             s=100, alpha=0.7, edgecolors='black')
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax2)
        cbar.set_label('ECE Score')
        
        ax2.set_xlabel('Total Sample Count')
        ax2.set_ylabel('Expected Calibration Error (ECE)')
        ax2.set_title('ECE vs Sample Count (Lower ECE = Better)')
        ax2.grid(True, alpha=0.3)
        
        # Add object labels to scatter plot
        for i, obj in enumerate(objects):
            ax2.annotate(obj, (total_counts[i], ece_scores[i]), 
                        xytext=(5, 5), textcoords='offset points', 
                        fontsize=8, ha='left')
        
        # Add horizontal lines for ECE thresholds
        ax2.axhline(y=0.05, color='green', linestyle='--', alpha=0.7, label='Excellent (≤0.05)')
        ax2.axhline(y=0.10, color='lightgreen', linestyle='--', alpha=0.7, label='Good (≤0.10)')
        ax2.axhline(y=0.15, color='yellow', linestyle='--', alpha=0.7, label='Fair (≤0.15)')
        ax2.axhline(y=0.20, color='orange', linestyle='--', alpha=0.7, label='Poor (≤0.20)')
        ax2.legend()
        
        plt.tight_layout()
        
        # Save the plot
        output_file = 'ece_calibration_analysis.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ ECE visualization saved to: {output_file}")
        
        # Show the plot
        plt.show()
        
    except Exception as e:
        print(f"Warning: Could not create ECE visualization: {e}")
        import traceback
        traceback.print_exc()



def create_probability_distribution_plots(results, target_objects):
    """Create probability distribution histograms for each object"""
    
    try:
        print(f"\nCreating probability distribution plots...")
        
        # Create a large figure with subplots
        n_objects = len(target_objects)
        n_cols = 5  # 5 columns
        n_rows = (n_objects + n_cols - 1) // n_cols  # Calculate rows needed
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(20, 4*n_rows))
        fig.suptitle('Probability Distribution for Each Object', fontsize=16, y=0.98)
        
        # Flatten axes if it's 2D
        if n_rows == 1:
            axes = [axes] if n_cols == 1 else axes
        else:
            axes = axes.flatten()
        
        for i, obj_type in enumerate(target_objects):
            ax = axes[i]
            
            if obj_type in results and results[obj_type]:
                # Get all probabilities for this object
                all_probs = []
                sample_types = []
                
                for sample_type, stats in results[obj_type].items():
                    if 'probabilities' in stats and len(stats['probabilities']) > 0:
                        all_probs.extend(stats['probabilities'])
                        sample_types.extend([sample_type] * len(stats['probabilities']))
                
                if all_probs:
                    # Create histogram
                    n, bins, patches = ax.hist(all_probs, bins=20, alpha=0.7, edgecolor='black')
                    
                    # Color patches based on sample type (use first sample type for each bin)
                    # Since we can't color individual bars by sample type in a single histogram,
                    # we'll create separate histograms for positive and negative samples
                    pos_probs = [p for p, st in zip(all_probs, sample_types) if st == 'positive']
                    neg_probs = [p for p, st in zip(all_probs, sample_types) if st == 'negative']
                    
                    # Clear the current histogram
                    ax.clear()
                    
                    # Plot positive samples in blue
                    if pos_probs:
                        ax.hist(pos_probs, bins=20, alpha=0.7, color='blue', edgecolor='black', label='Positive')
                    
                    # Plot negative samples in red
                    if neg_probs:
                        ax.hist(neg_probs, bins=20, alpha=0.7, color='red', edgecolor='black', label='Negative')
                    
                    # Add vertical line at probability 0.5
                    ax.axvline(x=0.5, color='green', linestyle='--', linewidth=2, label='Threshold (0.5)')
                    
                    # Add mean line
                    mean_prob = np.mean(all_probs)
                    ax.axvline(x=mean_prob, color='orange', linestyle='-', linewidth=2, label=f'Mean ({mean_prob:.3f})')
                    
                    ax.set_xlabel('Probability')
                    ax.set_ylabel('Frequency')
                    ax.set_title(f'{obj_type}\n({len(all_probs)} samples)')
                    ax.grid(True, alpha=0.3)
                    ax.legend()
                    
                    # Set x-axis limits
                    ax.set_xlim(0, 1)
                    
                    # Add text with statistics
                    pos_count = sum(1 for st in sample_types if st == 'positive')
                    neg_count = sum(1 for st in sample_types if st == 'negative')
                    ax.text(0.02, 0.98, f'Pos: {pos_count}\nNeg: {neg_count}', 
                           transform=ax.transAxes, verticalalignment='top',
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
                else:
                    ax.text(0.5, 0.5, 'No data', ha='center', va='center', 
                           transform=ax.transAxes, fontsize=12)
                    ax.set_title(f'{obj_type}\n(No data)')
            else:
                ax.text(0.5, 0.5, 'No data', ha='center', va='center', 
                       transform=ax.transAxes, fontsize=12)
                ax.set_title(f'{obj_type}\n(No data)')
            
            # Remove empty subplots
            if i >= n_objects - 1:
                for j in range(i + 1, len(axes)):
                    fig.delaxes(axes[j])
                break
        
        plt.tight_layout()
        
        # Save the plot
        output_file = 'probability_distribution_plots.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Probability distribution plots saved to: {output_file}")
        
        # Show the plot
        plt.show()
        
    except Exception as e:
        print(f"Warning: Could not create probability distribution plots: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":    
    analyze_all_features_files()