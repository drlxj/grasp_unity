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
OUTPUT_PATH = f"{ROOT_DIR}/processed_data"
FILE_NAME = "processed_data.csv"
VALID_TYPES = ["C", "P", "G", "O"]


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


def create_output_directory_and_file(output_path):
    # Create the output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)

    # Create an empty file in the output directory
    with open(os.path.join(output_path, FILE_NAME), "w") as f:
        f.write("")  # Create an empty file

    return os.path.join(output_path, FILE_NAME)


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


def write_header_and_objects_list_to_file(exist_session_types, objects_list, output_filename):
    # header object_name, session_type's catch duration, session_type's accuracy
    header = ["objName"]
    for session_type in exist_session_types:
        header.append(f"{session_type}_CatchDuration")
        header.append(f"{session_type}_Accuracy")
        # header.append(f"{session_type}_NumberOfAttempts")

    # Write the header and objects list to the file
    with open(output_filename, "w") as f:
        # Write the header
        f.write(",".join(header) + "\n")

        # Write the objects list (empty values for session data)
        for obj in objects_list:
            row = [obj] + [""] * (len(exist_session_types) * 2)  # Empty placeholders for session data
            f.write(",".join(row) + "\n")


def calculate_catch_duration_and_accuracy_and_attempts(session_type):
    session_folder = os.path.join(ROOT_DIR, session_type)
    # Read the session file
    grasping_file = os.path.join(session_folder, "GraspingData.csv")
    if not os.path.exists(grasping_file):
        print(f"Error: File '{grasping_file}' does not exist.")
        return

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
            results[obj_name] = (duration, accuracy)

    return results


def write_data_to_file(results, output_filename, index):
    with open(output_filename, "r") as f:
        lines = f.readlines()

    # Update the file with the calculated values
    for i in range(1, len(lines)):
        line = lines[i].strip().split(",")
        obj_name = line[0]

        # Check if the object name exists in the results
        if obj_name in results:
            duration, accuracy = results[obj_name]
            # duration, number_of_attempts = results[obj_name]
            line[index * 2 + 1] = str(duration)  # CatchDuration
            line[index * 2 + 2] = str(accuracy)  # Accuracy
            # line[index * 2 + 2] = str(number_of_attempts) # NumberOfAttempts
            # print("line:", line)

        # Update the line in the lines list
        lines[i] = ",".join(line) + "\n"

    # Write back to the file
    with open(output_filename, "w") as f:
        f.writelines(lines)

def calculate_mean_and_variance(output_filename):
    with open(output_filename, "r") as f:
        csv_reader = csv.reader(f)
        headers = next(csv_reader)  # Skip the header
        data = list(csv_reader)

    # Transpose the data to process columns
    columns = list(zip(*data))

    # Initialize results dictionary
    stats = {"mean": [], "variance": []}

    # Iterate over columns starting from the second (skip objName)
    for i, header in enumerate(headers[1:], start=1):
        try:
            # Convert column values to floats, ignoring empty strings
            values = [float(value) for value in columns[i] if value.strip()]
            mean = round(np.mean(values), 2)
            variance = round(np.var(values, ddof=0), 2)  # Population variance
            stats["mean"].append(mean)
            stats["variance"].append(variance)
        except ValueError:
            # Skip columns that cannot be converted to floats
            stats["mean"].append("")
            stats["variance"].append("")

    return stats

def append_stats_to_file(output_filename, stats):
    with open(output_filename, "r") as f:
        lines = f.readlines()

    # Prepare mean and variance rows
    mean_row = ["MEAN"] + stats["mean"]  # Add "MEAN" as the first cell
    var_row = ["VAR"] + stats["variance"]  # Add "VAR" as the first cell

    # Convert rows to CSV format
    mean_line = ",".join(map(str, mean_row)) + "\n"
    var_line = ",".join(map(str, var_row)) + "\n"

    # Insert mean and variance rows at the beginning
    lines.insert(1, mean_line)  # Insert mean row after the header
    lines.insert(2, var_line)  # Insert variance row after the mean row

    # Write back to the file
    with open(output_filename, "w") as f:
        f.writelines(lines)
    
def main():
    exist_session_types = collection_types()
    exist_session_types = sort_exist_session_types_according_to_valid_types(exist_session_types)
    output_filename = create_output_directory_and_file(OUTPUT_PATH)
    objects_list = get_objects_list()
    write_header_and_objects_list_to_file(exist_session_types, objects_list, output_filename)

    # calculate the catch duration and accuracy for each session type
    # and write it to the file
    index = 0
    for session_type in exist_session_types:
        result = calculate_catch_duration_and_accuracy_and_attempts(session_type)
        write_data_to_file(result, output_filename, index)
        index += 1
    
    # calculate mean and variance for each column
    stats = calculate_mean_and_variance(output_filename)

    # write the stats to the file
    append_stats_to_file(output_filename, stats)



if __name__ == "__main__":
    main()
