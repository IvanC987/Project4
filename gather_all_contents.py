import os

files_and_dirs = os.listdir('.')  # Lists everything in the current directory

if ".git" in files_and_dirs:
    files_and_dirs.remove(".git")

if "__pycache__" in files_and_dirs:
    files_and_dirs.remove("__pycache__")


output_filename = "all_contents.txt"

allowed_files_exts = ["html", "py", "css", "txt"]


def gather_text(path):
    result = []

    if os.path.isdir(path):
        sub_paths = os.listdir(path)
        for p in sub_paths:
            temp = gather_text(os.path.join(path, p))
            result.extend(temp)
    else:
        ext = path.split(".")[-1]
        if ext not in allowed_files_exts or output_filename in path:
            return []

        with open(path, "r", encoding="utf-8") as f:
            result.append(f"=========\n{path}\n===============\n{f.read()}\n")

    return result



final_result = []
for p in files_and_dirs:
    r = gather_text(p)
    final_result.extend(r)



with open(output_filename, "w", encoding="utf-8") as f:
    for content in final_result:
        f.write(f"{content}\n")

print("Completed!")








