#!/usr/bin/env python3

import subprocess
import os
import sys
from pathlib import Path

def clone_repository():
    """
    Clone the even_glasses repository with all branches and history.
    """
    repo_url = "https://github.com/emingenc/even_glasses.git"
    target_dir = "even_glasses"

    print(f"Starting to clone repository from {repo_url}...")

    try:
        # Remove target directory if it exists
        if os.path.exists(target_dir):
            print(f"Directory {target_dir} already exists. Removing it...")
            subprocess.run(['rm', '-rf', target_dir], check=True)

        # Clone the repository with all branches
        clone_process = subprocess.run(
            ['git', 'clone', '--recursive', repo_url],
            check=True,
            capture_output=True,
            text=True
        )

        if clone_process.returncode == 0:
            print("Repository cloned successfully!")
            
            # Verify the clone by checking if the directory exists
            if os.path.exists(target_dir):
                print(f"Verified: {target_dir} directory exists")
                
                # Get all branches
                os.chdir(target_dir)
                subprocess.run(
                    ['git', 'fetch', '--all'],
                    check=True
                )
                
                # Print repository information
                print("\nRepository Information:")
                subprocess.run(['git', 'branch', '-a'], check=True)
                print("\nRemote Information:")
                subprocess.run(['git', 'remote', '-v'], check=True)
                
                return True
            else:
                print(f"Error: {target_dir} directory was not created")
                return False
                
    except subprocess.CalledProcessError as e:
        print(f"Error during cloning: {str(e)}")
        print(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False

def main():
    """
    Main function to execute the cloning process.
    """
    print("Starting repository cloning process...")
    
    if clone_repository():
        print("\nCloning completed successfully!")
        sys.exit(0)
    else:
        print("\nCloning failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
