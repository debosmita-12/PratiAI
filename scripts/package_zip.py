import os
import zipfile
import sys
import shutil

def make_zip():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print(f"Project root: {project_root}")
    
    # Exclude ephemeral/build dirs and virtual envs
    EXCLUDE_DIRS = {
        'node_modules',
        'venv',
        '.venv',
        'env',
        '.pytest_cache',
        '__pycache__',
        '.git'
    }
    
    EXCLUDE_EXTS = {
        '.pyc',
        '.pyo',
        '.pyd'
    }
    
    # Target zip destinations:
    # 1. Downloads folder
    # 2. Desktop folder
    # 3. Artifact directory for web download
    destinations = [
        r"C:\Users\User\Downloads\PratiAI_SIH2026_RailSamanV.zip",
        r"C:\Users\User\OneDrive\Desktop\PratiAI_SIH2026_RailSamanV.zip",
        r"C:\Users\User\.gemini\antigravity\brain\c1252693-8643-438d-a60a-2867d3ff5402\PratiAI_SIH2026_RailSamanV.zip"
    ]
    
    primary_zip = destinations[0]
    os.makedirs(os.path.dirname(primary_zip), exist_ok=True)
    
    if os.path.exists(primary_zip):
        os.remove(primary_zip)
        
    print(f"Creating ZIP archive at: {primary_zip}...")
    file_count = 0
    total_bytes = 0
    
    with zipfile.ZipFile(primary_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(project_root):
            # Modify dirs in-place to avoid descending into excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.git')]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in EXCLUDE_EXTS:
                    continue
                
                full_path = os.path.join(root, file)
                # Compute relative path inside the zip archive, placing everything under "PratiAI/"
                rel_path = os.path.relpath(full_path, project_root)
                archive_name = os.path.join("PratiAI", rel_path)
                
                try:
                    zf.write(full_path, archive_name)
                    file_count += 1
                    total_bytes += os.path.getsize(full_path)
                except Exception as e:
                    print(f"Skipping {full_path}: {e}")
                    
    zip_size = os.path.getsize(primary_zip)
    print(f"ZIP creation successful!")
    print(f"Total files archived: {file_count}")
    print(f"Uncompressed size: {total_bytes / (1024*1024):.2f} MB")
    print(f"Compressed ZIP size: {zip_size / (1024*1024):.2f} MB")
    
    # Copy to Desktop and Artifact dir
    for dest in destinations[1:]:
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(primary_zip, dest)
            print(f"Copied to: {dest}")
        except Exception as e:
            print(f"Could not copy to {dest}: {e}")

if __name__ == "__main__":
    make_zip()
