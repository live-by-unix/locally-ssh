import customtkinter as ctk
import paramiko
import threading
import json
import os
import time
from datetime import datetime
from tkinter import messagebox, filedialog

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class GhosterPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GHOSTER")
        self.geometry("1200x800")
        self.db_path = "ghost_v3.json"
        self.nodes = self.load_nodes()
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # SIDEBAR
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="GHOSTER ", font=("Courier", 24, "bold")).pack(pady=20)
        ctk.CTkButton(self.sidebar, text="ADD NODE", command=self.add_node_window).pack(pady=10, padx=10)
        ctk.CTkButton(self.sidebar, text="EXPORT LOGS", command=self.export_all_logs, fg_color="transparent", border_width=1).pack(pady=10, padx=10)
        
        # MAIN VIEW (TABS)
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.tabview.add("Nodes")
        
        self.node_scroll = ctk.CTkScrollableFrame(self.tabview.tab("Nodes"), fg_color="transparent")
        self.node_scroll.pack(fill="both", expand=True)
        self.node_scroll.grid_columnconfigure((0,1,2), weight=1)
        
        self.refresh_dashboard()

    def load_nodes(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "r") as f: return json.load(f)
        return []

    def save_nodes(self):
        with open(self.db_path, "w") as f: json.dump(self.nodes, f)

    def refresh_dashboard(self):
        for widget in self.node_scroll.winfo_children(): widget.destroy()
        for i, node in enumerate(self.nodes):
            card = ctk.CTkFrame(self.node_scroll, border_width=1, border_color="#333")
            card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew")
            ctk.CTkLabel(card, text=node['name'], font=("Courier", 18, "bold")).pack(pady=5)
            ctk.CTkLabel(card, text=node['ip'], text_color="#888").pack()
            ctk.CTkButton(card, text="IGNITE", command=lambda n=node: self.ignite_session(n)).pack(pady=10, padx=20)
            ctk.CTkButton(card, text="SFTP", fg_color="#333", command=lambda n=node: self.open_sftp(n)).pack(pady=5, padx=20)

    def add_node_window(self):
        win = ctk.CTkToplevel(self)
        win.geometry("400x500")
        win.title("Node Config")
        win.attributes("-topmost", True)
        
        entries = {}
        for f in ["Name", "IP", "User", "Pass"]:
            ctk.CTkLabel(win, text=f).pack()
            e = ctk.CTkEntry(win, width=250, show="*" if f=="Pass" else "")
            e.pack(pady=5)
            entries[f] = e

        key_path = ctk.StringVar(value="")
        ctk.CTkButton(win, text="Select SSH Key", command=lambda: key_path.set(filedialog.askopenfilename())).pack(pady=10)

        def save():
            self.nodes.append({
                "name": entries["Name"].get(), "ip": entries["IP"].get(),
                "user": entries["User"].get(), "pass": entries["Pass"].get(),
                "key": key_path.get()
            })
            self.save_nodes()
            self.refresh_dashboard()
            win.destroy()
        
        ctk.CTkButton(win, text="SAVE TO VAULT", fg_color="green", command=save).pack(pady=20)

    def ignite_session(self, node):
        tab_name = f"Term: {node['name']}"
        if tab_name in self.tabview._tab_dict: self.tabview.set(tab_name); return
        
        self.tabview.add(tab_name)
        tab = self.tabview.tab(tab_name)
        
        stats_label = ctk.CTkLabel(tab, text="Monitoring: CPU 0% | MEM 0%", font=("Courier", 12), text_color="cyan")
        stats_label.pack(side="top", anchor="w", padx=10)
        
        text = ctk.CTkTextbox(tab, font=("Courier", 14), fg_color="#000", text_color="#00ff00")
        text.pack(fill="both", expand=True, padx=5, pady=5)
        
        def ssh_logic():
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                if node['key']:
                    client.connect(node['ip'], username=node['user'], pkey=paramiko.RSAKey.from_private_key_file(node['key']))
                else:
                    client.connect(node['ip'], username=node['user'], password=node['pass'])
                
                chan = client.invoke_shell()
                
                def monitor():
                    while True:
                        _, stdout, _ = client.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' && free -m | grep Mem | awk '{print $3/$2 * 100.0}'")
                        res = stdout.read().decode().split()
                        if len(res) >= 2:
                            stats_label.configure(text=f"Monitoring: CPU {res[0]}% | MEM {res[1][:4]}%")
                        time.sleep(5)

                threading.Thread(target=monitor, daemon=True).start()

                def listen():
                    while True:
                        if chan.recv_ready():
                            text.insert("end", chan.recv(1024).decode('utf-8', 'ignore'))
                            text.see("end")
                
                threading.Thread(target=listen, daemon=True).start()
                text.bind("<Return>", lambda e: (chan.send(text.get("insert linestart", "insert lineend").split('\n')[-1] + "\n"), "break")[1])
                
            except Exception as e:
                messagebox.showerror("Error", str(e))

        threading.Thread(target=ssh_logic, daemon=True).start()

    def open_sftp(self, node):
        win = ctk.CTkToplevel(self)
        win.title(f"SFTP Explorer: {node['name']}")
        win.geometry("500x600")
        listbox = ctk.CTkTextbox(win)
        listbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        try:
            transport = paramiko.Transport((node['ip'], 22))
            transport.connect(username=node['user'], password=node['pass'])
            sftp = paramiko.SFTPClient.from_transport(transport)
            files = sftp.listdir('.')
            listbox.insert("1.0", "\n".join(files))
        except Exception as e:
            listbox.insert("1.0", f"Error: {e}")

    def export_all_logs(self):
        with open(f"ghost_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w") as f:
            f.write(f"Ghoster Export - Nodes: {len(self.nodes)}\n")
            for n in self.nodes: f.write(f"{n['name']} ({n['ip']})\n")
        messagebox.showinfo("Success", "Logs Exported to Root.")

if __name__ == "__main__":
    app = GhosterPro()
    app.mainloop()
