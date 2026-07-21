from pathlib import Path
import shutil
import urllib.request
import os
import zipfile


class Download:
    def __init__(self, name, url, download_dir, branch, destination_dirs):
        self.name = name
        self.url = url
        self.branch = branch

        self.download_path = download_dir + "/"
        self.download_path += self.name + "-" + self.branch + ".zip"

        # The install location(s) are fixed at creation time rather than
        # passed to unzip(). This is what makes the self.unzipped guard
        # correct: a single download can be shared by several projects (and
        # deduplicated by Downloader.merge), and it must be installed to all
        # of its destinations exactly once. Each destination is the exact
        # directory the archive is unzipped into.
        self.destination_dirs = destination_dirs

        self.unzipped = False

    def download(self, substep):
        if substep != None:
            print("    Step 4" + substep + ": Fetching " + self.name +
                  " code from " + self.url,
                  flush=True)
        Path(self.download_path).parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(self.url, self.download_path)

    def unzip(self):
        """Extracts the downloaded package to its install location(s).

        The destination directories were fixed when the Download was created,
        so this can be safely guarded by self.unzipped even when the download
        is shared by several projects.
        """

        if not self.unzipped:
            print("    Unzipping " + self.download_path, flush=True)
            for destination_dir in self.destination_dirs:
                # The archive contains a single top-level "<name>-<branch>"
                # folder. Extract it next to the destination, then rename it
                # to the exact destination directory.
                extract_dir = os.path.dirname(destination_dir)
                temp_destination_dir = extract_dir + "/" + self.name + "-" + self.branch
                shutil.rmtree(destination_dir, ignore_errors=True)
                shutil.rmtree(temp_destination_dir, ignore_errors=True)
                Path(extract_dir).mkdir(parents=True, exist_ok=True)
                zip_ref = zipfile.ZipFile(self.download_path, "r")
                zip_ref.extractall(extract_dir)
                zip_ref.close()
                os.rename(temp_destination_dir, destination_dir)
        else:
            print("    " + self.download_path + " already unzipped",
                  flush=True)
        self.unzipped = True

    def add_destination_dirs(self, destination_dirs):
        """Adds install locations to this download, ignoring duplicates.

        A single archive can be requested by several projects with different
        install locations. It is still downloaded once, but must be installed
        to every requested destination, so the destination lists are unioned.
        """

        for destination_dir in destination_dirs:
            if destination_dir not in self.destination_dirs:
                self.destination_dirs.append(destination_dir)

    def refers_to_same_archive(self, other):
        """True if the two downloads fetch the same archive.

        The install locations (destination_dirs) are excluded on purpose: the
        same archive may be installed to several destinations, which
        Downloader.merge unions rather than treating as a difference.
        """

        return ((self.name == other.name) and (self.url == other.url) and
                (self.download_path == other.download_path))


class Downloader:
    def __init__(self):
        self.downloads = []

    def merge(self, other_downloader):
        for other_download in other_downloader.downloads:
            already_present = False
            for download in self.downloads:
                if download.url == other_download.url:
                    # Same archive requested by more than one project. It is
                    # downloaded once and installed to every requested
                    # destination, so merge the destination lists rather than
                    # treating differing destinations as a conflict. Any other
                    # difference (name or download path) means the same URL was
                    # defined inconsistently and remains an error.
                    if not download.refers_to_same_archive(other_download):
                        exception_text = "Conflicting values for " + \
                                         "download " + download.name
                        raise RuntimeError(exception_text)
                    download.add_destination_dirs(
                        other_download.destination_dirs)
                    already_present = True
                    break
            if not already_present:
                self.downloads.append(other_download)

    @staticmethod
    def _substep_label(index):
        """Returns a spreadsheet-style label: a, b, ..., z, aa, ab, ...

        Generating the download substep labels this way keeps them correct no
        matter how many downloads there are. The previous implementation zipped
        the downloads against range(ord("a"), ord("z")), which silently dropped
        every download past the 25th (they were never fetched, then failed when
        the build tried to unzip them).
        """

        label = ""
        index += 1
        while index > 0:
            index, remainder = divmod(index - 1, 26)
            label = chr(ord("a") + remainder) + label
        return label

    def download(self):
        for i, download in enumerate(self.downloads):
            download.download(self._substep_label(i))

    def unzip(self, name):
        for download in self.downloads:
            if download.name == name:
                download.unzip()
