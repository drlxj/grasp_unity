#!/usr/bin/env python3
"""
Test script to compare npz files between two folders and visualize similar data
"""

import numpy as np
import torch
from pathlib import Path
import json
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
import sys
import os

# Add the current directory to Python path to import functions
sys.path.append('.')

from npz_generator_data_collection import visualize_scene
from nets import InferenceNet
from config import model_config

def load_npz_file(file_path):
    """Load npz file and return data dictionary"""
    try:
        data = np.load(file_path, allow_pickle=True)
        return {key: data[key] for key in data.keys()}
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def calculate_similarity_using_inference_net(data1, data2, model):
    """Calculate similarity using InferenceNet features"""
    similarity_scores = {}

    # Prepare data for the model
    if 'object_point_cloud' in data1 and 'subject_joints_pos_rel2wrist' in data1 and \
        'object_pointcloud' in data2 and 'subject_joints_pos_rel2wrist' in data2:
        
        # Prepare data1
        obj_pcl1 = torch.tensor(data1['object_point_cloud'], dtype=torch.float32).unsqueeze(0)  # (1, N, 3)
        hand_joints1 = torch.tensor(data1['subject_joints_pos_rel2wrist'], dtype=torch.float32).unsqueeze(0)  # (1, 21, 3)
        
        # Prepare data2
        obj_pcl2 = torch.tensor(data2['object_pointcloud'], dtype=torch.float32).unsqueeze(0)  # (1, N, 3)
        hand_joints2 = torch.tensor(data2['subject_joints_pos_rel2wrist'], dtype=torch.float32).unsqueeze(0)  # (1, 21, 3)
        
        # calculate the distance between the two object point clouds
        distance = torch.norm(obj_pcl1 - obj_pcl2, dim=1).mean().item()
        similarity_scores['object_point_cloud_distance'] = distance
        
        # calculate the distance between the two hand joints
        distance = torch.norm(hand_joints1 - hand_joints2, dim=1).mean().item()
        similarity_scores['hand_joints_distance'] = distance
        with torch.no_grad():
            # Get features from model
            pred1 = model(hand_joints=hand_joints1, obj_pcl=obj_pcl1)
            pred2 = model(hand_joints=hand_joints2, obj_pcl=obj_pcl2)
            
            # Calculate fused embedding distance
            fused_distance = torch.norm(pred1["obj_logit"] - pred2["obj_logit"], dim=1).mean().item()
            similarity_scores['fused_embedding_distance'] = fused_distance
            similarity_scores['ref_prob'] = torch.sigmoid(pred1["obj_logit"]).item()
            similarity_scores['test_prob'] = torch.sigmoid(pred2["obj_logit"]).item()
                
    return similarity_scores


def find_most_similar_files(reference_folder, test_folder, model, top_k=5):
    """Find the most similar files between two folders using InferenceNet"""
    reference_files = list(reference_folder.glob("**/*.npz"))
    test_files = list(test_folder.glob("**/*.npz"))
    
    print(f"Found {len(reference_files)} reference files and {len(test_files)} test files")
    
    results = []
    
    for test_file in test_files:
        print(f"\nProcessing test file: {test_file.name}")
        test_data = load_npz_file(test_file)
        
        if test_data is None:
            continue
        
        file_similarities = []
        
        for ref_file in reference_files:
            ref_data = load_npz_file(ref_file)
            
            if ref_data is None:
                continue
            
            # Calculate similarity using InferenceNet
            similarity = calculate_similarity_using_inference_net(test_data, ref_data, model)
            
            if similarity:
                # Create combined similarity score using all available metrics
                combined_score = 0
                weights = {
                    'object_point_cloud_distance': 0.0,    # Lower distance = higher similarity
                    'hand_joints_distance': 0.0,           # Lower distance = higher similarity
                    'fused_embedding_distance': -1.0,       # Lower distance = higher similarity
                }
                
                for metric, value in similarity.items():
                    if metric in weights:
                        # Normalize distance values using exponential decay
                        combined_score += weights[metric] * value
                
                file_similarities.append({
                    'reference_file': ref_file,
                    'similarity_scores': similarity,
                    'combined_score': combined_score
                })
        
        # Sort by combined similarity score (higher is more similar)
        file_similarities.sort(key=lambda x: x['combined_score'], reverse=True)
        
        # Store top results
        results.append({
            'test_file': test_file,
            'test_data': test_data,
            'top_matches': file_similarities[:top_k]
        })
    
    return results

