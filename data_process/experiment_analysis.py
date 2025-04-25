import os
import csv
from datetime import datetime
import numpy as np
import argparse


VALID_EXP_TYPES = ["C", "P", "G", "O"]
FILE_NAME = "processed_data.csv"


def parse_arguments():
    """Parse command line arguments using argparse."""
    parser = argparse.ArgumentParser(description="Process grasping experiment data.")
    parser.add_argument("experiment_timestamp", type=str, help="The experiment timestamp to process")
    return parser.parse_args()


def collection_types(root_dir):
    """Identify the valid session types in the directory."""
    exist_types = []
    for folder in os.listdir(root_dir):
        if folder in VALID_EXP_TYPES:
            exist_types.append(folder)
    return exist_types


def sort_exist_session_types_according_to_valid_types(exist_session_types):
    """Sort session types according to VALID_TYPES."""
    return sorted(exist_session_types, key=lambda x: VALID_EXP_TYPES.index(x))


def create_output_directory_and_file(output_path):
    """Create the output directory and file."""
    os.makedirs(output_path, exist_ok=True)
    output_filename = os.path.join(output_path, FILE_NAME)
    with open(output_filename, "w"):
        pass  # Just create an empty file
    return output_filename


def get_objects_list(root_dir):
    """Retrieve the object list from the rotation sequence data."""
    rotation_file = os.path.join(root_dir, "meta_data", "RotationSeqData.csv")
    with open(rotation_file, "r") as f:
        objects_list = [line.split(",")[0] for line in f.readlines() if line.strip()]
    return objects_list


def write_header_and_objects_list_to_file(exist_session_types, objects_list, output_filename):
    """Write the header and object list to the output CSV file."""
    header = ["objName"]
    for session_type in exist_session_types:
        header.append(f"{session_type}_CatchDuration")
        header.append(f"{session_type}_Accuracy")

    with open(output_filename, "w") as f:
        f.write(",".join(header) + "\n")
        for obj in objects_list:
            row = [obj] + [""] * (len(exist_session_types) * 2)
            f.write(",".join(row) + "\n")


def calculate_catch_duration_and_accuracy(session_type, root_dir):
    """Calculate catch duration and accuracy from the grasping data."""
    session_folder = os.path.join(root_dir, session_type)
    grasping_file = os.path.join(session_folder, "GraspingData.csv")
    if not os.path.exists(grasping_file):
        print(f"Error: File '{grasping_file}' does not exist.")
        return {}

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

            accuracy = round(1 / (wrong_attempt + 1), 2)
            duration = (end_time - start_time).total_seconds()

            results[obj_name] = (duration, accuracy)

    return results


def write_data_to_file(results, output_filename, index):
    """Write the calculated results to the output CSV file."""
    with open(output_filename, "r") as f:
        lines = f.readlines()

    for i in range(1, len(lines)):
        line = lines[i].strip().split(",")
        obj_name = line[0]

        if obj_name in results:
            duration, accuracy = results[obj_name]
            line[index * 2 + 1] = str(duration)
            line[index * 2 + 2] = str(accuracy)

        lines[i] = ",".join(line) + "\n"

    with open(output_filename, "w") as f:
        f.writelines(lines)


def calculate_mean_and_variance(output_filename):
    """Calculate the mean and variance for each column."""
    with open(output_filename, "r") as f:
        csv_reader = csv.reader(f)
        headers = next(csv_reader)
        data = list(csv_reader)

    columns = list(zip(*data))
    stats = {"mean": [], "variance": []}

    for i, header in enumerate(headers[1:], start=1):
        try:
            values = [float(value) for value in columns[i] if value.strip()]
            mean = round(np.mean(values), 2)
            variance = round(np.var(values, ddof=0), 2)
            stats["mean"].append(mean)
            stats["variance"].append(variance)
        except ValueError:
            stats["mean"].append("")
            stats["variance"].append("")

    return stats


def append_stats_to_file(output_filename, stats):
    """Append the mean and variance statistics to the output CSV file."""
    with open(output_filename, "r") as f:
        lines = f.readlines()

    mean_row = ["MEAN"] + stats["mean"]
    var_row = ["VAR"] + stats["variance"]

    lines.insert(1, ",".join(map(str, mean_row)) + "\n")
    lines.insert(2, ",".join(map(str, var_row)) + "\n")

    with open(output_filename, "w") as f:
        f.writelines(lines)


def main():
    args = parse_arguments()

    root_dir = f"../DistanceGrasp/Assets/LogData/{args.experiment_timestamp}"
    output_path = f"{root_dir}/processed_data"
    output_filename = create_output_directory_and_file(output_path)

    exist_session_types = collection_types(root_dir)
    exist_session_types = sort_exist_session_types_according_to_valid_types(exist_session_types)

    objects_list = get_objects_list(root_dir)
    write_header_and_objects_list_to_file(exist_session_types, objects_list, output_filename)

    # Calculate the catch duration and accuracy for each session type and write it to the file
    for index, session_type in enumerate(exist_session_types):
        results = calculate_catch_duration_and_accuracy(session_type, root_dir)
        write_data_to_file(results, output_filename, index)

    # Calculate mean and variance for each column and append to the file
    stats = calculate_mean_and_variance(output_filename)
    append_stats_to_file(output_filename, stats)


if __name__ == "__main__":
    main()
