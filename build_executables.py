import os
import shutil
import subprocess
import sys

try:
    from PIL import Image
except Exception:
    Image = None

def convert_png_to_ico(png_path: str, ico_path: str) -> bool:
    """Convert a PNG to ICO with multiple sizes for Windows executables."""
    if not os.path.isfile(png_path):
        print(f"Icon source not found: {png_path}")
        return False
    if Image is None:
        print("Pillow is not installed; cannot convert PNG to ICO. Install with: pip install pillow")
        return False
    try:
        img = Image.open(png_path)
        # Ensure RGBA for transparency handling
        if img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA")
        sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(ico_path, sizes=sizes)
        print(f"Generated icon: {ico_path}")
        return True
    except Exception as e:
        print(f"Failed to convert {png_path} to {ico_path}: {e}")
        return False


def build_executable(script_name, executable_name, extra_datas, icon_path=None):
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

    if icon_path and os.path.isfile(icon_path):
        command.extend(['--icon', icon_path])
    else:
        if icon_path:
            print(f"Warning: Icon path not found or invalid, skipping icon: {icon_path}")

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

    # Prepare icons
    icons_dir = os.path.join('build', 'icons')
    os.makedirs(icons_dir, exist_ok=True)
    client_png = 'client.png'
    server_png = 'server.png'
    client_ico = os.path.join(icons_dir, 'client.ico')
    server_ico = os.path.join(icons_dir, 'server.ico')

    client_icon_ok = convert_png_to_ico(client_png, client_ico)
    server_icon_ok = convert_png_to_ico(server_png, server_ico)

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
        extra_datas=common_data,
        icon_path=server_ico if server_icon_ok else None,
    )

    # Build the client
    if server_built:
        print("\nBuilding Client Executable...")
        client_built = build_executable(
            script_name='working_client.py',
            executable_name='LAN_Auto_Install_Client',
            extra_datas=common_data,
            icon_path=client_ico if client_icon_ok else None,
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
