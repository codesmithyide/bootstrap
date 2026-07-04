class Config:
    """Configuration for the bootstrap build.

    Centralizes settings such as the directory layout so that they are defined
    in one place (in main) and injected into the components that need them,
    rather than being hardcoded throughout the code.
    """

    def __init__(self, build_dir="build", downloads_dir="downloads"):
        self.build_dir = build_dir
        self.downloads_dir = downloads_dir
