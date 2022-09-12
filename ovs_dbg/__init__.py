import os
import sys

if "ovs" not in sys.modules:
    parent_dir = os.path.abspath(os.path.dirname(__file__))
    vendor_dir = os.path.join(parent_dir, "vendor")
    # Insert vendor path before the standard library.
    sys.path.insert(1, vendor_dir)
    import ovs  # noqa: F401
