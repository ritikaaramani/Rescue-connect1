import os
import shutil

src_dir = r"c:\Users\VAIBHAVI\Rescue-connect1\user_app\rescue_connect\authority\public\images"
dest_dir = r"c:\Users\VAIBHAVI\Rescue-connect1\Traffic_Model1\emergency_routing_flutter\assets\images"

print(f"Creating {dest_dir}")
os.makedirs(dest_dir, exist_ok=True)

print(f"Copying from {src_dir} to {dest_dir}")
for f in os.listdir(src_dir):
    if f.endswith('.png'):
        src_file = os.path.join(src_dir, f)
        dest_file = os.path.join(dest_dir, f)
        print(f"Copying {f}...")
        shutil.copy2(src_file, dest_file)

print("Done copying.")
print("Files in destination:")
print(os.listdir(dest_dir))
