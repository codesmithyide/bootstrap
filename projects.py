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
                 env_var_value: str,
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
        self.env_var_value = env_var_value
        if makefile_path is None:
            self.makefile_path = None
        else:
            self.makefile_path = self.install_path + "/" + makefile_path
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
                           self.repository + "/archive/" + self.branch + ".zip"
            download = Download(self.repository, download_url, "build", self.branch)
        else:
            download_url = "https://github.com/codesmithyide/" + \
                           self.repository + "/archive/" + self.branch + ".zip"
            download = Download(self.repository, download_url,
                                "build/" + split_name[0], self.branch)
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

        Path(self.install_path).parent.mkdir(parents=True, exist_ok=True)
        downloader.unzip(self.repository, [self.install_path])

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
    def __init__(self, target):
        super().__init__("libgit2", "libgit2_libgit2", "main", "build/libgit2", "LIBGIT2", "libgit2", "$(arch)/CMakeLists.txt", False)
        self.target = target
        self.cmake_generation_args = ["-DBUILD_SHARED_LIBS=OFF",
                                      "-DSTATIC_CRT=OFF"]

    def unzip(self, downloader):
        if self.target.platform == "Linux":
            super().unzip(downloader)
        else:
            Path("build/libgit2").mkdir(exist_ok=True)
            downloader.unzip("libgit2",
                             ["build/libgit2/Win32", "build/libgit2/x64"])

class wxWidgetsProject(Project):
    def __init__(self):
        super().__init__("wxWidgets", "wxWidgets", "master", "wxWidgets", "WXWIN", "",
                         "build/msw/wx_$(compiler_short_name).sln", False)

    def create_downloader(self):
        downloader = super().create_downloader()
        modules = ["zlib", "libpng", "libexpat", "libjpeg-turbo", "libtiff"]
        url_prefix = "https://github.com/CodeSmithyIDE/"
        url_suffix = "/archive/wx.zip"
        for module in modules:
            downloader.downloads.append(
                Download(module, url_prefix + module + url_suffix,
                         "build/wxWidgets/src", "wx"))
        return downloader

    def unzip(self, downloader):
        super().unzip(downloader)
        downloader.unzip("zlib")
        downloader.unzip("libpng")
        os.rmdir("build/wxWidgets/src/png")
        os.rename("build/wxWidgets/src/libpng", "build/wxWidgets/src/png")
        downloader.unzip("libexpat")
        os.rmdir("build/wxWidgets/src/expat")
        os.rename("build/wxWidgets/src/libexpat", "build/wxWidgets/src/expat")
        downloader.unzip("libjpeg-turbo")
        os.rmdir("build/wxWidgets/src/jpeg")
        os.rename("build/wxWidgets/src/libjpeg-turbo",
                  "build/wxWidgets/src/jpeg")
        downloader.unzip("libtiff")
        os.rmdir("build/wxWidgets/src/tiff")
        os.rename("build/wxWidgets/src/libtiff", "build/wxWidgets/src/tiff")

    def _resolve_makefile_path(self, compiler, architecture_dir_name):
        return re.sub(r"\$\(compiler_short_name\)",
                      compiler.short_name.lower(),
                      self.makefile_path)


class Test:
    def __init__(self, project_name, executable):
        self.project_name = project_name
        self.executable = executable