def visualize_similar_data(results, output_dir):
    """Visualize the similar data pairs"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for result in results:
        test_file = result['test_file']
        test_data = result['test_data']
        
        print(f"\nVisualizing results for: {test_file.name}")
        
        # Create output subdirectory for this test file
        test_output_dir = output_dir / test_file.stem
        test_output_dir.mkdir(exist_ok=True)
        
        # Visualize test data
        if 'subject_joints_pos_rel2wrist' in test_data and 'object_pointcloud' in test_data:
            try:
                hand_pts = test_data['subject_joints_pos_rel2wrist']
                obj_pcl = test_data['object_pointcloud']
                obj_trans = test_data.get('object_translation', np.zeros(3))
                
                # Create joint colors (assuming 21 joints)
                joint_colors = np.array([
                    [255, 0, 0, 255],    # root
                    [255, 0, 0, 255],    [255, 0, 0, 255],    [255, 0, 0, 255],    [255, 0, 0, 255],    # thumb
                    [0, 255, 0, 255],    [0, 255, 0, 255],    [0, 255, 0, 255],    [0, 255, 0, 255],    # index
                    [0, 0, 255, 255],    [0, 0, 255, 255],    [0, 0, 255, 255],    [0, 0, 255, 255],    # middle
                    [255, 255, 0, 255],  [255, 255, 0, 255],  [255, 255, 0, 255],  [255, 255, 0, 255],  # ring
                    [255, 0, 255, 255],  [255, 0, 255, 255],  [255, 0, 255, 255],  [255, 0, 255, 255]   # pinky
                ])
                
                # Ensure we have enough colors
                while len(joint_colors) < len(hand_pts):
                    joint_colors = np.vstack([joint_colors, joint_colors[-1:]])
                
                # Save test data visualization
                test_img_path = test_output_dir / f"test_data.png"
                visualize_scene(
                    hand_pts, joint_colors, obj_pcl, obj_trans, 
                    save_image=True, save_path=test_img_path
                )
                print(f"Saved test visualization: {test_img_path}")
                
            except Exception as e:
                print(f"Error visualizing test data: {e}")
        
        # Visualize only the most similar reference data
        if result['top_matches']:
            best_match = result['top_matches'][0]  # Get the most similar match
            ref_file = best_match['reference_file']
            ref_data = load_npz_file(ref_file)
            
            if ref_data is not None and 'subject_joints_pos_rel2wrist' in ref_data and 'object_pointcloud' in ref_data:
                try:
                    hand_pts = ref_data['subject_joints_pos_rel2wrist']
                    obj_pcl = ref_data['object_pointcloud']
                    obj_trans = ref_data.get('object_translation', np.zeros(3))
                    
                    # Create joint colors
                    joint_colors = np.array([
                        [255, 0, 0, 255],    # root
                        [255, 0, 0, 255],    [255, 0, 0, 255],    [255, 0, 0, 255],    [255, 0, 0, 255],    # thumb
                        [0, 255, 0, 255],    [0, 255, 0, 255],    [0, 255, 0, 255],    [0, 255, 0, 255],    # index
                        [0, 0, 255, 255],    [0, 0, 255, 255],    [0, 0, 255, 255],    [0, 0, 255, 255],    # middle
                        [255, 255, 0, 255],  [255, 255, 0, 255],  [255, 255, 0, 255],  [255, 255, 0, 255],  # ring
                        [255, 0, 255, 255],  [255, 0, 255, 255],  [255, 0, 255, 255],  [255, 0, 255, 255]   # pinky
                    ])
                    
                    # Ensure we have enough colors
                    while len(joint_colors) < len(hand_pts):
                        joint_colors = np.vstack([joint_colors, joint_colors[-1:]])
                    
                    # Save best match visualization
                    best_match_img_path = test_output_dir / f"best_match_{ref_file.stem}.png"
                    visualize_scene(
                        hand_pts, joint_colors, obj_pcl, obj_trans, 
                        save_image=True, save_path=best_match_img_path
                    )
                    print(f"Saved best match visualization: {best_match_img_path}")
                    
                except Exception as e:
                    print(f"Error visualizing best match data: {e}")
        
        # Save similarity report
        report_path = test_output_dir / "similarity_report.txt"
        with open(report_path, 'w') as f:
            f.write(f"Similarity Analysis Report for: {test_file.name}\n")
            f.write("=" * 50 + "\n\n")
            
            if result['top_matches']:
                best_match = result['top_matches'][0]
                f.write(f"Best Match: {best_match['reference_file'].name}\n")
                f.write(f"Combined Score: {best_match['combined_score']:.4f}\n")
                f.write("Similarity Scores:\n")
                for metric, value in best_match['similarity_scores'].items():
                    f.write(f"  {metric}: {value:.6f}\n")
                f.write("\n")
                
                # Also show top 3 matches for reference
                f.write("Top 3 Matches:\n")
                f.write("-" * 30 + "\n")
                for i, match in enumerate(result['top_matches'][:3]):
                    f.write(f"{i+1}. {match['reference_file'].name} (Score: {match['combined_score']:.4f})\n")
            else:
                f.write("No matches found.\n")
        
        print(f"Saved similarity report: {report_path}")

def main():
    """Main function"""
    # Define paths
    reference_folder = Path(r"C:\Users\Researcher\grasping-unity\model\session_npz_files\unity_data_collection_20250805\unity_data_collection_20250805")
    test_folder = Path(r"C:\Users\Researcher\grasping-unity\model\session_npz_files\test")
    output_dir = Path("similarity_analysis_results")
    
    # Check if folders exist
    if not reference_folder.exists():
        print(f"Reference folder not found: {reference_folder}")
        return
    
    if not test_folder.exists():
        print(f"Test folder not found: {test_folder}")
        return
    
    print("Starting similarity analysis using InferenceNet...")
    print(f"Reference folder: {reference_folder}")
    print(f"Test folder: {test_folder}")
    print(f"Output directory: {output_dir}")
    print(f"Will generate: test_data.png + best_match.png for each test file")
    
    # Load InferenceNet model
    print("Loading InferenceNet model...")
    model = InferenceNet(**model_config).to('cpu')
    ckpt = torch.load(r'./files/0025_unityall_hand63_objects25_pos=neg.tar', map_location=torch.device('cpu'))
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()
    print("Model loaded successfully!")
    
    # Find similar files
    results = find_most_similar_files(reference_folder, test_folder, model, top_k=3)
    
    if not results:
        print("No results found!")
        return
    
    # Visualize results
    visualize_similar_data(results, output_dir)
    
    print(f"\nAnalysis complete! Results saved to: {output_dir}")
    
    # Print summary
    print("\nSummary:")
    for result in results:
        test_file = result['test_file']
        top_match = result['top_matches'][0] if result['top_matches'] else None
        
        if top_match:
            print(f"{test_file.name} -> {top_match['reference_file'].name} (Score: {top_match['combined_score']:.4f})")
            print(f"Reference probability: {top_match['similarity_scores']['ref_prob']:.4f}, Test probability: {top_match['similarity_scores']['test_prob']:.4f}")
        else:
            print(f"{test_file.name} -> No matches found")

if __name__ == "__main__":
    main()
