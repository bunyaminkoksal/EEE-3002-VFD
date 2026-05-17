"""
VFD Enerji Tasarrufu Analiz Uygulaması — GUI
==============================================
Endüstriyel santrifüj pompa için throttling vs VFD karşılaştırması.
EEE 3002 Electric Machines — Design Project (initial report tabanlı).

Kullanım:
    python vfd_analyzer.py

Gerekli paketler:
    pip install matplotlib numpy
    (tkinter çoğu Python kurulumunda yerleşiktir; Linux'ta:
     sudo apt install python3-tk)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk,
)

from vfd_core import (
    MotorParams, CircuitParams, LoadMode,
    OperatingProfile, EconomicParams, VFDAnalyzer,
)


class VFDApp:
    """Ana Tkinter uygulaması."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("VFD Enerji Tasarrufu Analiz Aracı — EEE 3002")
        self.root.geometry("1280x820")

        self.motor = MotorParams()
        self.circuit = CircuitParams()
        self.profile = OperatingProfile()
        self.econ = EconomicParams()

        self.motor_vars = {}
        self.circuit_vars = {}
        self.econ_vars = {}
        self.profile_vars = {}
        self.mode_vars = []

        self._build_ui()
        self.recalculate()

    # ---------------- UI iskelet ----------------
    def _build_ui(self):
        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left_outer = ttk.Frame(main, width=420)
        main.add(left_outer, weight=0)
        left_outer.pack_propagate(False)

        ttk.Label(left_outer, text="Girdi Parametreleri",
                  font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=8, pady=(4, 8))

        self.nb = ttk.Notebook(left_outer)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.tab_motor = ttk.Frame(self.nb)
        self.tab_circuit = ttk.Frame(self.nb)
        self.tab_load = ttk.Frame(self.nb)
        self.tab_econ = ttk.Frame(self.nb)
        self.nb.add(self.tab_motor,   text="Motor")
        self.nb.add(self.tab_circuit, text="Eşdeğer Devre")
        self.nb.add(self.tab_load,    text="Yük Profili")
        self.nb.add(self.tab_econ,    text="Ekonomi")

        self._build_motor_tab()
        self._build_circuit_tab()
        self._build_load_tab()
        self._build_econ_tab()

        btn_frame = ttk.Frame(left_outer)
        btn_frame.pack(fill=tk.X, padx=4, pady=8)
        ttk.Button(btn_frame, text="Hesapla",
                   command=self.recalculate).pack(
            side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="Varsayılana dön",
                   command=self.reset_defaults).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="CSV dışa aktar",
                   command=self.export_csv).pack(side=tk.LEFT, padx=2)

        right = ttk.Frame(main)
        main.add(right, weight=1)

        self.metrics_frame = ttk.LabelFrame(right, text="Sonuç Özeti")
        self.metrics_frame.pack(fill=tk.X, padx=4, pady=(0, 8))
        self.metric_labels = {}
        self._build_metric_cards()

        self.result_nb = ttk.Notebook(right)
        self.result_nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.tab_power = ttk.Frame(self.result_nb)
        self.tab_energy = ttk.Frame(self.result_nb)
        self.tab_curves = ttk.Frame(self.result_nb)
        self.tab_table = ttk.Frame(self.result_nb)
        self.tab_circuit_out = ttk.Frame(self.result_nb)

        self.result_nb.add(self.tab_power,       text="Şebeke Gücü")
        self.result_nb.add(self.tab_energy,      text="Yıllık Enerji")
        self.result_nb.add(self.tab_curves,      text="Sürekli Eğriler")
        self.result_nb.add(self.tab_table,       text="Detay Tablo")
        self.result_nb.add(self.tab_circuit_out, text="Devre Doğrulama")

        self._build_chart_tabs()
        self._build_table_tab()
        self._build_circuit_output_tab()

    def _add_field(self, parent, row, label, var, unit=""):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", padx=6, pady=3)
        ttk.Entry(parent, textvariable=var, width=12).grid(
            row=row, column=1, sticky="ew", padx=6, pady=3)
        if unit:
            ttk.Label(parent, text=unit, foreground="#666").grid(
                row=row, column=2, sticky="w", padx=2)

    def _build_motor_tab(self):
        f = self.tab_motor
        f.columnconfigure(1, weight=1)
        v = self.motor_vars
        v["Pn"]      = tk.DoubleVar(value=self.motor.Pn)
        v["P_pump_n"]= tk.DoubleVar(value=self.motor.P_pump_n)
        v["VLL"]     = tk.DoubleVar(value=self.motor.VLL)
        v["freq"]    = tk.DoubleVar(value=self.motor.freq)
        v["poles"]   = tk.IntVar(value=self.motor.poles)
        v["nn"]      = tk.DoubleVar(value=self.motor.nn)
        v["eff_n"]   = tk.DoubleVar(value=self.motor.eff_n)
        v["pf"]      = tk.DoubleVar(value=self.motor.pf)
        v["eff_vfd"] = tk.DoubleVar(value=self.motor.eff_vfd)

        self._add_field(f, 0, "Motor nominal gücü Pn",  v["Pn"],       "kW")
        self._add_field(f, 1, "Pompa nom. şaft gücü",   v["P_pump_n"], "kW")
        self._add_field(f, 2, "Hat gerilimi V_LL",      v["VLL"],      "V")
        self._add_field(f, 3, "Frekans f",              v["freq"],     "Hz")
        self._add_field(f, 4, "Kutup sayısı p",         v["poles"],    "")
        self._add_field(f, 5, "Nominal hız nn",         v["nn"],       "rpm")
        self._add_field(f, 6, "Nominal verim ηn",       v["eff_n"],    "")
        self._add_field(f, 7, "Güç faktörü cosφ",       v["pf"],       "")
        self._add_field(f, 8, "VFD verimi η_VFD",       v["eff_vfd"],  "")

        ttk.Label(f, text="Sarım bağlantısı: Yıldız (Y)",
                  foreground="#666").grid(
            row=9, column=0, columnspan=3, sticky="w", padx=6, pady=8)

    def _build_circuit_tab(self):
        f = self.tab_circuit
        f.columnconfigure(1, weight=1)
        v = self.circuit_vars
        v["R1"] = tk.DoubleVar(value=self.circuit.R1)
        v["R2"] = tk.DoubleVar(value=self.circuit.R2)
        v["X1"] = tk.DoubleVar(value=self.circuit.X1)
        v["X2"] = tk.DoubleVar(value=self.circuit.X2)
        v["Xm"] = tk.DoubleVar(value=self.circuit.Xm)

        self._add_field(f, 0, "Stator direnci R₁",        v["R1"], "Ω")
        self._add_field(f, 1, "Rotor direnci (ind.) R₂'", v["R2"], "Ω")
        self._add_field(f, 2, "Stator kaçak reakt. X₁",   v["X1"], "Ω")
        self._add_field(f, 3, "Rotor kaçak reakt. X₂'",   v["X2"], "Ω")
        self._add_field(f, 4, "Mıknatıslama reakt. Xm",   v["Xm"], "Ω")

        info = ("Tüm değerler per-faz, statora indirgenmiş.\n"
                "Yaklaşık eşdeğer devre kullanılır:\n"
                "mıknatıslama dalı terminale taşınmıştır.")
        ttk.Label(f, text=info, foreground="#666",
                  justify="left").grid(
            row=5, column=0, columnspan=3, sticky="w", padx=6, pady=8)

    def _build_load_tab(self):
        f = self.tab_load
        f.columnconfigure(0, weight=1)
        v = self.profile_vars
        v["hpd"] = tk.DoubleVar(value=self.profile.hours_per_day)
        v["dpy"] = tk.DoubleVar(value=self.profile.days_per_year)

        top = ttk.Frame(f)
        top.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        top.columnconfigure(1, weight=1)
        self._add_field(top, 0, "Günlük çalışma", v["hpd"], "saat")
        self._add_field(top, 1, "Yıllık çalışma", v["dpy"], "gün")

        self.hours_year_label = ttk.Label(top, text="", foreground="#0a6")
        self.hours_year_label.grid(row=2, column=0, columnspan=3,
                                    sticky="w", padx=6, pady=(2, 6))

        modes_frame = ttk.LabelFrame(f, text="Yük modları")
        modes_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        f.rowconfigure(1, weight=1)

        headers = ["Etiket", "Pay (%)", "Q/Qn", "η_motor"]
        for j, h in enumerate(headers):
            ttk.Label(modes_frame, text=h,
                      font=("Segoe UI", 9, "bold")).grid(
                row=0, column=j, padx=4, pady=4, sticky="w")

        for i, mode in enumerate(self.profile.modes):
            label_var = tk.StringVar(value=mode.label)
            share_var = tk.DoubleVar(value=mode.share * 100)
            q_var = tk.DoubleVar(value=mode.q_ratio)
            eff_var = tk.DoubleVar(value=mode.eff_motor)

            ttk.Entry(modes_frame, textvariable=label_var, width=12).grid(
                row=i + 1, column=0, padx=4, pady=3)
            ttk.Entry(modes_frame, textvariable=share_var, width=8).grid(
                row=i + 1, column=1, padx=4, pady=3)
            ttk.Entry(modes_frame, textvariable=q_var, width=8).grid(
                row=i + 1, column=2, padx=4, pady=3)
            ttk.Entry(modes_frame, textvariable=eff_var, width=8).grid(
                row=i + 1, column=3, padx=4, pady=3)

            self.mode_vars.append({
                "label": label_var, "share": share_var,
                "q": q_var, "eff": eff_var,
            })

        self.share_sum_label = ttk.Label(f, text="", foreground="#0a6")
        self.share_sum_label.grid(row=2, column=0, sticky="w",
                                   padx=12, pady=4)

    def _build_econ_tab(self):
        f = self.tab_econ
        f.columnconfigure(1, weight=1)
        v = self.econ_vars
        v["tariff"]   = tk.DoubleVar(value=self.econ.tariff)
        v["vfd_cost"] = tk.DoubleVar(value=self.econ.vfd_cost)
        v["co2"]      = tk.DoubleVar(value=self.econ.co2_factor)

        self._add_field(f, 0, "Elektrik tarifesi",    v["tariff"],   "TL/kWh")
        self._add_field(f, 1, "VFD kurulum maliyeti", v["vfd_cost"], "TL")
        self._add_field(f, 2, "CO₂ emisyon faktörü",  v["co2"],      "kg/kWh")

        ttk.Label(f, text="10-yıl net kazanç iskonto edilmeden hesaplanır.",
                  foreground="#666").grid(row=3, column=0, columnspan=3,
                                            sticky="w", padx=6, pady=8)

    def _build_metric_cards(self):
        cards = [
            ("Yıllık enerji tasarrufu", "energy",  "kWh"),
            ("Tasarruf oranı",          "pct",     "%"),
            ("Yıllık kazanç",           "money",   "TL"),
            ("Geri ödeme süresi",       "payback", "ay"),
            ("CO₂ azalımı",             "co2",     "t/yıl"),
            ("10-yıl net kazanç",       "net10",   "TL"),
        ]
        for i, (title, key, unit) in enumerate(cards):
            frame = ttk.Frame(self.metrics_frame, relief="ridge",
                              borderwidth=1, padding=8)
            frame.grid(row=0, column=i, padx=4, pady=4, sticky="nsew")
            self.metrics_frame.columnconfigure(i, weight=1)

            ttk.Label(frame, text=title, font=("Segoe UI", 9),
                      foreground="#555").pack(anchor="w")
            value_lbl = ttk.Label(frame, text="—",
                                   font=("Segoe UI", 14, "bold"),
                                   foreground="#1a5")
            value_lbl.pack(anchor="w", pady=(2, 0))
            ttk.Label(frame, text=unit, font=("Segoe UI", 8),
                      foreground="#888").pack(anchor="w")
            self.metric_labels[key] = value_lbl

    def _build_chart_tabs(self):
        self.fig_power = Figure(figsize=(7, 4.2), dpi=100)
        self.ax_power = self.fig_power.add_subplot(111)
        self.canvas_power = FigureCanvasTkAgg(self.fig_power,
                                                master=self.tab_power)
        self.canvas_power.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas_power, self.tab_power)

        self.fig_energy = Figure(figsize=(7, 4.2), dpi=100)
        self.ax_energy = self.fig_energy.add_subplot(111)
        self.canvas_energy = FigureCanvasTkAgg(self.fig_energy,
                                                master=self.tab_energy)
        self.canvas_energy.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas_energy, self.tab_energy)

        self.fig_curves = Figure(figsize=(7, 4.2), dpi=100)
        self.ax_curves = self.fig_curves.add_subplot(111)
        self.canvas_curves = FigureCanvasTkAgg(self.fig_curves,
                                                master=self.tab_curves)
        self.canvas_curves.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas_curves, self.tab_curves)

    def _build_table_tab(self):
        cols = ("mod", "q", "saat", "PA", "PB", "EA", "EB")
        self.table = ttk.Treeview(self.tab_table, columns=cols,
                                    show="headings", height=10)
        headings = {
            "mod":  ("Mod",            120),
            "q":    ("Q/Qn",            70),
            "saat": ("Saat/yıl",        90),
            "PA":   ("P_throt (kW)",   100),
            "PB":   ("P_VFD (kW)",     100),
            "EA":   ("E_throt (kWh)",  120),
            "EB":   ("E_VFD (kWh)",    120),
        }
        for c, (txt, w) in headings.items():
            self.table.heading(c, text=txt)
            self.table.column(c, width=w, anchor="e")
        self.table.column("mod", anchor="w")
        self.table.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _build_circuit_output_tab(self):
        self.circuit_text = tk.Text(self.tab_circuit_out, height=20,
                                      wrap="word", font=("Consolas", 10))
        self.circuit_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.circuit_text.configure(state="disabled")

    # ---------------- Eylem işleyicileri ----------------
    def _collect_inputs(self) -> bool:
        try:
            m = MotorParams(
                Pn=self.motor_vars["Pn"].get(),
                P_pump_n=self.motor_vars["P_pump_n"].get(),
                VLL=self.motor_vars["VLL"].get(),
                freq=self.motor_vars["freq"].get(),
                poles=int(self.motor_vars["poles"].get()),
                nn=self.motor_vars["nn"].get(),
                eff_n=self.motor_vars["eff_n"].get(),
                pf=self.motor_vars["pf"].get(),
                eff_vfd=self.motor_vars["eff_vfd"].get(),
            )
            c = CircuitParams(
                R1=self.circuit_vars["R1"].get(),
                R2=self.circuit_vars["R2"].get(),
                X1=self.circuit_vars["X1"].get(),
                X2=self.circuit_vars["X2"].get(),
                Xm=self.circuit_vars["Xm"].get(),
            )
            modes = []
            share_sum = 0.0
            for mv in self.mode_vars:
                share = mv["share"].get() / 100.0
                share_sum += mv["share"].get()
                modes.append(LoadMode(
                    label=mv["label"].get(),
                    share=share,
                    q_ratio=mv["q"].get(),
                    eff_motor=mv["eff"].get(),
                ))
            p = OperatingProfile(
                hours_per_day=self.profile_vars["hpd"].get(),
                days_per_year=self.profile_vars["dpy"].get(),
                modes=modes,
            )
            e = EconomicParams(
                tariff=self.econ_vars["tariff"].get(),
                vfd_cost=self.econ_vars["vfd_cost"].get(),
                co2_factor=self.econ_vars["co2"].get(),
            )

            if m.poles < 2 or m.poles % 2 != 0:
                messagebox.showerror(
                    "Geçersiz girdi",
                    "Kutup sayısı çift sayı olmalı (≥2).")
                return False
            ns = 120 * m.freq / m.poles
            if m.nn >= ns:
                messagebox.showerror(
                    "Geçersiz girdi",
                    f"Nominal hız (nn={m.nn}) senkron hızdan "
                    f"(ns={ns:.0f}) küçük olmalı.")
                return False

            if abs(share_sum - 100.0) > 0.5:
                self.share_sum_label.config(
                    text=f"⚠ Pay toplamı: {share_sum:.1f}% (100% olmalı)",
                    foreground="#c33")
            else:
                self.share_sum_label.config(
                    text=f"✓ Pay toplamı: {share_sum:.1f}%",
                    foreground="#0a6")

            self.motor, self.circuit = m, c
            self.profile, self.econ = p, e
            return True
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("Geçersiz girdi", f"Hata: {exc}")
            return False

    def recalculate(self):
        if not self._collect_inputs():
            return
        analyzer = VFDAnalyzer(self.motor, self.circuit,
                                self.profile, self.econ)
        circ = analyzer.equivalent_circuit()
        result = analyzer.annual_analysis()
        self._last_result = (analyzer, circ, result)

        self.hours_year_label.config(
            text=f"Toplam: {self.profile.hours_year:.0f} saat/yıl")

        self.metric_labels["energy"].config(
            text=f"{result['energy_saving']:,.0f}")
        self.metric_labels["pct"].config(
            text=f"{result['saving_pct']:.1f}")
        self.metric_labels["money"].config(
            text=f"{result['cost_saving']:,.0f}")
        self.metric_labels["payback"].config(
            text=f"{result['payback_month']:.1f}")
        self.metric_labels["co2"].config(
            text=f"{result['co2_reduction_t']:.1f}")
        self.metric_labels["net10"].config(
            text=f"{result['net_10y']:,.0f}")

        self._update_power_chart(result)
        self._update_energy_chart(result)
        self._update_curves_chart(analyzer)
        self._update_table(result)
        self._update_circuit_text(analyzer, circ)

    def _update_power_chart(self, result):
        ax = self.ax_power
        ax.clear()
        rows = result["rows"]
        labels = [f"{r['label']}\n(Q={r['q']:.2f})" for r in rows]
        pa = [r["P_grid_A"] for r in rows]
        pb = [r["P_grid_B"] for r in rows]
        x = np.arange(len(rows))
        w = 0.35
        bars1 = ax.bar(x - w/2, pa, w, label="Throttling", color="#D85A30")
        bars2 = ax.bar(x + w/2, pb, w, label="VFD", color="#1D9E75")
        for bars in (bars1, bars2):
            for b in bars:
                ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.2,
                        f"{b.get_height():.1f}", ha="center", fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylabel("Şebeke gücü (kW)")
        ax.set_title("Her yük noktasında şebeke gücü")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        self.fig_power.tight_layout()
        self.canvas_power.draw()

    def _update_energy_chart(self, result):
        ax = self.ax_energy
        ax.clear()
        rows = result["rows"]
        labels = [f"{r['label']}\n(Q={r['q']:.2f})" for r in rows]
        ea = [r["E_A"] for r in rows]
        eb = [r["E_B"] for r in rows]
        x = np.arange(len(rows))
        w = 0.35
        ax.bar(x - w/2, ea, w, label="Throttling", color="#D85A30")
        ax.bar(x + w/2, eb, w, label="VFD",        color="#1D9E75")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylabel("Yıllık enerji (kWh)")
        ax.set_title(
            f"Yıllık enerji — Δ = {result['energy_saving']:,.0f} kWh "
            f"({result['saving_pct']:.1f}%)")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        self.fig_energy.tight_layout()
        self.canvas_energy.draw()

    def _update_curves_chart(self, analyzer: VFDAnalyzer):
        ax = self.ax_curves
        ax.clear()
        q = np.linspace(0.1, 1.0, 100)
        p_a = np.array([analyzer.grid_power_throttle(qi) for qi in q])
        modes = analyzer.profile.modes
        q_pts = sorted([(m.q_ratio, m.eff_motor) for m in modes])
        q_arr = np.array([p[0] for p in q_pts])
        e_arr = np.array([p[1] for p in q_pts])
        eff_interp = np.interp(q, q_arr, e_arr)
        p_b = np.array([analyzer.grid_power_vfd(qi, ei)
                        for qi, ei in zip(q, eff_interp)])
        ax.plot(q, p_a, color="#D85A30", linewidth=2,
                label="Throttling (lineer)")
        ax.plot(q, p_b, color="#1D9E75", linewidth=2,
                label="VFD (kübik afinite)")
        ax.fill_between(q, p_b, p_a, where=(p_a >= p_b),
                          color="#1D9E75", alpha=0.12,
                          label="Tasarruf bölgesi")
        for m in modes:
            ax.axvline(m.q_ratio, color="#aaa", linestyle=":", alpha=0.5)
        ax.set_xlabel("Q / Qn (göreli debi)")
        ax.set_ylabel("Şebeke gücü (kW)")
        ax.set_title("Throttling vs VFD — sürekli yük eğrisi")
        ax.legend(loc="upper left")
        ax.grid(alpha=0.3)
        self.fig_curves.tight_layout()
        self.canvas_curves.draw()

    def _update_table(self, result):
        for row_id in self.table.get_children():
            self.table.delete(row_id)
        for r in result["rows"]:
            self.table.insert("", "end", values=(
                r["label"],
                f"{r['q']:.2f}",
                f"{r['hours']:.0f}",
                f"{r['P_grid_A']:.2f}",
                f"{r['P_grid_B']:.2f}",
                f"{r['E_A']:,.0f}",
                f"{r['E_B']:,.0f}",
            ))
        self.table.insert("", "end", values=(
            "TOPLAM", "—",
            f"{result['hours_year']:.0f}",
            "—", "—",
            f"{result['E_throttle']:,.0f}",
            f"{result['E_vfd']:,.0f}",
        ), tags=("total",))
        self.table.tag_configure("total", background="#eef")

    def _update_circuit_text(self, analyzer: VFDAnalyzer, circ: dict):
        ns = analyzer.synchronous_speed()
        sn = analyzer.rated_slip()
        ws, wm = analyzer.angular_speeds()
        Tn = analyzer.rated_torque()
        Pn_kW = analyzer.motor.Pn
        sapma_pct = abs(circ['P_mech_W']/1000 - Pn_kW) / Pn_kW * 100
        lines = [
            "EŞDEĞER DEVRE DOĞRULAMASI",
            "=" * 50,
            "",
            f"  Senkron hız       ns  = 120·f / p          = {ns:.2f} rpm",
            f"  Rated slip        sn  = (ns − nn) / ns     = {sn*100:.3f} %",
            f"  Senkron açısal    ωs  = 2π·ns / 60         = {ws:.3f} rad/s",
            f"  Mekanik açısal    ωm  = (1−s)·ωs           = {wm:.3f} rad/s",
            f"  Nominal tork      Tn  = Pn / ωm            = {Tn:.2f} N·m",
            "",
            f"  Faz gerilimi      V₁  = V_LL / √3          = {circ['V1']:.3f} V",
            f"  Toplam direnç      R  = R₁ + R₂'/sn         = {circ['R_tot']:.4f} Ω",
            f"  Toplam reaktans    X  = X₁ + X₂'            = {circ['X_tot']:.4f} Ω",
            f"  Empedans modülü   |Z| = √(R²+X²)            = {circ['Z_mag']:.4f} Ω",
            f"  Stator akımı      I₁  = V₁ / |Z|            = {circ['I1']:.3f} A",
            "",
            f"  Hava aralığı gücü Pag = 3·I₁²·(R₂'/sn)      = "
            f"{circ['P_ag_W']:.1f} W ({circ['P_ag_W']/1000:.2f} kW)",
            f"  Mekanik güç     Pmech = Pag·(1−s)           = "
            f"{circ['P_mech_W']:.1f} W ({circ['P_mech_W']/1000:.2f} kW)",
            "",
            f"  Nominal güçle karşılaştırma: Pn = {Pn_kW:.2f} kW",
            f"  Sapma: {sapma_pct:.2f} % "
            "(yaklaşık devre — mıknatıslama akımı ihmal edildi).",
        ]
        self.circuit_text.configure(state="normal")
        self.circuit_text.delete("1.0", tk.END)
        self.circuit_text.insert(tk.END, "\n".join(lines))
        self.circuit_text.configure(state="disabled")

    def reset_defaults(self):
        d_m = MotorParams()
        for k in self.motor_vars:
            self.motor_vars[k].set(getattr(d_m, k))
        d_c = CircuitParams()
        for k in self.circuit_vars:
            self.circuit_vars[k].set(getattr(d_c, k))
        d_p = OperatingProfile()
        self.profile_vars["hpd"].set(d_p.hours_per_day)
        self.profile_vars["dpy"].set(d_p.days_per_year)
        for mv, mode in zip(self.mode_vars, d_p.modes):
            mv["label"].set(mode.label)
            mv["share"].set(mode.share * 100)
            mv["q"].set(mode.q_ratio)
            mv["eff"].set(mode.eff_motor)
        d_e = EconomicParams()
        self.econ_vars["tariff"].set(d_e.tariff)
        self.econ_vars["vfd_cost"].set(d_e.vfd_cost)
        self.econ_vars["co2"].set(d_e.co2_factor)
        self.recalculate()

    def export_csv(self):
        if not hasattr(self, "_last_result"):
            self.recalculate()
            if not hasattr(self, "_last_result"):
                return
        _, _, result = self._last_result
        path = filedialog.asksaveasfilename(
            title="CSV olarak kaydet",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="vfd_analiz.csv",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as fp:
                fp.write("Mod;Q/Qn;Saat;P_throt(kW);P_VFD(kW);"
                          "E_throt(kWh);E_VFD(kWh)\n")
                for r in result["rows"]:
                    fp.write(f"{r['label']};{r['q']:.3f};"
                              f"{r['hours']:.1f};"
                              f"{r['P_grid_A']:.3f};{r['P_grid_B']:.3f};"
                              f"{r['E_A']:.1f};{r['E_B']:.1f}\n")
                fp.write(f"\nTOPLAM;;{result['hours_year']:.1f};;;")
                fp.write(f"{result['E_throttle']:.1f};"
                          f"{result['E_vfd']:.1f}\n")
                fp.write("\nÖzet\n")
                fp.write(f"Yıllık tasarruf (kWh);"
                          f"{result['energy_saving']:.1f}\n")
                fp.write(f"Tasarruf (%);{result['saving_pct']:.2f}\n")
                fp.write(f"Yıllık kazanç (TL);"
                          f"{result['cost_saving']:.2f}\n")
                fp.write(f"Geri ödeme (ay);"
                          f"{result['payback_month']:.2f}\n")
                fp.write(f"CO2 azalımı (ton/yıl);"
                          f"{result['co2_reduction_t']:.3f}\n")
                fp.write(f"10 yıl net (TL);{result['net_10y']:.2f}\n")
            messagebox.showinfo("Dışa aktarım",
                                  f"Sonuçlar kaydedildi:\n{path}")
        except OSError as exc:
            messagebox.showerror("Hata", f"Dosya yazılamadı: {exc}")


def main():
    root = tk.Tk()
    style = ttk.Style(root)
    available = style.theme_names()
    for preferred in ("clam", "vista", "alt", "default"):
        if preferred in available:
            style.theme_use(preferred)
            break
    VFDApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