class Projects:
    def __init__(self, target):
        self.downloader = Downloader()
        self.projects = []
        self.projects.append(Project(
            "pugixml",
            "ishiko-cpp_pugixml",
            "master",
            "build/ishiko/cpp/pugixml",
            "PUGIXML",
            "",
            None,
            False))
        self.projects.append(libgit2Project(target))
        self._add_ishiko_project(
            "Ishiko/BasePlatform",
            "ishiko-cpp_base-platform",
            "main",
            "build/ishiko/cpp/platform",
            "ISHIKO_CPP",
            "ishiko/cpp",
            None,
            False)
        self._add_ishiko_project(
            "Ishiko/Errors",
            "ishiko-cpp-errors",
            "main",
            "build/ishiko/cpp/errors",
            "ISHIKO_CPP",
            "ishiko/cpp",
            "build/$(compiler_short_name)/IshikoErrors.sln",
            False))
        self._add_ishiko_project(
            "Ishiko/Types",
            "ishiko-cpp-types",
            "main",
            "build/ishiko/cpp/types",
            "ISHIKO_CPP",
            "ishiko/cpp",
            "build/$(compiler_short_name)/IshikoTypes.sln",
            False))
        self._add_ishiko_project(
            "Ishiko/Collections",
            "ishiko-cpp-collections",
            "main",
            "build/ishiko/cpp/collections",
            "ISHIKO_CPP",
            "ishiko/cpp",
            "build/$(compiler_short_name)/IshikoCollections.sln",
            False))
        self._add_ishiko_project(
            "Ishiko/Text",
            "ishiko-cpp-text",
            "main",
            "build/ishiko/cpp/text",
            "ISHIKO_CPP",
            "ishiko/cpp",
            "build/$(compiler_short_name)/IshikoText.sln",
            False))
        self._add_ishiko_project(
            "Ishiko/Process",
            "ishiko-cpp-process",
            "main",
            "build/ishiko/cpp/process",
            "ISHIKO_CPP",
            "ishiko/cpp",
            "build/$(compiler_short_name)/IshikoProcess.sln",
            False))
        self._add_ishiko_project(
            "Ishiko/FileSystem",
            "ishiko-cpp-filesystem",
            "main",
            "build/ishiko/cpp/filesystem",
            "ISHIKO_CPP",
            "ishiko/cpp",
            "build/$(compiler_short_name)/IshikoFileSystem.sln",
            False))
        self._add_ishiko_project(
            "Ishiko/Terminal",
            "ishiko-cpp-terminal",
            "main",
            "build/ishiko/cpp/terminal",
            "ISHIKO_CPP",
            "ishiko/cpp",
            "build/$(compiler_short_name)/IshikoTerminal.sln",
            False))
        self._add_ishiko_project(
            "Ishiko/Workflows",
            "ishiko-cpp_workflows",
            "main",
            "build/ishiko/cpp/tasks",
            "ISHIKO_CPP",
            "ishiko/cpp",
            "build/$(compiler_short_name)/IshikoTasks.sln",
            False))
        self._add_diplodocusdb_project(
            "DiplodocusDB/Core",
            "diplodocusdb-core",
            "main",
            "build/diplodocusdb/core",
            "DIPLODOCUSDB",
            "diplodocusdb",
            "build/$(compiler_short_name)/DiplodocusDBCore.sln",
            False))
        self._add_diplodocusdb_project(
            "DiplodocusDB/TreeDB/Core",
            "diplodocusdb-tree-db",
            "main",
            "build/diplodocusdb/tree-db",
            "DIPLODOCUSDB",
            "diplodocusdb",
            "core/build/$(compiler_short_name)/DiplodocusTreeDBCore.sln",
            False))
        self._add_diplodocusdb_project(
            "DiplodocusDB/TreeDB/XMLTreeDB",
            "diplodocusdb-tree-db",
            "main",
            "build/diplodocusdb/tree-db",
            "DIPLODOCUSDB",
            "diplodocusdb",
            "xml-tree-db/build/$(compiler_short_name)/DiplodocusXMLTreeDB.sln",
            False))
        self._add_codesmithyide_project(
            "CodeSmithyIDE/VersionControl/Git",
            "version-control",
            "main",
            "build/codesmithyide/version-control",
            "CODESMITHYIDE",
            "codesmithyide",
            "git/build/$(compiler_short_name)/CodeSmithyGit.sln",
            False))
        self._add_codesmithyide_project(
            "CodeSmithyIDE/BuildToolchains",
            "build-toolchains",
            "main",
            "build/codesmithyide/build-toolchains",
            "CODESMITHYIDE",
            "codesmithyide",
            "build/$(compiler_short_name)/CodeSmithyBuildToolchains.sln",
            False))
        self._add_codesmithyide_project(
            "CodeSmithyIDE/CodeSmithy/Core",
            "codesmithy",
            "main",
            "build/codesmithyide/codesmithy",
            "CODESMITHYIDE",
            "codesmithyide",
            "core/build/$(compiler_short_name)/CodeSmithyCore.sln",
            False))
        self._add_codesmithyide_project(
            "CodeSmithyIDE/CodeSmithy/CLI",
            "codesmithy",
            "main",
            "build/codesmithyide/codesmithy",
            "CODESMITHYIDE",
            "codesmithyide",
            "cli/build/$(compiler_short_name)/CodeSmithyCLI.sln",
            False))
        self._add_codesmithyide_project(
            "Ishiko/Tests/Core",
            "ishiko-cpp-tests",
            "main",
            "build/ishiko/cpp/tests",
            "ISHIKO_CPP",
            "ishiko/cpp",
            "core/build/$(compiler_short_name)/IshikoTestsCore.sln",
            True))
        self._add_ishiko_project(
            "Ishiko/WindowsRegistry",
            "ishiko-cpp-windows-registry",
            "main",
            "build/ishiko/cpp/windows-registry",
            "ISHIKO_CPP",
            "ishiko/cpp",
            "build/$(compiler_short_name)/IshikoWindowsRegistry.sln",
            True))
        self._add_ishiko_project(
            "Ishiko/FileTypes",
            "ishiko-cpp-file-types",
            "main",
            "build/ishiko/cpp/file-types",
            "ISHIKO_CPP",
            "ishiko/cpp",
            "build/$(compiler_short_name)/IshikoFileTypes.sln",
            True))
        self._add_codesmithyide_project(
            "CodeSmithyIDE/CodeSmithy/UICore",
            "codesmithy",
            "main",
            "build/codesmithyide/codesmithy",
            "CODESMITHYIDE",
            "codesmithyide",
            "Makefiles/$(compiler_short_name)/CodeSmithyUICore.sln",
            True))
        self.projects.append(wxWidgetsProject())
        self._add_codesmithyide_project(
            "CodeSmithyIDE/CodeSmithy/UIElements",
            "codesmithy",
            "main",
            "build/codesmithyide/codesmithy",
            "CODESMITHYIDE",
            "codesmithyide",
            "Makefiles/$(compiler_short_name)/CodeSmithyUIElements.sln",
            True)
        self._add_codesmithyide_project(
            "CodeSmithyIDE/CodeSmithy/UIImplementation",
            "codesmithy",
            "main",
            "build/codesmithyide/codesmithy",
            "CODESMITHYIDE",
            "codesmithyide",
            "Makefiles/$(compiler_short_name)/CodeSmithyUIImplementation.sln",
            True)
        self._add_codesmithyide_project(
            "CodeSmithyIDE/CodeSmithy/UI",
            "codesmithy",
            "main",
            "build/codesmithyide/codesmithy",
            "CODESMITHYIDE",
            "codesmithyide",
            "Makefiles/$(compiler_short_name)/CodeSmithy.sln",
            True)
        self._add_codesmithyide_project(
            "CodeSmithyIDE/CodeSmithy/Tests/Core",
            "codesmithy",
            "main",
            "build/codesmithyide/codesmithy",
            "CODESMITHYIDE",
            "codesmithyide",
            "Makefiles/$(compiler_short_name)/CodeSmithyCoreTests.sln",
            True)
        self._add_codesmithyide_project(
            "CodeSmithyIDE/CodeSmithy/Tests/Make",
            "codesmithy",
            "main",
            "build/codesmithyide/codesmithy",
            "CODESMITHYIDE",
            "codesmithyide",
            "Makefiles/$(compiler_short_name)/CodeSmithyMakeTests.sln",
            True)
        self._add_codesmithyide_project(
            "CodeSmithyIDE/CodeSmithy/Tests/UICore",
            "codesmithy",
            "main",
            "build/codesmithyide/codesmithy",
            "CODESMITHYIDE",
            "codesmithyide",
            "Makefiles/$(compiler_short_name)/CodeSmithyUICoreTests.sln",
            True)
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
            value = None
            if project.env_var_value is None:
                value = os.getcwd() + "/build/" + project.name.split("/")[0]
            else:
                value = os.getcwd() + "/build/" + project.env_var_value
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
            executable_path = "build/" + test.project_name + \
                              "/Makefiles/VC15/x64/Debug/" + test.executable
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

    def _add_codesmithyide_project(self,
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
