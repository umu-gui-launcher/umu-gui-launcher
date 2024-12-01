#!/usr/bin/env python3

import sys
import argparse
import logging
from .app import UmuRunLauncher

def main():
    parser = argparse.ArgumentParser(description='UMU Launcher - A Wine Game Launcher')
    parser.add_argument('-v', '--verbose', action='store_true',
                      help='Enable verbose logging')
    parser.add_argument('-q', '--quiet', action='store_true',
                      help='Disable all logging except errors')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
        
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger('umu-launcher')
    logger.setLevel(log_level)
    
    # Start the application
    app = UmuRunLauncher()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
