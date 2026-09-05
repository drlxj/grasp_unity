import os
import csv
from datetime import datetime
import numpy as np
import sys
import glob

if len(sys.argv) < 2:
    print("Error: Please provide the experiment timestamp as an argument.")
    sys.exit(1)

INPUT_EXPERIMENT_TIMESTAMP = sys.argv[1]
ROOT_DIR = f"../user_study_data/{INPUT_EXPERIMENT_TIMESTAMP}"
OUTPUT_PATH = f"{ROOT_DIR}"
FILE_NAME = "processed_data.csv"
VALID_TYPES = ["C", "P", "G", "O"]
summary_dict = {}

def collection_types():
    exist_types = []
    for folder in os.listdir(ROOT_DIR):
        # if the folder'name is in valid_types, add it to the list
        if folder in VALID_TYPES:
            exist_types.append(folder)

    return exist_types


def sort_exist_session_types_according_to_valid_types(exist_session_types):
    # Sort the exist_session_types according to the order of VALID_TYPES
    sorted_exist_session_types = sorted(exist_session_types, key=lambda x: VALID_TYPES.index(x))
    # print(f"sorted_exist_session_types: {sorted_exist_session_types}")
    return sorted_exist_session_types


def create_output_directory_and_file(output_path, session_type):

    output_path_with_session_type = os.path.join(output_path, session_type)

    # Create an empty file in the output directory
    with open(os.path.join(output_path_with_session_type, FILE_NAME), "w") as f:
        f.write("")  # Create an empty file

    return os.path.join(output_path_with_session_type, FILE_NAME)

def create_summary_file(output_path):
    summary_file_name = "summary.csv"
    with open(os.path.join(output_path, summary_file_name), "w") as f:
        f.write("")  # Create an empty file

    return os.path.join(output_path, summary_file_name)


def get_objects_list():
    # Use glob to find all matching files
    rotation_files = glob.glob(f"{ROOT_DIR}/*/GraspingData.csv")
    
    if not rotation_files:
        raise FileNotFoundError(f"No files found matching pattern: {ROOT_DIR}/*/GraspingData.csv")
    
    # Read the first column of all matching files and return as a list
    objects_list = []
    for rotation_file in rotation_files:
        with open(rotation_file, "r") as f:
            objects_list.extend([line.split(",")[0] for line in f.readlines() if line.strip()])

    # Deduplicate the list
    objects_list = list(set(objects_list))

    return objects_list


def write_header_and_objects_list_to_file(session_type, objects_list, output_filename):
    # header object_name, session_type's catch duration, session_type's accuracy
    header = ["objName"]
    for session_type in session_type:
        header.append(f"{session_type}_CatchDuration")
        header.append(f"{session_type}_Accuracy")
        if session_type == "C":
            header.append(f"gesture_score_is_larger")
        # header.append(f"{session_type}_NumberOfAttempts")

    # Write the header and objects list to the file
    with open(output_filename, "w") as f:
        # Write the header
        f.write(",".join(header) + "\n")

        # Write the objects list (empty values for session data)
        for obj in objects_list:
            row = [obj] + [""] * (len(session_type) * 3)  # Empty placeholders for session data
            f.write(",".join(row) + "\n")

def write_header_and_method_list_to_summary_filename(exist_session_types, summary_filename):
    # header object_name, session_type's catch duration, session_type's accuracy
    header = ["methodName"]
    
    header.append(f"duration mean")
    header.append(f"duration var")
    header.append(f"acc mean")
    header.append(f"acc var")
    header.append(f"gesture percent")

    # Write the header and objects list to the file
    with open(summary_filename, "w") as f:
        # Write the header
        f.write(",".join(header) + "\n")

        # Write the objects list (empty values for session data)
        for session_type in exist_session_types:
            row = [session_type] + [""] * 5  # Empty placeholders for session data
            f.write(",".join(row) + "\n")

        # summary_row = ["summary"] + [""] * 5
        # f.write(",".join(summary_row) + "\n")


