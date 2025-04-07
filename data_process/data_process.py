import os
import csv
from datetime import datetime

INPUT_EXPERIMENT_TIMESTAMP = "20250407_164224.809"
ROOT_DIR = f"../DistanceGrasp/Assets/LogData/{INPUT_EXPERIMENT_TIMESTAMP}"
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
    rotation_file = f"{ROOT_DIR}/meta_data/RotationSeqData.csv"
    # Read the rotation file and get the objects list
    # read tht first column of the file and return it as a list,  keep the first raw bacause there is no header
    with open(rotation_file, "r") as f:
        objects_list = [line.split(",")[0] for line in f.readlines() if line.strip()]

    return objects_list


def write_header_and_objects_list_to_file(exist_session_types, objects_list, output_filename):
    # header object_name, session_type's catch duration, session_type's accuracy
    header = ["objName"]
    for session_type in exist_session_types:
        header.append(f"{session_type}_CatchDuration")
        header.append(f"{session_type}_Accuracy")

    # Write the header and objects list to the file
    with open(output_filename, "w") as f:
        # Write the header
        f.write(",".join(header) + "\n")

        # Write the objects list (empty values for session data)
        for obj in objects_list:
            row = [obj] + [""] * (len(exist_session_types) * 2)  # Empty placeholders for session data
            f.write(",".join(row) + "\n")


def calculate_catch_duration_and_accuracy(session_type):
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

            # Calculate accuracy
            accuracy = 1 / (wrong_attempt + 1)

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
            line[index * 2 + 1] = str(duration)  # CatchDuration
            line[index * 2 + 2] = str(accuracy)  # Accuracy
            # print("line:", line)

        # Update the line in the lines list
        lines[i] = ",".join(line) + "\n"

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
        result = calculate_catch_duration_and_accuracy(session_type)
        write_data_to_file(result, output_filename, index)
        index += 1


if __name__ == "__main__":
    main()
