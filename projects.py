from typing import Optional
import os
import re
import subprocess
from pathlib import Path
from download import Downloader
from download import Download
from input import Input
from output import Output
from build import BuildTools, BuildConfiguration


class Project:
    """Represents a project that can be downloaded and optionally built."""

    def __init__(self,
                 name: str,
                 repository: str,
                 branch: str,
                 download_path: str,
                 install_path: str,
                 env_var_name: str,
                 makefile_path: Optional[str],
                 use_codesmithy_make: bool):
        """
        Parameters
        ----------
        name : str
            The name of the project. The location of the package to download is
            derived from the name.
        repository : str
            The name of the source repository. Combined with the branch, this
            identifies the source to download.
        branch : str
            The name of the branch to download.
        download_path : str
            The directory where downloaded packages are cached.
        install_path : str
            The directory under which the project is unzipped and built (the
            build directory).
        env_var_name : str
            The name of the environment variable that will point to the
            location of this project. The location is derived from the name.
        makefile_path : str, optional
            The path of the makefile used to build the project. The path is
            relative to the directory where the project is unzipped. None if
            the project only needs to be downloaded.
        use_codesmithy_make : bool
            Whether CodeSmithyMake should be used to build the project.
        """

        self.name = name
        self.repository = repository
        self.branch = branch
        self.download_path = download_path
        self.install_path = install_path
        self.env_var_name = env_var_name
        if makefile_path is None:
            self.makefile_path = None
        else:
            self.makefile_path = install_path + "/" + name + "/" + \
                                 makefile_path
        self.use_codesmithy_make = use_codesmithy_make
        self.cmake_generation_args = []

        split_name = name.split("/")

        # The installation directory is derived from the project name
        if len(split_name) == 1:
            self.install_dir = split_name[0]
        else:
            self.install_dir = split_name[0] + "/" + split_name[1]

        self.built = False

    def create_downloader(self) -> Downloader:
        """Creates a downloader to download the package(s) for this project.

        Returns
        -------
        Downloader
            An instance of the Downloader class that can be used to download
            the package or packages for this project.
        """

        downloader = Downloader()

        # The download URL is derived from the project name
        split_name = self.name.split("/")
        download = None
        if len(split_name) == 1:
            download_url = "https://github.com/codesmithyide/" + \
                           split_name[0] + "/archive/" + self.branch + ".zip"
            download = Download(split_name[0], download_url,
                                self.install_path,
                                self.download_path, self.branch)
        else:
            download_url = "https://github.com/codesmithyide/" + \
                           split_name[1] + "/archive/" + self.branch + ".zip"
            download = Download(split_name[1], download_url,
                                self.install_path + "/" + split_name[0],
                                self.download_path, self.branch)
        downloader.downloads.append(download)

        return downloader

    def unzip(self, downloader: Downloader):
        """Unzips the package(s) for this project.

        In the Project class there is only one package but derived classes can
        specify more than one package to unzip.

        Parameters
        ----------
        downloader : Downloader
            The downloader that was used to download the package(s).
        """

        split_name = self.name.split("/")
        if len(split_name) == 1:
            downloader.unzip(split_name[0])
        else:
            downloader.unzip(split_name[1])

    def build(self, build_tools: BuildTools,
              parent_build_configuration: BuildConfiguration,
              input: Input,
              output: Output):
        """Builds the project.

        Parameters
        ----------
        build_tools : BuildTools
            The build tools. An appropriate build tool will be selected based
            on the type of the project.
        parent_build_configuration : BuildConfiguration
            The parent build configuration. This may be further modified if the
            project has specific settings.
        input : Input
            The input helper.
        output : Output
            The output helper.
        """

        try:
            if self.makefile_path is None:
                print("    No build required for this project")
            else:
                cmake = build_tools.cmake
                compiler = build_tools.compiler
                codesmithymake = build_tools.codesmithymake
                build_configuration = BuildConfiguration(parent_build_configuration)
                build_configuration.cmake_generation_args.extend(self.cmake_generation_args)
                resolved_makefile_path = self._resolve_makefile_path(compiler, build_configuration.architecture_dir_name)
                if not os.path.exists(resolved_makefile_path):
                    raise RuntimeError(resolved_makefile_path + " not found")
                if self.use_codesmithy_make:
                    print("    Using CodeSmithyMake")
                    codesmithymake.build(compiler, resolved_makefile_path,
                                         build_configuration.codesmithymake_configuration,
                                         input)
                elif self.makefile_path.endswith("/CMakeLists.txt"):
                    log = self.name + "_build.log"
                    print("    Using CMake, build log: " + log)
                    cmake.build(resolved_makefile_path, build_configuration,
                                log)
                else:
                    print("    Using " + compiler.name)
                    compiler.compile(resolved_makefile_path,
                                     build_configuration.compiler_configuration,
                                     input)
                print("    Project build successfully")
            self.built = True
        except RuntimeError:
            print("    Failed to build project")
            raise

    def launch(self, compiler, architecture_dir_name):
        compiler.launch(self._resolve_makefile_path(compiler,
                                                    architecture_dir_name))

    def _resolve_makefile_path(self, compiler, architecture_dir_name):
        if compiler.short_name == "GNUmakefile":
            result = re.sub(r"\$\(compiler_short_name\).*",
                            compiler.short_name + "/GNUmakefile",
                            self.makefile_path)
        else:
            result = re.sub(r"\$\(compiler_short_name\)",
                            compiler.short_name,
                            self.makefile_path)
        result = re.sub(r"\$\(arch\)",
                        architecture_dir_name,
                        result)
        return result