def calculate_catch_duration_and_accuracy_and_attempts(session_type):
    session_folder = os.path.join(ROOT_DIR, session_type)
    # Read the session file
    grasping_file = os.path.join(session_folder, "GraspingData.csv")
    if not os.path.exists(grasping_file):
        print(f"Error: File '{grasping_file}' does not exist.")
        return
    
    gesture_file = os.path.join(session_folder, "GestureData.csv")
    if not os.path.exists(gesture_file):
        print(f"Error: File '{gesture_file}' does not exist.")
        return
    
    if session_type == "C":
        gesture_is_larger_dict = {}
        with open(gesture_file, "r") as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                if not row or len(row) < 6:
                    continue

                if row[0] == "0":
                    continue

                obj_name = row[1]

                # if time limited
                if row[0] == "9":
                    gesture_is_larger_dict[obj_name] = ""

                raw_gesture_scores = row[5]

                gesture_scores_per_obj = raw_gesture_scores.split("/")
                
                scores = []
                for gesture_score_current_obj in gesture_scores_per_obj:
                    current_obj_name = gesture_score_current_obj.split("|")[0]
                    if current_obj_name == obj_name:
                        scores = gesture_score_current_obj.split("|")[1:]
                        gesture_score = float(scores[0])
                        pos_score = float(scores[1])

                        if gesture_score > pos_score:
                            gesture_is_larger_dict[obj_name] = "1"
                        else:
                            gesture_is_larger_dict[obj_name] = "0"
                        break

    results = {}
    with open(grasping_file, "r") as f:
        csv_reader = csv.reader(f)
        for row in csv_reader:
            if not row or len(row) < 4:
                continue  # Skip empty or invalid rows

            obj_name = row[0]
            wrong_attempt = int(row[1])
            start_time = datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S.%f")
            end_time = datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S.%f")
            
            # Calculate number of attempts
            number_of_attempts = wrong_attempt + 1

            # Calculate accuracy
            accuracy = round(1 / number_of_attempts, 2)

            # Calculate duration in seconds
            duration = (end_time - start_time).total_seconds()
            
            # Store results
            if session_type != "C": 
                results[obj_name] = (duration, accuracy, wrong_attempt)
            else:
                results[obj_name] = (duration, accuracy, wrong_attempt, gesture_is_larger_dict[obj_name])



    return results


def write_data_to_file(results, output_filename, session_type):
    with open(output_filename, "r") as f:
        lines = f.readlines()
    
    per_method_summary_dict = {}
    # Update the file with the calculated values
    for i in range(1, len(lines)):
        line = lines[i].strip().split(",")
        obj_name = line[0]

        # Check if the object name exists in the results
        if obj_name in results:
            if session_type == "C":
                duration, accuracy, wrong_attempt, gesture_is_larger = results[obj_name]
                line[1] = str(duration) # CatchDuration
                line[2] = str(accuracy) # Accuracy
                line[3] = str(gesture_is_larger)
                per_method_summary_dict[obj_name] = (duration, accuracy, wrong_attempt, gesture_is_larger)

            else: 
                duration, accuracy, wrong_attempt = results[obj_name]
                line[1] = str(duration)  # CatchDuration
                line[2] = str(accuracy)  # Accuracy
                per_method_summary_dict[obj_name] = (duration, accuracy, wrong_attempt)
            

        summary_dict[session_type] = per_method_summary_dict

        # Update the line in the lines list
        lines[i] = ",".join(line) + "\n"

    # Write back to the file
    with open(output_filename, "w") as f:
        f.writelines(lines)

def calculate_mean_and_variance(session_type, summary_filename):
    with open(summary_filename, "r") as f:
        csv_reader = csv.reader(f)
        headers = next(csv_reader)  # Skip the header
        rows = list(csv_reader)

    per_method_dur_acc_dict = {}
    for row in rows:
        if row[0] == session_type:
            summary_current_session_type = summary_dict[session_type]
            
            duration_list = []
            accuracy_list = []
            wrong_attempt_list = []
            gesture_is_larger_list = []
            for key, value in summary_current_session_type.items():
                duration_list.append(value[0])
                accuracy_list.append(value[1])
                wrong_attempt_list.append(value[2])
                if session_type == "C":
                    gesture_is_larger_list.append(value[3])

            # Convert string elements in the list to float
            duration_list = [float(x) for x in duration_list]
            accuracy_list = [float(x) for x in accuracy_list]
            duration_mean = round(np.mean(duration_list), 2)
            duration_variance = round(np.var(duration_list, ddof=0), 2)  # Population variance
            accuracy_mean = round(np.mean(accuracy_list), 2)
            accuracy_variance = round(np.var(accuracy_list, ddof=0), 2)  # Population variance
            gesture_percent = ""
            if session_type == "C":
                # print(f"gesture_is_larger_list: {gesture_is_larger_list}")  ['1', '1', '0', '0', '0']

                # amount of '1' number of gesture_is_larger_list
                count_of_ones = gesture_is_larger_list.count('1')

                # amount of '0' number of gesture_is_larger_list
                count_of_zeros = gesture_is_larger_list.count('0')

                gesture_percent = round(count_of_ones / (count_of_ones + count_of_zeros), 2)


            per_method_dur_acc_dict = {
                    "duration_mean": duration_mean, 
                    "duration_var": duration_variance,
                    "acc_mean": accuracy_mean,
                    "acc_var": accuracy_variance,
                    "gesture_percent": gesture_percent
                }
            
            return per_method_dur_acc_dict
        
