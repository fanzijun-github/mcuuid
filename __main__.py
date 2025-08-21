import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkinter import Tk
from gui.main_gui import UUIDScannerGUI

# 添加高DPI支持
try:
    # Windows 8.1及以上版本支持 per-monitor DPI
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

# 启动 GUI
if __name__ == "__main__":
    try:
        from ttkthemes import ThemedStyle
        root = Tk()
        # 添加高DPI支持
        try:
            # Windows 8.1及以上版本支持 per-monitor DPI
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
            ScaleFactor = windll.shcore.GetScaleFactorForDevice(0)
            root.tk.call('tk', 'scaling', ScaleFactor / 75)
        except:
            pass
        # root.iconbitmap("icon.ico")
        style = ThemedStyle(root)
        style.set_theme("arc")  # 或其他主题
    except ImportError:
        # 如果没有安装 ttkthemes，则使用默认主题
        root = Tk()
        # 不设置特殊主题，使用默认的 ttk 样式
    
    app = UUIDScannerGUI(root)
    root.mainloop()