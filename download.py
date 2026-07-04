from pathlib import Path
import shutil
import urllib.request
import os
import zipfile


class Download:
    def __init__(self, name, url, extract_path, download_dir, branch="main"):
        self.name = name
        self.url = url
        self.branch = branch

        self.download_path = download_dir + "/"
        self.download_path += self.name + "-" + self.branch + ".zip"

        self.extract_path_prefix = extract_path + "/"

        self.unzipped = False

    def download(self, substep):
        if substep != None:
            print("    Step 4" + substep + ": Fetching " + self.name +
                  " code from " + self.url,
                  flush=True)
        Path(self.download_path).parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(self.url, self.download_path)

    def unzip(self, destination_dirs=None):
        """Creates a downloader to download the package(s) for this project.

        Parameters
        ----------
        destination_dirs
            A list of directories where the package should be unzipped.
        """

        if not self.unzipped:
            print("    Unzipping " + self.download_path, flush=True)
            if destination_dirs is None:
                destination_dirs = [self.extract_path_prefix + self.name]
            for destination_dir in destination_dirs:
                temp_destination_dir = self.extract_path_prefix + self.name + "-" + self.branch
                shutil.rmtree(destination_dir, ignore_errors=True)
                shutil.rmtree(temp_destination_dir, ignore_errors=True)
                zip_ref = zipfile.ZipFile(self.download_path, "r")
                zip_ref.extractall(self.extract_path_prefix)
                zip_ref.close()
                os.rename(temp_destination_dir, destination_dir)
        else:
            print("    " + self.download_path + " already unzipped",
                  flush=True)
        self.unzipped = True

    def __eq__(self, other):
        if not isinstance(other, Download):
            return False
        return ((self.name == other.name) and (self.url == other.url) and
                (self.download_path == other.download_path) and
                (self.extract_path_prefix == other.extract_path_prefix) and
                (self.unzipped == other.unzipped))


class Downloader:
    def __init__(self):
        self.downloads = []

    def merge(self, other_downloader):
        for other_download in other_downloader.downloads:
            already_present = False
            for download in self.downloads:
                if download.url == other_download.url:
                    if download != other_download:
                        exception_text = "Conflicting values for " + \
                                         "download " + download.name
                        raise RuntimeError(exception_text)
                    already_present = True
                    break
            if not already_present:
                self.downloads.append(other_download)

    def download(self):
        for download, i in zip(self.downloads, range(ord("a"), ord("z"))):
            download.download(chr(i))

    def unzip(self, name, destination_dirs=None):
        for download in self.downloads:
            if download.name == name:
                download.unzip(destination_dirs)
