import os
import json
import uuid
from tkinter import messagebox, Toplevel, StringVar, Label, Radiobutton, Button, W, END
# 修复相对导入问题
import sys
import os as os2
sys.path.append(os2.path.dirname(os2.path.dirname(os2.path.abspath(__file__))))
from core.utils import query_mojang_api, load_cache, save_cache, has_playerdata

# 全局变量用于存储当前选择的世界路径
current_world_path = None


# 弹出窗口让用户选择世界
def simple_choice_window(parent, title, prompt, choices):
    win = Toplevel(parent)
    win.title(title)
    # 设置最小尺寸并更新，然后再添加控件，确保正确计算尺寸
    win.minsize(400, 100)  # 设置一个基础最小尺寸

    Label(win, text=prompt).pack(pady=5)

    var = StringVar()
    first = True
    for choice in choices:
        rb = Radiobutton(win, text=os.path.basename(choice), variable=var, value=choice)
        rb.pack(anchor=W)
        if first:
            rb.invoke()  # 选中第一个选项
            first = False

    result = []

    def on_ok():
        result.append(var.get())
        win.destroy()

    Button(win, text="确定", command=on_ok).pack(pady=10)
    
    # # 让窗口根据内容调整大小
    # win.update_idletasks()  # 先更新窗口以计算所需大小
    # # 根据内容调整窗口大小
    # width = max(win.winfo_reqwidth(), 400)   # 最小宽度400
    # height = win.winfo_reqheight()           # 高度根据内容确定
    # win.geometry(f"{width}x{height}")
    # win.minsize(width, height)
    
    win.grab_set()
    parent.wait_window(win)
    return result[0] if result else None


# 处理服务器模式
def handle_server_mode(root_dir, cache):
    usercache_path = os.path.join(root_dir, "usercache.json")
    world_folder = os.path.join(root_dir, "world")

    if not os.path.isfile(usercache_path):
        return []

    with open(usercache_path, 'r', encoding='utf-8') as f:
        usercache = json.load(f)

    results = []
    for entry in usercache:
        name = entry['name']
        uuid_str = entry['uuid'].replace('-', '')
        exists_on_mojang, real_name = query_mojang_api(uuid_str, cache)
        has_data = has_playerdata(world_folder, uuid_str)

        status = "✅ 正版" if exists_on_mojang == "valid" else \
                 "⚠️ 离线" if exists_on_mojang == "offline" else "❓ 未知"
        data_status = "有存档" if has_data else "无存档"

        results.append((name, uuid_str, status, data_status))

    return results


# 处理客户端模式
def handle_client_mode(root_dir, cache):
    saves_folder = os.path.join(root_dir, "saves")
    if not os.path.isdir(saves_folder):
        return []

    results = []
    worlds = [d for d in os.listdir(saves_folder) if os.path.isdir(os.path.join(saves_folder, d))]
    for world in worlds:
        world_path = os.path.join(saves_folder, world)
        playerdata_path = os.path.join(world_path, "playerdata")
        if not os.path.isdir(playerdata_path):
            continue

        for file in os.listdir(playerdata_path):
            if file.endswith(".dat"):
                uuid_str = file[:-4]
                try:
                    parsed_uuid = uuid.UUID(uuid_str).hex
                except ValueError:
                    continue

                exists_on_mojang, real_name = query_mojang_api(uuid_str, cache)
                status = "✅ 正版" if exists_on_mojang == "valid" else \
                         "⚠️ 离线" if exists_on_mojang == "offline" else "❓ 未知"

                results.append((real_name or "未知", parsed_uuid, status, "有存档"))

    return results


# 处理客户端模式下的单个世界
def handle_client_mode_single_world(root_dir, world_path, cache):
    playerdata_path = os.path.join(world_path, "playerdata")
    if not os.path.isdir(playerdata_path):
        return []

    results = []
    for file in os.listdir(playerdata_path):
        if file.endswith(".dat"):
            uuid_str = file[:-4]
            try:
                parsed_uuid = uuid.UUID(uuid_str).hex
            except ValueError:
                continue

            exists_on_mojang, real_name = query_mojang_api(uuid_str, cache)
            status = "✅ 正版" if exists_on_mojang == "valid" else \
                     "⚠️ 离线" if exists_on_mojang == "offline" else "❓ 未知"

            results.append((real_name or "未知", parsed_uuid, status, "有存档"))

    return results


def scan_directory(gui):
    global current_world_path
    root_dir = gui.root_dir_var.get()
    if not os.path.isdir(root_dir):
        messagebox.showerror("错误", "请输入有效的目录路径。")
        return

    cache = load_cache()

    server_test = os.path.isfile(os.path.join(root_dir, "eula.txt"))
    client_test = os.path.isdir(os.path.join(root_dir, "saves"))

    results = []

    if server_test:
        results = handle_server_mode(root_dir, cache)
    elif client_test:
        saves_folder = os.path.join(root_dir, "saves")
        worlds = [d for d in os.listdir(saves_folder) if os.path.isdir(os.path.join(saves_folder, d))]
        if not worlds:
            messagebox.showerror("错误", "未发现任何存档世界。")
            return

        selected_world = simple_choice_window(gui.master, "选择世界", "请选择用于扫描的世界：", 
                                              [os.path.join(saves_folder, w) for w in worlds])
        if not selected_world:
            return

        results = handle_client_mode_single_world(root_dir, selected_world, cache)
        current_world_path = selected_world  # 保存当前世界路径为全局变量
    else:
        messagebox.showerror("错误", "无法识别此目录类型，请确认是否为 Minecraft 根目录。")
        return

    gui.update_table(results)
    save_cache(cache)
    gui.log("✅ 扫描完成。")