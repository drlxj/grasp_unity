import os

def count_npz_files(directory):
    count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.npz'):
                count += 1
    return count

# 使用方法：替换这里的路径为你要查询的目录
path_to_check = r'C:\Users\Researcher\grasping-unity\model\session_npz_files\s3'
npz_file_count = count_npz_files(path_to_check)
print(f"在路径 {path_to_check} 下共找到 {npz_file_count} 个 .npz 文件。")