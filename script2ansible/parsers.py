import logging

from .PerlParser import PerlParser

# from .BashParser import BashParser
from .BashLexParser import BashLexParser as BashParser


class ParserFactory:
    @staticmethod
    def get_parser(file_path=None, script_string=None, config=None):
        first_line = ""
        if file_path:
            # Check file extension first
            if file_path.endswith(".pl"):
                return PerlParser(file_path=file_path, config=config)
            elif file_path.endswith(".sh") or file_path.endswith(".bash"):
                return BashParser(file_path=file_path, config=config)
            try:
                with open(file_path, "r") as f:
                    first_line = f.readline()
            except Exception as e:
                logging.warning(
                    f"Could not read file for shebang detection: {file_path}: {e}"
                )
        else:
            first_line = script_string.split("\n", 1)[0]

        if first_line.startswith("#!"):
            if "perl" in first_line:
                return PerlParser(file_path=file_path, config=config)
            elif "bash" in first_line or "sh" in first_line:
                return BashParser(file_path=file_path, config=config)

        # Default to BashParser
        return BashParser(file_path=file_path, config=config)
