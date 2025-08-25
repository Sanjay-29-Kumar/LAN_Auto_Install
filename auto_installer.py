import subprocess
import os
from pathlib import Path

class AutoInstaller:
    def __init__(self, installers_dir: str):
        self.installers_path = Path(installers_dir)
        self.SILENT_COMMANDS = {
            '.msi': self.install_msi,
            '.msp': self.install_msp,
            '.exe': self.install_exe,
            '.msix': self.install_msix,
            '.appx': self.install_msix,
            '.bat': self.install_batch,
            '.cmd': self.install_batch,
            '.ps1': self.install_powershell,
            '.zip': self.extract_archive,
            '.7z': self.extract_archive,
            '.rar': self.extract_archive,
            '.jar': self.install_jar,
            '.iso': self.mount_iso_and_install,
        }

    def run_command(self, cmd: str):
        try:
            print(f"Running: {cmd}")
            completed = subprocess.run(cmd, shell=True, check=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return completed.returncode
        except subprocess.CalledProcessError as e:
            print(f"Installation failed: {cmd}\nError: {e.stderr.decode()}")
            return e.returncode

    def install_msi(self, file_path: Path):
        cmd = f'msiexec /i "{file_path}" /qn /norestart /l*v "{file_path}.log"'
        return self.run_command(cmd)
    
    def install_msp(self, file_path: Path):
        cmd = f'msiexec /p "{file_path}" /qn /norestart /l*v "{file_path}.log"'
        return self.run_command(cmd)

    def install_exe(self, file_path: Path):
        # Always use the most silent switches possible, no UI, no prompts
        silent_switch_sets = [
            ['/S', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'], # Inno Setup, NSIS
            ['/S', '/silent', '/NORESTART'],
            ['/quiet', '/norestart'], # MSI wrappers
            ['/VERYSILENT', '/SP-', '/SUPPRESSMSGBOXES', '/NORESTART'],
            ['/s', '/v', '/qn'], # InstallShield/MSI wrapper
        ]
        is_python_installer = "python" in file_path.name.lower()

        if is_python_installer:
            cmd = f'"{file_path}" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0'
            ret = self.run_command(cmd)
            if ret == 0:
                return 0
            else:
                return -1 # Python installer failed silently
        
        # For non-Python EXE installers, try silent switches.
        # If any return 0, we still assume manual intervention might be needed
        # because some EXEs return 0 even if a UI was shown and cancelled.
        for switches in silent_switch_sets:
            cmd = f'"{file_path}" {" ".join(switches)}'
            ret = self.run_command(cmd)
            if ret == 0:
                # If a non-Python EXE returns 0, we will now assume it still might have required manual intervention
                # due to the user's feedback that Ulaa.exe returned 0 on cancellation.
                # This is a heuristic to prioritize flagging potential manual intervention.
                return 1 # Indicate manual setup needed
        
        # If all silent attempts fail (non-zero return code), return 1 to specifically indicate manual setup is required.
        return 1
    
    def install_msix(self, file_path: Path):
        cmd = f'powershell Add-AppxPackage -Path "{file_path}"'
        return self.run_command(cmd)
    
    def install_batch(self, file_path: Path):
        cmd = f'"{file_path}"'
        return self.run_command(cmd)

    def install_powershell(self, file_path: Path):
        cmd = f'powershell -ExecutionPolicy Bypass -File "{file_path}"'
        return self.run_command(cmd)

    def install_jar(self, file_path: Path):
        cmd = f'java -jar "{file_path}" /S'
        # If the /S switch is not supported by the JAR installer, manual intervention might be required.
        return self.run_command(cmd)

    def extract_archive(self, file_path: Path):
        output_dir = file_path.parent / file_path.stem
        cmd = f'7z x "{file_path}" -o"{output_dir}" -y'
        ret = self.run_command(cmd)
        if ret == 0:
            print(f"Extracted {file_path.name} to {output_dir}")
            # Recursively install any installers found in the extracted folder
            for root, dirs, files in os.walk(output_dir):
                for f in files:
                    ext = Path(f).suffix.lower()
                    installer_func = self.SILENT_COMMANDS.get(ext)
                    if installer_func:
                        installer_func(Path(root) / f)
        return ret
    
    def mount_iso_and_install(self, file_path: Path):
        print(f"ISO file detected: {file_path}. Manual intervention is required to mount the ISO and run the installer within.")
        return -1

    def segregate_and_install(self):
        for file_path in self.installers_path.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                # Skip .info.txt and .txt files
                if ext == '.txt' or file_path.name.endswith('.info.txt'):
                    continue
                installer_func = self.SILENT_COMMANDS.get(ext)
                if installer_func:
                    print(f"Installing {file_path.name}...")
                    ret = installer_func(file_path)
                    if ret == 0:
                        print(f"Installed {file_path.name} successfully.")
                    else:
                        print(f"Installation failed for {file_path.name}.")
                else:
                    print(f"No install handler configured for file: {file_path.name}")

if __name__ == "__main__":
    # Use the real path to your installers directory in the workspace
    installer = AutoInstaller("installer/installers/manual_setup")
    installer.segregate_and_install()
