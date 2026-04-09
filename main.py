"© 2026 Punksm4ck. All rights reserved."
"© 2026 Punksm4ck. All rights reserved."
import asyncio
import threading
import sys
import math
import colorsys
import traceback
import subprocess
from datetime import datetime
import tkinter as tk
import customtkinter as ctk
from bleak import BleakScanner, BleakClient

class MohuanProtocol:
    @staticmethod
    def power(state=True):
        return bytearray([0x69, 0x96, 0x02, 0x01, 0x01 if state else 0x00])

    @staticmethod
    def rgb(r, g, b, brightness=100):
        scale = max(0.0, min(1.0, float(brightness) / 100.0))
        return bytearray([0x69, 0x96, 0x05, 0x02, int(r * scale), int(g * scale), int(b * scale)])

    @staticmethod
    def hardware_mode(mode_byte, speed=100):
        return bytearray([0x69, 0x96, 0x03, 0x03, mode_byte, speed])

class ColorWheel(tk.Canvas):
    def __init__(self, master, command=None, **kwargs):
        super().__init__(master, width=320, height=320, bg="#212121", highlightthickness=0, **kwargs)
        self.command = command
        self.radius, self.center = 150, 160
        self.draw_wheel()
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_click)

    def draw_wheel(self):
        for angle in range(0, 360, 1):
            rad = math.radians(angle)
            x1, y1 = self.center + math.cos(rad) * 100, self.center + math.sin(rad) * 100
            x2, y2 = self.center + math.cos(rad) * self.radius, self.center + math.sin(rad) * self.radius
            h = angle / 360.0
            r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0)]
            self.create_polygon(self.center, self.center, x1, y1, x2, y2, fill=f"#{r:02x}{g:02x}{b:02x}", outline="")
        self.create_oval(self.center-90, self.center-90, self.center+90, self.center+90, fill="#000000", outline="")
        self.create_oval(self.center-60, self.center-60, self.center+60, self.center+60, fill="#212121", outline="")

    def on_click(self, event):
        dx, dy = event.x - self.center, event.y - self.center
        dist = math.sqrt(dx**2 + dy**2)
        if dist > self.radius: return
        angle = math.atan2(dy, dx)
        if angle < 0: angle += 2 * math.pi
        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(angle/(2*math.pi), 1.0, 1.0)]
        self.delete("indicator")
        ix, iy = self.center + math.cos(angle) * 125, self.center + math.sin(angle) * 125
        self.create_oval(ix-10, iy-10, ix+10, iy+10, outline="#FFFFFF", width=4, tags="indicator")
        if self.command: self.command(r, g, b)

class MohuanEnterpriseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MohuanLED v23.0 - Omni-Sight Array")
        self.geometry("1600x1050")
        ctk.set_appearance_mode("dark")

        self.ble_loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_ble_loop, daemon=True).start()

        self.is_on, self.current_r, self.current_g, self.current_b, self.current_brightness = True, 255, 255, 255, 100
        self.discovered_hardware, self.active_clients, self.device_checkboxes = {}, {}, {}
        self.scanner = None

        self._build_ui_core()
        asyncio.run_coroutine_threadsafe(self._omni_sight_radar(), self.ble_loop)

    def _run_ble_loop(self):
        asyncio.set_event_loop(self.ble_loop)
        self.ble_loop.run_forever()

    def log(self, msg, level="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{level}] {msg}")
        color = {"INFO": "#FFFFFF", "SUCCESS": "#4CAF50", "BT": "#2196F3", "CRITICAL": "#F44336"}.get(level, "#FFFFFF")
        def update():
            self.log_window.configure(state="normal")
            self.log_window.insert("end", f"[{ts}] [{level}] {msg}\n", level)
            self.log_window.tag_config(level, foreground=color)
            self.log_window.see("end")
            self.log_window.configure(state="disabled")
        self.after(0, update)

    def _build_ui_core(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = ctk.CTkFrame(self, width=450, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="FLEET PERSISTENCE RADAR", font=("Courier", 24, "bold")).pack(pady=30)
        self.device_container = ctk.CTkScrollableFrame(self.sidebar, height=600)
        self.device_container.pack(padx=20, pady=10, fill="both", expand=True)
        self.btn_link = ctk.CTkButton(self.sidebar, text="FORCE FLEET SYNC", fg_color="#4CAF50", height=65, font=("Courier", 16, "bold"), command=self.connect_ble)
        self.btn_link.pack(padx=30, pady=15, fill="x")
        self.main_view = ctk.CTkTabview(self)
        self.main_view.grid(row=0, column=1, padx=25, pady=25, sticky="nsew")
        self.tabs = {n: self.main_view.add(n) for n in ["PrimaryCommand", "LogicDynamics", "RhythmSync"]}
        self.log_window = ctk.CTkTextbox(self, height=300, font=("Courier", 12), border_width=2, border_color="#333333")
        self.log_window.grid(row=1, column=0, columnspan=2, padx=25, pady=(0, 25), sticky="nsew")
        self.log_window.configure(state="disabled")
        self._setup_tabs()

    def _setup_tabs(self):
        t = self.tabs["PrimaryCommand"]
        ctk.CTkButton(t, text="⏻ GLOBAL FLEET POWER", font=("Courier", 28, "bold"), fg_color="#F44336", height=100, command=self.toggle_power).pack(fill="x", padx=60, pady=35)
        s = ctk.CTkFrame(t, fg_color="transparent"); s.pack(fill="both", expand=True, padx=60)
        l = ctk.CTkFrame(s, fg_color="transparent"); l.pack(side="left", fill="both", expand=True)
        ColorWheel(l, command=self.send_color).pack(pady=15)
        self.sb = ctk.CTkSlider(l, from_=0, to=100, command=self.send_brightness); self.sb.set(100); self.sb.pack(fill="x", pady=30)
        r = ctk.CTkFrame(s, fg_color="#1A1A1A", corner_radius=35); r.pack(side="right", fill="both", expand=True, padx=(50, 0))
        ctk.CTkLabel(r, text="REMOTE MATRIX", font=("Courier", 20, "bold")).pack(pady=25)
        g = ctk.CTkFrame(r, fg_color="transparent"); g.pack(padx=20, pady=20)
        ir = [[("#FF0000",255,0,0),("#00FF00",0,255,0),("#0000FF",0,0,255),("#FFFFFF",255,255,255)],
              [("#FF4500",255,69,0),("#32CD32",50,205,50),("#1E90FF",30,144,255),("#FF69B4",255,105,180)],
              [("#FF8C00",255,140,0),("#00FFFF",0,255,255),("#800080",128,0,128),("#FFB6C1",255,182,193)],
              [("#FFA500",255,165,0),("#20B2AA",32,178,170),("#8B008B",139,0,139),("#87CEEB",135,206,235)],
              [("#FFFF00",255,255,0),("#ADD8E6",173,216,230),("#C71585",199,21,133),("#B0E0E6",176,224,230)]]
        for ri, row in enumerate(ir):
            for ci, (h, red, gr, bl) in enumerate(row):
                ctk.CTkButton(g, text="", fg_color=h, width=75, height=75, corner_radius=38, command=lambda cr=red, cg=gr, cb=bl: self.send_color(cr, cg, cb)).grid(row=ri, column=ci, padx=15, pady=15)

        m_g = ctk.CTkFrame(self.tabs["LogicDynamics"], fg_color="transparent"); m_g.pack(pady=70)
        modes = [("JUMP 3", 0x00), ("JUMP 7", 0x01), ("FADE 3", 0x02), ("FADE 7", 0x03), ("FLASH", 0x04), ("AUTO", 0x05), ("QUICK", 0x06), ("SLOW", 0x07)]
        for i, (name, val) in enumerate(modes):
            ctk.CTkButton(m_g, text=name, font=("Courier", 20, "bold"), fg_color="#3F51B5", width=350, height=110, command=lambda v=val: self.send_packet(MohuanProtocol.hardware_mode(v))).grid(row=i//2, column=i%2, padx=35, pady=35)

        a_g = ctk.CTkFrame(self.tabs["RhythmSync"], fg_color="transparent"); a_g.pack(pady=70)
        for i in range(4):
            ctk.CTkButton(a_g, text=f"RHYTHM SENSOR {i+1}", font=("Courier", 24, "bold"), fg_color="#E91E63", width=450, height=160, command=lambda v=i+8: self.send_packet(MohuanProtocol.hardware_mode(v))).grid(row=i//2, column=i%2, padx=50, pady=50)

    def _device_found_callback(self, device, adv):
        mac = device.address.upper()
        if mac.startswith("23:01") and mac not in self.discovered_hardware:
            self.discovered_hardware[mac] = device
            name = device.name or adv.local_name or f"Ghost_Node_{mac[-5:].replace(':','')}"
            self.log(f"Omni-Sight Locked: {name} ({mac})", "SUCCESS")
            self.after(0, lambda m=mac, n=name: self._inject_node(m, n))

    async def _omni_sight_radar(self):
        self.log("Omni-Sight Radar: Persistent stream engaged.", "BT")
        self.scanner = BleakScanner(detection_callback=self._device_found_callback, scanning_mode="active")
        try:
            await self.scanner.start()
        except Exception as e:
            self.log(f"Radar Startup Fault: {e}", "CRITICAL")

        while True:
            await asyncio.sleep(1)

    def _inject_node(self, mac, name):
        v = tk.StringVar(value="off")
        cb = ctk.CTkCheckBox(self.device_container, text=f"{name}\n{mac}", font=("Courier", 14), variable=v, onvalue=mac, offvalue="off")
        cb.pack(anchor="w", pady=18, padx=25); self.device_checkboxes[mac] = v

    def connect_ble(self):
        macs = [m for m, v in self.device_checkboxes.items() if v.get() != "off"]
        if macs:
            self.log("Arbiter: Suspending continuous stream for Uplink sequence.", "BT")
            asyncio.run_coroutine_threadsafe(self._overseer_uplink(macs), self.ble_loop)

    async def _overseer_uplink(self, macs):
        try:
            await self.scanner.stop()
        except: pass

        subprocess.run(["bluetoothctl", "scan", "off"], capture_output=True)
        for m in macs:
            subprocess.run(["bluetoothctl", "disconnect", m], capture_output=True)
            subprocess.run(["bluetoothctl", "remove", m], capture_output=True)

        await asyncio.sleep(3.0)

        for mac in macs:
            if mac in self.active_clients: continue
            try:
                self.log(f"Tunneling: {mac}", "BT")
                d = await BleakScanner.find_device_by_address(mac, timeout=20.0)
                if not d: continue
                c = BleakClient(d)
                await c.connect(timeout=35.0)
                target = None
                for s in c.services:
                    for ch in s.characteristics:
                        if "write-without-response" in ch.properties:
                            if any(x in ch.uuid.lower() for x in ["ee02", "ffd5", "ffd1"]):
                                target = ch.uuid; break
                    if target: break
                if target:
                    self.active_clients[mac] = {"client": c, "char": target}
                    self.log(f"Uplink Hardened: {mac}", "SUCCESS")
                    await asyncio.sleep(5.0)
                else:
                    await c.disconnect()
            except Exception as e:
                self.log(f"Kernel Fault for {mac}: {str(e)[:50]}", "CRITICAL")
                await asyncio.sleep(2.0)

        try:
            await self.scanner.start()
            self.log("Radar Stream Resumed.", "BT")
        except: pass
        self.after(0, lambda: self.btn_link.configure(text=f"{len(self.active_clients)} NODES SYNCED"))

    def disconnect_all(self): asyncio.run_coroutine_threadsafe(self._purge(), self.ble_loop)
    async def _purge(self):
        for d in list(self.active_clients.values()):
            try: await d["client"].disconnect()
            except: pass
        self.active_clients.clear(); self.after(0, lambda: self.btn_link.configure(text="FORCE FLEET SYNC"))

    def send_packet(self, data):
        asyncio.run_coroutine_threadsafe(self._broadcast(data), self.ble_loop)
    async def _broadcast(self, data):
        for entry in list(self.active_clients.values()):
            try: await entry["client"].write_gatt_char(entry["char"], data, response=False)
            except: pass

    def toggle_power(self):
        self.is_on = not self.is_on; self.send_packet(MohuanProtocol.power(self.is_on))
    def send_color(self, r, g, b):
        self.current_r, self.current_g, self.current_b = r, g, b
        self.send_packet(MohuanProtocol.rgb(r, g, b, self.current_brightness))
    def send_brightness(self, v):
        self.current_brightness = float(v)
        self.send_packet(MohuanProtocol.rgb(self.current_r, self.current_g, self.current_b, self.current_brightness))

if __name__ == "__main__": MohuanEnterpriseApp().mainloop()
