import os
import subprocess

class CodeSmithyMake:
    def __init__(self, architecture, config):
        self.executable = os.getcwd() + "/" + config.build_dir + \
                          "/codesmithyide/codesmithy/bin/"
        if architecture == "64":
            self.executable += "x64"
        else:
            self.executable += "Win32"
        self.executable += "/CodeSmithyMake.exe"

    def build(self, compiler, makefile_path, configuration, input):
        try:
            subprocess.check_call([self.executable, "-p", configuration, makefile_path])
        except subprocess.CalledProcessError:
            launchIDE = input.query("    Compilation failed. Do you you want to launch the IDE?", ["y", "n"], "n")
            if launchIDE == "y":
                compiler.launch(makefile_path)
            raise RuntimeError("Compilation of " + makefile_path + " failed.")
