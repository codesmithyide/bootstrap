import platform
import sys
import os.path
import subprocess
import zipfile
import urllib.request
import shutil
from pathlib import Path

print("\nCodeSmithy bootstrap build")
print("--------------------------\n")

platformName = platform.system()
is64bit = False
if platform.machine() == "AMD64":
    is64bit = True
    
print("Platform: " + platformName)
if is64bit:
    print("Architecture: 64 bit")
else:
    print("Architecture: 32 bit")
print("")

shutil.rmtree("Downloads", ignore_errors=True)
shutil.rmtree("Build", ignore_errors=True)

Path("Downloads").mkdir(exist_ok=True)
Path("Build").mkdir(exist_ok=True)

def downloadAndUnzip(substep, name, url):
    print("Step 1" + substep + ": Fetching " + name + " code from " + url, flush=True)
    urllib.request.urlretrieve(url, "Downloads/" + name + "-master.zip")
    print("Step 1" + substep + ": Unzipping " + name + "-master.zip\n", flush=True)
    zip_ref = zipfile.ZipFile("Downloads/" + name + "-master.zip", "r")
    zip_ref.extractall("Build")
    zip_ref.close()
    os.rename("Build/" + name + "-master", "Build/" + name)
    return

downloadAndUnzip("a", "Errors", "https://github.com/CodeSmithyIDE/Errors/archive/master.zip")
downloadAndUnzip("b", "Process", "https://github.com/CodeSmithyIDE/Process/archive/master.zip")
downloadAndUnzip("c", "WindowsRegistry", "https://github.com/CodeSmithyIDE/WindowsRegistry/archive/master.zip")
downloadAndUnzip("d", "FileTypes", "https://github.com/CodeSmithyIDE/FileTypes/archive/master.zip")
downloadAndUnzip("e", "TestFramework", "https://github.com/CodeSmithyIDE/TestFramework/archive/master.zip")
downloadAndUnzip("f", "libgit2", "https://github.com/CodeSmithyIDE/libgit2/archive/master.zip")
downloadAndUnzip("g", "wxWidgets", "https://github.com/CodeSmithyIDE/wxWidgets/archive/master.zip")
downloadAndUnzip("h", "CodeSmithy", "https://github.com/CodeSmithyIDE/CodeSmithy/archive/master.zip")

print("Step 2: Finding compilers")
compilers = []
compilerPaths = []
foundMSVC14 = os.path.isfile("C:/Program Files (x86)/Microsoft Visual Studio 14.0/Common7/IDE/devenv.exe")
if foundMSVC14:
    compilers.append("Visual Studio 2015")
    compilerPaths.append("C:/Program Files (x86)/Microsoft Visual Studio 14.0/Common7/IDE/devenv.exe")

print("The following compilers have been found")
for i, c in enumerate(compilers):
    print(str(i+1) + ") " + c)

if len(compilers) == 0:
    print("No suitable compilers found, exiting")
    sys.exit(-1);

selectedCompiler = (int(input("Select the compiler to use: ")) - 1)
print("")

# CMake is not easily buildable on Windows so we rely on a binary distribution
print("Step 3: Installing CMake\n", flush=True)
cmakePath = ""
if platformName == "Windows":
    if is64bit:
        zip_ref = zipfile.ZipFile("CMake/cmake-3.6.1-win64-x64.zip", "r")
        cmakePath = "cmake-3.6.1-win64-x64/bin/cmake.exe"
    else:
        zip_ref = zipfile.ZipFile("CMake/cmake-3.6.1-win32-x86.zip", "r")
        cmakePath = "cmake-3.6.1-win32-x86/bin/cmake.exe"
    zip_ref.extractall(".")
    zip_ref.close()

print("Step 4: Building libgit2", flush=True)
os.chdir("Build/libgit2")
rc = subprocess.call(["../../" + cmakePath, "."])
rc = subprocess.call(["../../" + cmakePath, "--build", "."])
if rc == 0:
    print("libgit2 build successfully")
else:
    print("Failed to build libgit2, exiting")
    sys.exit(-1)
os.chdir("../..")
print("")

os.environ["ISHIKO"] = os.getcwd() + "/Build"

print("Step 5: Building Process", flush=True)
processMakefilePath = ""
if compilers[selectedCompiler] == "Visual Studio 2015":
    processMakefilePath = "Build/Process/Makefiles/VC14/IshikoProcess.sln"
