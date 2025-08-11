class Parser:
    def __init__(self, file_path, config):
        self.file_path = file_path
        self.config = config

    def parse(self):
        raise NotImplementedError("Subclasses should implement this method to parse the script.")   