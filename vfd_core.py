"""
VFD Enerji Tasarrufu — Hesaplama Çekirdeği
============================================
Saf Python (sadece math + dataclasses). GUI'den bağımsız.
Tüm matematik bu modülde; test edilebilir ve yeniden kullanılabilir.

Referans: EEE 3002 Initial Report (10.05.2026).
"""

import math
from dataclasses import dataclass, field
from typing import List


# ------------------------------------------------------------------ #
# Veri sınıfları                                                      #
# ------------------------------------------------------------------ #
@dataclass
class MotorParams:
    """Motor nameplate ve operasyonel parametreler."""
    Pn: float = 22.0          # Motor nominal gücü [kW]
    P_pump_n: float = 20.0    # Pompa nominal şaft gücü [kW] (≤ Pn)
    VLL: float = 400.0        # Hat-hat gerilim [V]
    freq: float = 50.0        # Frekans [Hz]
    poles: int = 4            # Kutup sayısı
    nn: float = 1465.0        # Nominal hız [rpm]
    eff_n: float = 0.91       # Nominal verim
    pf: float = 0.86          # Güç faktörü cos(phi)
    eff_vfd: float = 0.97     # VFD verimi


@dataclass
class CircuitParams:
    """Per-faz eşdeğer devre parametreleri (yıldız, statora indirgenmiş)."""
    R1: float = 0.29
    R2: float = 0.18
    X1: float = 0.52
    X2: float = 0.52
    Xm: float = 18.5


@dataclass
class LoadMode:
    """Yıllık duty cycle içindeki tek bir yük modu."""
    label: str
    share: float       # 0-1 aralığında (zaman payı)
    q_ratio: float     # Q/Qn
    eff_motor: float   # bu yüklemede motor verimi


@dataclass
class OperatingProfile:
    """Yıllık çalışma profili — saatler + yük modları."""
    hours_per_day: float = 16.0
    days_per_year: float = 350.0
    modes: List[LoadMode] = field(default_factory=lambda: [
        LoadMode("Tam yük",    0.20, 1.00, 0.91),
        LoadMode("Yüksek yük", 0.30, 0.80, 0.89),
        LoadMode("Orta yük",   0.35, 0.60, 0.85),
        LoadMode("Düşük yük",  0.15, 0.40, 0.78),
    ])

    @property
    def hours_year(self) -> float:
        return self.hours_per_day * self.days_per_year


@dataclass
class EconomicParams:
    """Tarife, kurulum maliyeti ve emisyon faktörü."""
    tariff: float = 2.80      # TL / kWh
    vfd_cost: float = 45000.0  # TL
    co2_factor: float = 0.442  # kg CO2 / kWh


# ------------------------------------------------------------------ #
# Çekirdek hesaplayıcı                                                #
# ------------------------------------------------------------------ #
class VFDAnalyzer:
    """Tüm hesap mantığını içeren çekirdek. Rapordaki bölüm numaraları
    ilgili metotların docstring'lerinde yer alır."""

    def __init__(self, motor: MotorParams, circuit: CircuitParams,
                 profile: OperatingProfile, econ: EconomicParams):
        self.motor = motor
        self.circuit = circuit
        self.profile = profile
        self.econ = econ

    # ---- 3.1: Senkron hız & slip ----
    def synchronous_speed(self) -> float:
        """ns = 120·f / p (rpm)"""
        return 120.0 * self.motor.freq / self.motor.poles

    def rated_slip(self) -> float:
        """sn = (ns − nn) / ns"""
        ns = self.synchronous_speed()
        return (ns - self.motor.nn) / ns

    def angular_speeds(self):
        """(ωs, ωm) çiftini döndürür."""
        ns = self.synchronous_speed()
        sn = self.rated_slip()
        ws = 2 * math.pi * ns / 60.0
        wm = (1 - sn) * ws
        return ws, wm

    # ---- 3.2: Nominal şaft torku ----
    def rated_torque(self) -> float:
        """Tn = Pn / ωm  (N·m)"""
        _, wm = self.angular_speeds()
        return self.motor.Pn * 1000.0 / wm

    # ---- 3.3: Eşdeğer devre doğrulaması ----
    def equivalent_circuit(self) -> dict:
        """Yaklaşık devre (mıknatıslama dalı terminale taşınmış)."""
        sn = self.rated_slip()
        V1 = self.motor.VLL / math.sqrt(3)
        R_tot = self.circuit.R1 + self.circuit.R2 / sn
        X_tot = self.circuit.X1 + self.circuit.X2
        Z_mag = math.sqrt(R_tot**2 + X_tot**2)
        I1 = V1 / Z_mag
        P_ag = 3 * I1**2 * (self.circuit.R2 / sn)
        P_mech = P_ag * (1 - sn)
        return {
            "V1": V1, "R_tot": R_tot, "X_tot": X_tot,
            "Z_mag": Z_mag, "I1": I1,
            "P_ag_W": P_ag, "P_mech_W": P_mech,
        }

    # ---- 3.5: Throttling kontrolünde şebeke gücü ----
    def grid_power_throttle(self, q: float) -> float:
        """P_grid (kW) — lineer yaklaşım: P_throttle = P_pump_n·(0.40 + 0.60·Q/Qn)"""
        P_throttle = self.motor.P_pump_n * (0.40 + 0.60 * q)
        return P_throttle / self.motor.eff_n

    # ---- 3.6: VFD kontrolünde şebeke gücü ----
    def grid_power_vfd(self, q: float, eff_motor: float) -> float:
        """P_grid (kW) — kübik afinite yasası: P_pump = P_pump_n·(Q/Qn)³"""
        P_pump = self.motor.P_pump_n * (q ** 3)
        return P_pump / (eff_motor * self.motor.eff_vfd)

    # ---- 3.7–3.8: Yıllık enerji ve ekonomik analiz ----
    def annual_analysis(self) -> dict:
        """Tüm yük modları için kapsamlı yıllık analiz."""
        rows = []
        EA_total = 0.0
        EB_total = 0.0
        h_year = self.profile.hours_year

        for m in self.profile.modes:
            hours = m.share * h_year
            P_throttle = self.motor.P_pump_n * (0.40 + 0.60 * m.q_ratio)
            P_grid_A = P_throttle / self.motor.eff_n
            P_pump = self.motor.P_pump_n * (m.q_ratio ** 3)
            P_grid_B = P_pump / (m.eff_motor * self.motor.eff_vfd)
            E_A = P_grid_A * hours
            E_B = P_grid_B * hours
            EA_total += E_A
            EB_total += E_B
            rows.append({
                "label": m.label, "share": m.share, "q": m.q_ratio,
                "hours": hours,
                "P_throttle": P_throttle, "P_grid_A": P_grid_A, "E_A": E_A,
                "P_pump": P_pump, "P_grid_B": P_grid_B, "E_B": E_B,
                "eff_motor": m.eff_motor,
            })

        dE = EA_total - EB_total
        pct = 100.0 * dE / EA_total if EA_total > 0 else 0.0
        dCost = dE * self.econ.tariff
        payback_year = self.econ.vfd_cost / dCost if dCost > 0 else float("inf")
        dCO2 = dE * self.econ.co2_factor / 1000.0
        net10 = dCost * 10 - self.econ.vfd_cost

        return {
            "rows": rows,
            "hours_year": h_year,
            "E_throttle": EA_total,
            "E_vfd": EB_total,
            "energy_saving": dE,
            "saving_pct": pct,
            "cost_saving": dCost,
            "payback_year": payback_year,
            "payback_month": payback_year * 12,
            "co2_reduction_t": dCO2,
            "net_10y": net10,
        }