rc = subprocess.call([compilerPaths[selectedCompiler], processMakefilePath, "/build", "Debug"])
if rc == 0:
    print("Process built successfully")
else:
    print("Failed to build Process, exiting")
    sys.exit(-1)
print("")

print("Step 6: Building CodeSmithyCore", flush=True)
codeSmithyCoreMakefilePath = ""
if compilers[selectedCompiler] == "Visual Studio 2015":
    codeSmithyCoreMakefilePath = "Build/CodeSmithy/Core/Makefiles/VC14/CodeSmithyCore.sln"
rc = subprocess.call([compilerPaths[selectedCompiler], codeSmithyCoreMakefilePath, "/build", "Debug"])
if rc == 0:
    print("CodeSmithyCore built successfully")
else:
    print("Failed to build CodeSmithyCore, exiting")
    sys.exit(-1)
print("")

print("Step 7: Building CodeSmithyMake", flush=True)
codeSmithyMakeMakefilePath = ""
codeSmithyMakePath = ""
if compilers[selectedCompiler] == "Visual Studio 2015":
    codeSmithyMakeMakefilePath = "Build/CodeSmithy/Make/Makefiles/VC14/CodeSmithyMake.sln"
    codeSmithyMakePath = "Build/CodeSmithy/Bin/Win32/CodeSmithyMake.exe"
rc = subprocess.call([compilerPaths[selectedCompiler], codeSmithyMakeMakefilePath, "/build", "Debug"])
if rc == 0:
    print("CodeSmithyMake built successfully")
else:
    print("Failed to build CodeSmithyMake, exiting")
    sys.exit(-1)
print("")

print("Step 8: Build Errors", flush=True)
rc = subprocess.call([codeSmithyMakePath, "Build/Errors/Makefiles/VC14/IshikoErrors.sln"])
if rc == 0:
    print("Errors built successfully")
else:
    print("Failed to build Errors, exiting")
    sys.exit(-1)
print("")

print("Step 9: Build TestFrameworkCore", flush=True)
rc = subprocess.call([codeSmithyMakePath, "Build/TestFramework/Core/Makefiles/VC14/IshikoTestFrameworkCore.sln"])
if rc == 0:
    print("TestFrameworkCore built successfully")
else:
    print("Failed to build TestFrameworkCore, exiting")
    sys.exit(-1)
print("")

print("Step 10: Build WindowsRegistry", flush=True)
rc = subprocess.call([codeSmithyMakePath, "Build/WindowsRegistry/Makefiles/VC14/IshikoWindowsRegistry.sln"])
if rc == 0:
    print("WindowsRegistry built successfully")
else:
    print("Failed to build WindowsRegistry, exiting")
    sys.exit(-1)
print("")

print("Step 11: Build FileTypes", flush=True)
rc = subprocess.call([codeSmithyMakePath, "Build/FileTypes/Makefiles/VC14/IshikoFileTypes.sln"])
if rc == 0:
    print("FileTypes built successfully")
else:
    print("Failed to build FileTypes, exiting")
    sys.exit(-1)
print("")

print("Step 12: Build CodeSmithy", flush=True)
rc = subprocess.call([codeSmithyMakePath, "Build/CodeSmithy/UI/Makefiles/VC14/CodeSmithy.sln"])
if rc == 0:
    print("CodeSmithy built successfully")
else:
    print("Failed to build CodeSmithy, exiting")
    sys.exit(-1)
print("")

print("Step 13: Build CodeSmithyCore tests", flush=True)
rc = subprocess.call([codeSmithyMakePath, "Build/CodeSmithy/Tests/Core/Makefiles/VC14/CodeSmithyCoreTests.sln"])
if rc == 0:
    print("CodeSmithyCoreTests built successfully")
else:
    print("Failed to build CodeSmithyCoreTests, exiting")
    sys.exit(-1)
print("")

print("Step 14: Build CodeSmithyMake tests", flush=True)
rc = subprocess.call([codeSmithyMakePath, "Build/CodeSmithy/Tests/Make/Makefiles/VC14/CodeSmithyMakeTests.sln"])
if rc == 0:
    print("CodeSmithyMakeTests built successfully")
else:
    print("Failed to build CodeSmithyMakeTests, exiting")
    sys.exit(-1)
print("")