def calculate_summary_mean_and_variance():
    # get all element from per_method_summary_dict in summary_dict
    all_duration_list = []
    all_wrong_attempt_list = []
    for session_type, per_method_summary_dict in summary_dict.items():
        for key, value in per_method_summary_dict.items():
            all_duration_list.append(value[0])
            all_wrong_attempt_list.append(value[2])
    
    all_duration_list = [float(x) for x in all_duration_list if x != ""]
    all_wrong_attempt_list = [int(x) for x in all_wrong_attempt_list if x != ""]
    # calculate the mean and variance for all duration and accuracy
    all_duration_mean = round(np.mean(all_duration_list), 2)
    all_duration_variance = round(np.var(all_duration_list, ddof=0), 2)  # Population variance
    # accuracy is round(1 / number_of_attempts, 2)
    all_accuracy_list = []
    for wrong_attempt in all_wrong_attempt_list:
        accuracy = round(1 / (wrong_attempt + 1), 2)
        all_accuracy_list.append(accuracy)

    all_accuracy_mean = round(np.mean(all_accuracy_list), 2)
    all_accuracy_variance = round(np.var(all_accuracy_list, ddof=0), 2)  # Population variance

    summary_dur_acc_dict = {
        "duration_mean": all_duration_mean, 
        "duration_var": all_duration_variance,
        "acc_mean": all_accuracy_mean,
        "acc_var": all_accuracy_variance,
        "gesture_percent": ""
    }

    return summary_dur_acc_dict



def append_summary_to_file(summary_filename, summary_dict):
    with open(summary_filename, "r") as f:
        csv_reader = csv.reader(f)
        headers = next(csv_reader)
        rows = list(csv_reader)

    # Update the file with the calculated values
    for i in range(0, len(rows)):
        line = rows[i]
        session_type = line[0]

        # Check if the session type exists in the summary_dict
        if session_type in summary_dict:
            duration_mean = summary_dict[session_type]["duration_mean"]
            duration_var = summary_dict[session_type]["duration_var"]
            acc_mean = summary_dict[session_type]["acc_mean"]
            acc_var = summary_dict[session_type]["acc_var"]
            gesture_percent = summary_dict[session_type]["gesture_percent"]

            line[1] = str(duration_mean)  # CatchDuration mean
            line[2] = str(duration_var)  # CatchDuration var
            line[3] = str(acc_mean)  # Accuracy mean
            line[4] = str(acc_var)  # Accuracy var
            line[5] = str(gesture_percent)  # gesture percent

    # print rows
    # print(f"rows: {rows}")

    # Write back to the file
    with open(summary_filename, "w") as f:
        # Write the header
        f.write(",".join(headers) + "\n")
        for row in rows:
            f.write(",".join(row) + "\n")
    
def main():
    exist_session_types = collection_types()
    exist_session_types = sort_exist_session_types_according_to_valid_types(exist_session_types)
    objects_list = get_objects_list()
    
    # calculate the catch duration and accuracy for each session type
    # and write it to the file
    for session_type in exist_session_types:
        output_filename = create_output_directory_and_file(OUTPUT_PATH, session_type)
        write_header_and_objects_list_to_file(session_type, objects_list, output_filename)
        result = calculate_catch_duration_and_accuracy_and_attempts(session_type)
        write_data_to_file(result, output_filename, session_type)
    

    # calculate summary statistics for each session type
    summary_filename = create_summary_file(OUTPUT_PATH)
    write_header_and_method_list_to_summary_filename(exist_session_types, summary_filename)
    summary_dict = {}
    for session_type in exist_session_types:
        per_method_dur_acc_dict = calculate_mean_and_variance(session_type, summary_filename)
        summary_dict[session_type] = per_method_dur_acc_dict
    

    # summary_dur_acc_dict = calculate_summary_mean_and_variance()
    # summary_dict["summary"] = summary_dur_acc_dict

    # # write the summary_dict to the file
    append_summary_to_file(summary_filename, summary_dict)

if __name__ == "__main__":
    main()
