"""نقطة تشغيل البرنامج: ‎python main.py [--scan | --deep-scan]‎"""

import sys

from pcdoctor.gui import main

if __name__ == "__main__":
    mode = "deep" if "--deep-scan" in sys.argv else "quick" if "--scan" in sys.argv else None
    main(mode)
