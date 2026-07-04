import os
import zipfile
import subprocess
import shutil
from pathlib import Path
from state import State
from target import Target
from compilers import GNUmake
from output import Output
from download import Download
from build import BuildConfiguration


class CMake:
    """Wrapper used to invoke CMake."""

    def __init__(self, generator, config):
        self.generator = generator
        self.config = config

    def install(self, target: Target, state: State, output: Output):
        """Installs CMake.

        CMake is not easily buildable on Windows so we rely on a binary
        distribution

        Parameters
        ----------
        target: Target
            The target platform and architecture.
        state: State
            The state of the bootstrap build.
        output: Output
            The output helper.
        """
        print("")
        output.print_step_title("Installing CMake")
        if state.cmake_path == "":
            self._install(target)
            print("    CMake installed successfully")
        else:
            self.path = state.cmake_path
            print("    Using previous installation: " + self.path)
        state.set_cmake_path(self.path)
        output.next_step()

    def build(self, makefile_path: str,
              build_configuration: BuildConfiguration,
              logfile: str):
        """Generate the makefiles and then use them to build the project.

        Parameters
        ----------
        makefile_path : str
            Path to the makefile. It should be the CMakeLists.txt.
        build_configuration: BuildConfiguration
            The build configuration.
        logfile: str
            The path to the file where the output of CMake will be written.
        """
        previous_working_dir = os.getcwd()
        os.chdir(Path(makefile_path).parent)
        try:
            with open(logfile, "w") as output_file:
                cmake_path = previous_working_dir + "/" + self.path
                generation_args = [cmake_path, "-G", self.generator, "."]
                generation_args.extend(build_configuration.cmake_generation_args)
                print("    Executing " + " ".join(generation_args))
                subprocess.check_call(generation_args, stdout=output_file)
                build_args = [cmake_path, "--build", "."]
                if build_configuration.cmake_configuration:
                    build_args.extend(["--config", build_configuration.cmake_configuration])
                print("    Executing " + " ".join(build_args))
                subprocess.check_call(build_args, stdout=output_file)
        except subprocess.CalledProcessError:
            raise RuntimeError("Compilation of " + makefile_path + " failed.")
        finally:
            os.chdir(previous_working_dir)

    def _install(self, target):
        self.path = ""
        if target.platform == "Windows":
            architecture_string = ""
            if target.architecture == "64":
                architecture_string = "-win64-x64"
            else:
                architecture_string = "-win32-x86"
            source_path = "CMake/cmake-3.12.3" + architecture_string + ".zip"
            zip_ref = zipfile.ZipFile(source_path, "r")
            self.path = self.config.build_dir + "/cmake-3.12.3" + \
                        architecture_string + "/bin/cmake.exe"

            # TODO : the path we delete here doesn't seem right
            shutil.rmtree(self.path, ignore_errors=True)
            zip_ref.extractall(self.config.build_dir)
            zip_ref.close()
        elif target.platform == "Linux":
            download_url = "https://github.com/codesmithyide/CMake/archive/main.zip"
            download = Download("CMake", download_url, self.config.build_dir,
                                self.config.downloads_dir, "main")
            download.download(None)
            download.unzip()
            previous_working_dir = os.getcwd()
            os.chdir(self.config.build_dir + "/CMake")
            try:
                try:
                    subprocess.check_call(["chmod", "0774", "bootstrap"])
                except subprocess.CalledProcessError:
                    raise RuntimeError("chmod 0774 bootstrap failed.")
                try:
                    subprocess.check_call("./bootstrap")
                except subprocess.CalledProcessError:
                    raise RuntimeError("./bootstrap failed.")
                GNUmake().compile("Makefile", None, None)
                self.path = self.config.build_dir + "/CMake/bin/cmake"
            finally:
                os.chdir(previous_working_dir)
        else:
            raise RuntimeError("Unsupported platform: " + target.platform)