class libgit2Project(Project):
    def __init__(self, download_path, install_path, target):
        super().__init__("libgit2", "TODO_REPOSITORY", "main", download_path, install_path, "LIBGIT2",
                         "$(arch)/CMakeLists.txt", False)
        self.target = target
        self.cmake_generation_args = ["-DBUILD_SHARED_LIBS=OFF",
                                      "-DSTATIC_CRT=OFF"]

    def unzip(self, downloader):
        if self.target.platform == "Linux":
            super().unzip(downloader)
        else:
            libgit2_dir = self.install_path + "/libgit2"
            Path(libgit2_dir).mkdir(exist_ok=True)
            downloader.unzip("libgit2",
                             [libgit2_dir + "/Win32", libgit2_dir + "/x64"])

class wxWidgetsProject(Project):
    def __init__(self, download_path, install_path):
        super().__init__("wxWidgets", "TODO_REPOSITORY", "master", download_path, install_path, "WXWIN",
                         "build/msw/wx_$(compiler_short_name).sln", False)

    def create_downloader(self):
        downloader = super().create_downloader()
        modules = ["zlib", "libpng", "libexpat", "libjpeg-turbo", "libtiff"]
        url_prefix = "https://github.com/codesmithyide/"
        url_suffix = "/archive/wx.zip"
        for module in modules:
            downloader.downloads.append(
                Download(module, url_prefix + module + url_suffix,
                         self.install_path + "/wxWidgets/src",
                         self.download_path, "wx"))
        return downloader

    def unzip(self, downloader):
        super().unzip(downloader)
        src = self.install_path + "/wxWidgets/src"
        downloader.unzip("zlib")
        downloader.unzip("libpng")
        os.rmdir(src + "/png")
        os.rename(src + "/libpng", src + "/png")
        downloader.unzip("libexpat")
        os.rmdir(src + "/expat")
        os.rename(src + "/libexpat", src + "/expat")
        downloader.unzip("libjpeg-turbo")
        os.rmdir(src + "/jpeg")
        os.rename(src + "/libjpeg-turbo", src + "/jpeg")
        downloader.unzip("libtiff")
        os.rmdir(src + "/tiff")
        os.rename(src + "/libtiff", src + "/tiff")

    def _resolve_makefile_path(self, compiler, architecture_dir_name):
        return re.sub(r"\$\(compiler_short_name\)",
                      compiler.short_name.lower(),
                      self.makefile_path)


class Test:
    def __init__(self, project_name, executable):
        self.project_name = project_name
        self.executable = executable


