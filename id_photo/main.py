"""نقطة تشغيل البرنامج: ‎python main.py [صورة]‎"""

import sys

from idphoto.gui import main

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
