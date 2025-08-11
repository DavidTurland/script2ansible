

import logging

from .Parser import Parser
from .PerlParser import PerlParser
from .BashParser import BashParser

class ParserFactory:
    @staticmethod
    def get_parser(file_path, config):
        # Check file extension first
        if file_path.endswith('.pl'):
            return PerlParser(file_path, config)
        elif file_path.endswith('.sh') or file_path.endswith('.bash'):
            return BashParser(file_path, config)
        # If no extension, check shebang
        try:
            with open(file_path, 'r') as f:
                first_line = f.readline()
                if first_line.startswith('#!'):
                    if 'perl' in first_line:
                        return PerlParser(file_path, config)
                    elif 'bash' in first_line or 'sh' in first_line:
                        return BashParser(file_path, config)
        except Exception as e:
            logging.warning(f"Could not read file for shebang detection: {file_path}: {e}")
        # Default to BashParser
        return BashParser(file_path, config)