class Projects:
    def __init__(self, target, config):
        self.config = config
        self.downloader = Downloader()
        self.projects = []
        self.projects.append(Project(
            "pugixml",
            "TODO_REPOSITORY",
            "master",
            config.downloads_dir,
            config.build_dir,
            "PUGIXML",
            None,
            False))
        self.projects.append(libgit2Project(config.downloads_dir, config.build_dir, target))
        self._add_ishiko_project(
            "Ishiko/Platform",
            "ishiko-cpp_platform",
            "main",
            config.downloads_dir,
            config.build_dir,
            "ISHIKO_CPP",
            None,
            False)
        self._add_ishiko_project(
            "Ishiko/Errors",
            "ishiko-cpp_errors",
            "main",
            config.downloads_dir,
            config.build_dir,
            "ISHIKO_CPP",
            "Makefiles/$(compiler_short_name)/IshikoErrors.sln",
            False)
        self._add_ishiko_project(
            "Ishiko/Types",
            "ishiko-cpp_types",
            "main",
            config.downloads_dir,
            config.build_dir,
            "ISHIKO_CPP",
            "Makefiles/$(compiler_short_name)/IshikoTypes.sln",
            False)
        self._add_ishiko_project(
            "Ishiko/Process",
            "ishiko-cpp_process",
            "main",
            config.downloads_dir,
            config.build_dir,
            "ISHIKO_CPP",
            "Makefiles/$(compiler_short_name)/IshikoProcess.sln",
            False)
        self._add_ishiko_project(
            "Ishiko/Collections",
            "ishiko-cpp_collections",
            "main",
            config.downloads_dir,
            config.build_dir,
            "ISHIKO_CPP",
            "Makefiles/$(compiler_short_name)/IshikoCollections.sln",
            False)
        self._add_ishiko_project(
            "Ishiko/FileSystem",
            "ishiko-cpp_filesystem",
            "main",
            config.downloads_dir,
            config.build_dir,
            "ISHIKO_CPP",
            "Makefiles/$(compiler_short_name)/IshikoFileSystem.sln",
            False)
        self._add_ishiko_project(
            "Ishiko/Terminal",
            "ishiko-cpp_terminal",
            "main",
            config.downloads_dir,
            config.build_dir,
            "ISHIKO_CPP",
            "Makefiles/$(compiler_short_name)/IshikoTerminal.sln",
            False)
        self._add_ishiko_project(
            "Ishiko/Tasks",
            "ishiko-cpp_tasks",
            "main",
            config.downloads_dir,
            config.build_dir,
            "ISHIKO_CPP",
            "Makefiles/$(compiler_short_name)/IshikoTasks.sln",
            False)
        self._add_diplodocusdb_project(
            "DiplodocusDB/Core",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "DIPLODOCUSDB",
            "Makefiles/$(compiler_short_name)/DiplodocusDBCore.sln",
            False)
        self._add_diplodocusdb_project(
            "DiplodocusDB/TreeDB/Core",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "DIPLODOCUSDB",
            "Makefiles/$(compiler_short_name)/DiplodocusTreeDBCore.sln",
            False)
        self._add_diplodocusdb_project(
            "DiplodocusDB/TreeDB/XMLTreeDB",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "DIPLODOCUSDB",
            "Makefiles/$(compiler_short_name)/DiplodocusXMLTreeDB.sln",
            False)
        self.projects.append(Project(
            "CodeSmithyIDE/VersionControl/Git",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "CODESMITHYIDE",
            "Makefiles/$(compiler_short_name)/CodeSmithyGit.sln",
            False))
        self.projects.append(Project(
            "CodeSmithyIDE/BuildToolchains",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "CODESMITHYIDE",
            "Makefiles/$(compiler_short_name)/CodeSmithyBuildToolchains.sln",
            False))
        self.projects.append(Project(
            "CodeSmithyIDE/CodeSmithy/Core",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "CODESMITHYIDE",
            "Makefiles/$(compiler_short_name)/CodeSmithyCore.sln",
            False))
        self.projects.append(Project(
            "CodeSmithyIDE/CodeSmithy/CLI",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "CODESMITHYIDE",
            "Makefiles/$(compiler_short_name)/CodeSmithyCLI.sln",
            False))
        self._add_ishiko_project(
            "Ishiko/TestFramework/Core",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "ISHIKO_CPP",
            "Makefiles/$(compiler_short_name)/IshikoTestFrameworkCore.sln",
            True)
        self._add_ishiko_project(
            "Ishiko/WindowsRegistry",
            "ishiko-cpp_windowsregistry",
            "main",
            config.downloads_dir,
            config.build_dir,
            "ISHIKO_CPP",
            "Makefiles/$(compiler_short_name)/IshikoWindowsRegistry.sln",
            True)
        self._add_ishiko_project(
            "Ishiko/FileTypes",
            "ishiko-cpp_filetypes",
            "main",
            config.downloads_dir,
            config.build_dir,
            "ISHIKO_CPP",
            "Makefiles/$(compiler_short_name)/IshikoFileTypes.sln",
            True)
        self.projects.append(Project(
            "CodeSmithyIDE/CodeSmithy/UICore",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "CODESMITHYIDE",
            "Makefiles/$(compiler_short_name)/CodeSmithyUICore.sln",
            True))
        self.projects.append(wxWidgetsProject(config.downloads_dir, config.build_dir))
        self.projects.append(Project(
            "CodeSmithyIDE/CodeSmithy/UIElements",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "CODESMITHYIDE",
            "Makefiles/$(compiler_short_name)/CodeSmithyUIElements.sln",
            True))
        self.projects.append(Project(
            "CodeSmithyIDE/CodeSmithy/UIImplementation",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "CODESMITHYIDE",
            "Makefiles/$(compiler_short_name)/CodeSmithyUIImplementation.sln",
            True))
        self.projects.append(Project(
            "CodeSmithyIDE/CodeSmithy/UI",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "CODESMITHYIDE",
            "Makefiles/$(compiler_short_name)/CodeSmithy.sln",
            True))
        self.projects.append(Project(
            "CodeSmithyIDE/CodeSmithy/Tests/Core",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "CODESMITHYIDE",
            "Makefiles/$(compiler_short_name)/CodeSmithyCoreTests.sln",
            True))
        self.projects.append(Project(
            "CodeSmithyIDE/CodeSmithy/Tests/Make",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "CODESMITHYIDE",
            "Makefiles/$(compiler_short_name)/CodeSmithyMakeTests.sln",
            True))
        self.projects.append(Project(
            "CodeSmithyIDE/CodeSmithy/Tests/UICore",
            "TODO_REPOSITORY",
            "main",
            config.downloads_dir,
            config.build_dir,
            "CODESMITHYIDE",
            "Makefiles/$(compiler_short_name)/CodeSmithyUICoreTests.sln",
            True))
        self.tests = []
        self.tests.append(Test("CodeSmithyIDE/CodeSmithy/Tests/Core",
                               "CodeSmithyCoreTests.exe"))
        self._init_downloader()

    def get(self, name):
        for project in self.projects:
            if project.name == name:
                return project
        return None

    def set_environment_variables(self, output):
        print("")
        output.print_step_title("Setting environment variables")
        env = {}
        for project in self.projects:
            value = os.getcwd() + "/" + self.config.build_dir + "/" + \
                    project.name.split("/")[0]
            if project.env_var_name in env:
                old_value = env[project.env_var_name]
                if (old_value != value):
                    exception_text = "Conflicting values for " + \
                        "environment variable " + project.env_var_name + " (" + \
                        value + " vs " + old_value + ")"
                    raise RuntimeError(exception_text)
            else:
                env[project.env_var_name] = value
        for var_name in env:
            print("    " + var_name + ": " + env[var_name])
            os.environ[var_name] = env[var_name]
        output.next_step()

    def download(self):
        self.downloader.download()

    def build(self, build_tools, build_configuration,
              input, state, output):
        # For now only bypass pugixml, libgit2 and wxWidgets because they
        # are independent from the rest. More complex logic is required to
        # handle the other projects.
        # Unless we have built all project succesfully.
        for project in self.projects:
            if state.build_complete:
                project.built = True
            elif project.name in ["libgit2", "pugixml", "wxWidgets"]:
                if project.name in state.built_projects:
                    project.built = True
        for project in self.projects:
            print("")
            output.print_step_title("Building " + project.name)
            if project.built:
                print("    Using previous execution")
            else:
                project.unzip(self.downloader)
                project.build(build_tools, build_configuration,
                              input, output)
            state.set_built_project(project.name)
            output.next_step()
        state.set_build_complete()

    def test(self, compiler, architecture_dir_name, input):
        for test in self.tests:
            # TODO
            executable_path = self.config.build_dir + "/" + test.project_name + \
                              "/Makefiles/vc15/x64/Debug/" + test.executable
            try:
                subprocess.check_call([executable_path])
            except subprocess.CalledProcessError:
                launchIDE = input.query("    Tests failed. Do you you want to"
                                        " launch the IDE?", ["y", "n"], "n")
                if launchIDE == "y":
                    self.get(test.project_name).launch(compiler,
                                                       architecture_dir_name)
                raise RuntimeError(test.project_name + " tests failed.")

    def _add_ishiko_project(self,
                            name: str,
                            repository: str,
                            branch: str,
                            download_path: str,
                            install_path: str,
                            env_var_name: str,
                            makefile_path: Optional[str],
                            use_codesmithy_make: bool):
        self.projects.append(Project(name, repository, branch, download_path,
                                     install_path, env_var_name, makefile_path,
                                     use_codesmithy_make))

    def _add_diplodocusdb_project(self,
                                  name: str,
                                  repository: str,
                                  branch: str,
                                  download_path: str,
                                  install_path: str,
                                  env_var_name: str,
                                  makefile_path: Optional[str],
                                  use_codesmithy_make: bool):
        self.projects.append(Project(name, repository, branch, download_path,
                                     install_path, env_var_name, makefile_path,
                                     use_codesmithy_make))

    def _init_downloader(self):
        for project in self.projects:
            project_downloader = project.create_downloader()
            self.downloader.merge(project_downloader)
