from datetime import datetime
import csv
import os
import numpy as np



def parse_time(time_str):
    return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")


def process_detail_data(input_filename, input_csv, output_dir):
    with open(input_csv, "r") as file:
        reader = csv.reader(file)
        data = list(reader)

    result = [("ObjId", "Name", "CatchDuration", "AttemptCount")]

    for idx, (name, attempt_count, start_time, end_time) in enumerate(data, start=1):
        start_time = parse_time(start_time.strip())
        end_time = parse_time(end_time.strip())
        catch_duration = (end_time - start_time).total_seconds() + (end_time.microsecond - start_time.microsecond) / 1e6

        result.append((idx, name, f"{catch_duration:.2f}", attempt_count))

    filename = f"{input_filename}_detail.csv"
    output_csv = os.path.join(output_dir, filename)

    os.makedirs(output_dir, exist_ok=True)
    with open(output_csv, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(result)

    print(f"Processed data saved to {output_csv}")

    return filename


def summarize_data(input_filename, output_detail_filename, output_path):
    detail_input_csv = os.path.join(output_path, output_detail_filename)
    with open(detail_input_csv, "r") as file:
        reader = csv.reader(file)
        headers = next(reader)  # skip head
        data = list(reader)

    obj_count = len(data)
    catch_durations = np.array([float(row[2]) for row in data])
    attempt_counts = np.array([int(row[3]) for row in data])

    catch_duration_mean = np.mean(catch_durations)
    catch_duration_var = np.var(catch_durations, ddof=0)

    attempt_count_mean = np.mean(attempt_counts)
    attempt_count_var = np.var(attempt_counts, ddof=0)

    summary = [
        ["ObjCount", obj_count],
        ["CatchDuration_Mean", round(catch_duration_mean, 6)],
        ["CatchDuration_Variance", round(catch_duration_var, 6)],
        ["AttemptCount_Mean", round(attempt_count_mean, 6)],
        ["AttemptCount_Variance", round(attempt_count_var, 6)]
    ]

    print(f"round(catch_duration_mean, 6): {round(catch_duration_mean, 6)}")

    filename = f"{input_filename}_summary.csv"
    output_csv = os.path.join(output_path, filename)
    with open(output_csv, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(summary)

    print(f"Summary saved to {filename}")

    return

# todo change file name
input_filename = "GraspingData_20250304_180941_I"
input_csv = f"../DistanceGrasp/Assets/LogData/{input_filename}.csv"
output_path = f"./processed_data"
output_detail_filename = process_detail_data(input_filename, input_csv, output_path)
summarize_data(input_filename, output_detail_filename, output_path)

