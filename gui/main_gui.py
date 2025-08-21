import os
import threading
import shutil
import uuid
from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog, messagebox, Toplevel
from nbtlib import File, Compound
# 修复相对导入问题
import sys
import os as os2
sys.path.append(os2.path.dirname(os2.path.dirname(os2.path.abspath(__file__))))
from core.scanner import scan_directory, simple_choice_window, current_world_path


# 显示 NBT 内容（支持压缩）
def show_nbt_content(file_path, parent_window):
    try:
        # 加载 NBT 文件（带 gzip 解压）
        nbt_data = File.load(file_path, gzipped=True)

        window = Toplevel(parent_window)
        window.transient(parent_window)  # 设置为临时窗口（跟随主窗口）
        window.grab_set()                # 抢占焦点，阻止与主窗口交互
        window.title("NBT 内容预览")
        window.geometry("800x600")

        text = Text(window, wrap=None)
        text.pack(fill=BOTH, expand=True)

        def insert_compound(compound, depth=0):
            indent = "  " * depth
            for key, value in compound.items():
                if isinstance(value, Compound):
                    text.insert(END, f"{indent}{key}:\n")
                    insert_compound(value, depth + 1)
                else:
                    text.insert(END, f"{indent}{key}: {value}\n")

        # 直接使用 nbt_data 作为根节点
        insert_compound(nbt_data, depth=0)
        text.config(state=DISABLED)

    except Exception as e:
        messagebox.showerror("错误", f"无法解析 NBT 文件: {str(e)}")


# 查找对应 uuid 的 .dat 文件路径
def find_player_dat(playerdata_path, uuid_str):
    # 支持无连字符和有连字符的 uuid
    try:
        uuid_canonical = str(uuid.UUID(uuid_str))
    except Exception:
        uuid_canonical = uuid_str
    candidates = [
        os.path.join(playerdata_path, f"{uuid_str}.dat"),
        os.path.join(playerdata_path, f"{uuid_canonical}.dat"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


# GUI 类
class UUIDScannerGUI:
    def __init__(self, master):
        self.master = master
        master.title("Minecraft UUID 查询工具 - GUI 版")
        master.geometry("1000x600")

        Label(master, text="Minecraft 根目录：").pack(pady=5)
        self.root_dir_var = StringVar()
        Entry(master, textvariable=self.root_dir_var, width=80).pack(pady=5)
        Button(master, text="浏览...", command=self.browse_dir).pack(pady=5)
        Button(master, text="开始扫描", command=self.start_scan).pack(pady=10)
        Button(master, text="替换存档", command=self.replace_dat_file).pack(pady=5)

        self.table = Treeview(master, columns=("名称", "UUID", "类型", "存档"), show="headings")
        self.table.heading("名称", text="名称")
        self.table.heading("UUID", text="UUID")
        self.table.heading("类型", text="类型")
        self.table.heading("存档", text="存档")
        self.table.pack(fill=BOTH, expand=True, padx=10, pady=5)

        self.log_area = Text(master, height=10)
        self.log_area.pack(padx=10, pady=5, fill=X)

    def log(self, message):
        self.log_area.insert(END, message + "\n")
        self.log_area.see(END)

    def browse_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.root_dir_var.set(path)

    def start_scan(self):
        threading.Thread(target=scan_directory, args=(self,), daemon=True).start()
        self.log("⏳ 开始扫描...")

    def update_table(self, results):
        for row in self.table.get_children():
            self.table.delete(row)

        for item in results:
            self.table.insert("", END, values=item)

    def replace_dat_file(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个玩家。")
            return

        item = self.table.item(selected[0])
        uuid_str = item['values'][1]

        confirm = messagebox.askyesno("确认操作", "确定要替换此玩家的存档吗？\n这将覆盖原始文件。")
        if not confirm:
            return

        new_dat_path = filedialog.askopenfilename(
            title="选择新的 .dat 文件",
            filetypes=[("Minecraft 存档文件", "*.dat"), ("所有文件", "*.*")]
        )
        if not new_dat_path:
            return

        show_nbt_content(new_dat_path, self.master)

        root_dir = self.root_dir_var.get()
        server_test = os.path.isfile(os.path.join(root_dir, "eula.txt"))
        client_test = os.path.isdir(os.path.join(root_dir, "saves"))

        global current_world_path
        if server_test:
            playerdata_path = os.path.join(root_dir, "world", "playerdata")
        elif client_test:
            if not current_world_path:
                messagebox.showerror("错误", "请先扫描并选择一个世界。"+str(current_world_path))
                return
            playerdata_path = os.path.join(current_world_path, "playerdata")
        else:
            messagebox.showerror("错误", "无法识别目录类型。")
            return

        target_path = find_player_dat(playerdata_path, uuid_str)
        if not target_path:
            messagebox.showerror("错误", "找不到对应的目标 .dat 文件。")
            return

        backup_path = target_path + ".bak"
        if os.path.exists(target_path):
            import shutil
            shutil.copy2(target_path, backup_path)
            self.log(f"📦 已备份原文件到: {backup_path}")

        # 新增：查找并替换 .dat_old 文件
        dat_old_path = target_path + "_old"
        backup_old_path = dat_old_path + ".bak"
        dat_old_exists = os.path.exists(dat_old_path)
        if dat_old_exists:
            shutil.copy2(dat_old_path, backup_old_path)
            self.log(f"📦 已备份原 .dat_old 文件到: {backup_old_path}")

        try:
            with open(new_dat_path, 'rb') as src:
                new_data = src.read()
            with open(target_path, 'wb') as dst:
                dst.write(new_data)
            if dat_old_exists:
                with open(dat_old_path, 'wb') as dst_old:
                    dst_old.write(new_data)
            self.log(f"✅ 成功替换存档文件: {target_path}")
            if dat_old_exists:
                self.log(f"✅ 成功替换存档文件: {dat_old_path}")
            messagebox.showinfo("成功", "已成功替换存档文件！")
            self.start_scan()  # 自动刷新表格
        except Exception as e:
            messagebox.showerror("错误", f"替换失败: {str(e)}")