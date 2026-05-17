"""
Hesaplama çekirdeğini rapordaki değerlere karşı doğrular.
GUI başlatılmadan (headless) yalnızca matematik çağrılır.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from vfd_core import (
    MotorParams, CircuitParams, OperatingProfile, EconomicParams,
    VFDAnalyzer,
)

motor = MotorParams()
circuit = CircuitParams()
profile = OperatingProfile()
econ = EconomicParams()

a = VFDAnalyzer(motor, circuit, profile, econ)

print("--- Bölüm 3.1 ---")
print(f"ns = {a.synchronous_speed():.2f} rpm  (rapor: 1500)")
print(f"sn = {a.rated_slip()*100:.3f} %  (rapor: 2.33)")
ws, wm = a.angular_speeds()
print(f"ws = {ws:.2f} rad/s  (rapor: 157.08)")
print(f"wm = {wm:.2f} rad/s  (rapor: 153.42)")

print("\n--- Bölüm 3.2 ---")
print(f"Tn = {a.rated_torque():.1f} N·m  (rapor: 143.4)")

print("\n--- Bölüm 3.3 ---")
c = a.equivalent_circuit()
print(f"V1 = {c['V1']:.2f} V  (rapor: 230.9)")
print(f"|Z| = {c['Z_mag']:.2f} Ω  (rapor: 8.09)")
print(f"I1 = {c['I1']:.2f} A  (rapor: 28.5)")
print(f"Pag = {c['P_ag_W']:.0f} W  (rapor: 18834)")
print(f"Pmech = {c['P_mech_W']:.0f} W  (rapor: 18396)")

print("\n--- Bölüm 3.5 (Throttling) ---")
for q in [1.0, 0.8, 0.6, 0.4]:
    print(f"  Q/Qn={q}: P_grid_A = {a.grid_power_throttle(q):.2f} kW")
print("  Rapor: 21.98 / 19.34 / 16.70 / 14.07")

print("\n--- Bölüm 3.6 (VFD) ---")
effs = {1.0: 0.91, 0.8: 0.89, 0.6: 0.85, 0.4: 0.78}
for q, e in effs.items():
    print(f"  Q/Qn={q}: P_grid_B = {a.grid_power_vfd(q, e):.2f} kW")
print("  Rapor: 22.65 / 11.86 / 5.24 / 1.69")

print("\n--- Bölüm 3.7-3.8 (Yıllık) ---")
r = a.annual_analysis()
print(f"E_throttle = {r['E_throttle']:,.0f} kWh  (rapor: 101 660)")
print(f"E_vfd      = {r['E_vfd']:,.0f} kWh  (rapor: 56 983)")
print(f"Tasarruf   = {r['energy_saving']:,.0f} kWh  (rapor: 44 677)")
print(f"Oran       = {r['saving_pct']:.1f} %  (rapor: 43.9)")
print(f"Kazanç     = {r['cost_saving']:,.0f} TL/yıl  (rapor: 125 096)")
print(f"Geri ödeme = {r['payback_month']:.2f} ay  (rapor: ~4.3)")
print(f"CO2        = {r['co2_reduction_t']:.2f} t/yıl  (rapor: 19.7)")
print(f"10-yıl net = {r['net_10y']:,.0f} TL  (rapor: ~1 205 960)")
