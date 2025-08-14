import os
import shutil
import subprocess
import sys

def build_executable(script_name, executable_name, extra_datas):
    """
    Builds a single executable using PyInstaller.
    """
    command = [
        'pyinstaller',
        '--name', executable_name,
        '--onefile',
        '--windowed',
        '--clean',
    ]

    for data in extra_datas:
        command.extend(['--add-data', data])

    command.append(script_name)

    print(f"Running command: {' '.join(command)}")
    
    try:
        subprocess.check_call(command)
        print(f"Successfully built {executable_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building {executable_name}: {e}")
        return False
    except FileNotFoundError:
        print("Error: PyInstaller is not installed or not in the system's PATH.")
        print("Please install it using: pip install pyinstaller")
        return False

def main():
    print("Starting the build process...")

    # Clean up previous builds
    for dir_name in ['dist', 'build']:
        if os.path.isdir(dir_name):
            try:
                shutil.rmtree(dir_name)
            except PermissionError:
                print(f"Could not remove '{dir_name}'. Please make sure no applications from a previous build are running.")
                sys.exit(1)

    # Data to be included in both executables
    common_data = [
        f"network{os.pathsep}network",
        f"ui{os.pathsep}ui",
        f"utils{os.pathsep}utils",
    ]

    # Build the server
    print("\nBuilding Server Executable...")
    server_built = build_executable(
        script_name='working_server.py',
        executable_name='LAN_Auto_Install_Server',
        extra_datas=common_data
    )

    # Build the client
    if server_built:
        print("\nBuilding Client Executable...")
        client_built = build_executable(
            script_name='working_client.py',
            executable_name='LAN_Auto_Install_Client',
            extra_datas=common_data
        )

        if client_built:
            print("\nBuild process completed successfully!")
            print(f"Executables are located in the '{os.path.abspath('dist')}' directory.")
        else:
            print("\nClient build failed. Please check the errors above.")
    else:
        print("\nServer build failed. Aborting client build.")

if __name__ == '__main__':
    main()
