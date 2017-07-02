# coding=utf-8
# Author: Gabriel Bertacco <niteckbj@gmail.com>
#
# This file was developed as a 3rd party provider for SickRage.
# It is not part of SickRage's oficial repository.
#
# SickRage is free software: distributed under the terms of the
# GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import re
import shutil
import logging

def main(SICKRAGE_PATH):
    logger = logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    logger = logging.getLogger('install_bj_provider')
    
    if not SICKRAGE_PATH:
        logger.info("No SickRage Path informed.")
        sys.exit(1)
    
    SICKRAGE_PATH = os.path.abspath(SICKRAGE_PATH)
    
    logger.debug("SickRage Path: {}".format(SICKRAGE_PATH))
    
    PROVIDERS_PATH = os.path.join(SICKRAGE_PATH,"sickbeard/providers")
    logger.debug("Providers Path: {}".format(PROVIDERS_PATH))
    
    IMG_PATH = os.path.join(SICKRAGE_PATH, "gui/slick/images/providers")
    logger.debug("Image Path: {}".format(IMG_PATH))

    if os.path.exists(PROVIDERS_PATH):
        if os.path.exists(os.path.join(PROVIDERS_PATH, "bjshare.py")):
            logger.info("An old version of bjshare.py was found. It will be replaced.")
            os.remove(os.path.join(PROVIDERS_PATH, "bjshare.py"))

        try:
            shutil.copy("bjshare.py", PROVIDERS_PATH)
            logger.info("Ok! bjshare.py was copied.")
        except Exception as e:
            logger.error("Failed to copy bjshare.py. {}".format(e))
            sys.exit(1)

        if not os.path.exists(os.path.join(PROVIDERS_PATH, "__init__.py")):
            logger.error("__init__.py was not found in providers' folder.")
            sys.exit(1)
            
        with open(os.path.join(PROVIDERS_PATH, "__init__.py"), "r+") as f:
            file_text = f.read()

            if not re.search("from sickbeard.providers import bjshare,", file_text):
                file_text = re.sub("from sickbeard.providers import", "from sickbeard.providers import bjshare,", file_text)
            if not re.search("__all__ = \[\n    'bjshare', ", file_text):
                file_text = re.sub("__all__ = \[\n    ", "__all__ = [\n    'bjshare', ",file_text)

            f.seek(0)
            f.write(file_text)
            f.truncate()
            logger.info("{}/__init__.py was successfully modified".format(PROVIDERS_PATH))

    if os.path.exists(IMG_PATH):
        if os.path.exists(os.path.join(IMG_PATH, "bj_share.png")):
            logger.info("An old version of bj_share.png was found. It will be replaced")
            os.remove(os.path.join(IMG_PATH, "bj_share.png"))
        
        try:
            shutil.copy("bj_share.png", IMG_PATH)
            logger.info("bj_share.png was copied.")
        except Exception as e:
            logger.error("Failed to copy bjshare.py. {}".format(e))
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("usage:\n python install.py sickrage_absolute_path\n")
        sys.exit(1)
    
    main(sys.argv[1])
