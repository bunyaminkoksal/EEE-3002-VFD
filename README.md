# VFD Enerji Tasarrufu Analiz Aracı

EEE 3002 — Electric Machines, Design Project (Initial Report tabanlı)
Endüstriyel santrifüj pompa için throttling (kısma) vs VFD (Variable Frequency Drive) karşılaştırması.

## Dosya yapısı

```
vfd_app/
├── vfd_core.py            # Hesaplama çekirdeği (saf Python, GUI-bağımsız)
├── vfd_analyzer.py        # Tkinter + matplotlib GUI
├── test_calculations.py   # Rapor sonuçlarına karşı doğrulama
├── preview.py             # Headless örnek grafikler
└── README.md
```

## Kurulum

Python 3.8+ gereklidir.

```bash
pip install numpy matplotlib
```

`tkinter` Python ile birlikte yerleşik gelir.
Linux'ta yoksa: `sudo apt install python3-tk`

## Çalıştırma

```bash
python vfd_analyzer.py
```

Doğrulama testini çalıştırmak için (GUI başlatmaz):
```bash
python test_calculations.py
```

## Özellikler

### Girdi parametreleri (4 sekme)

1. **Motor** — Motor nominal gücü (Pn), pompa nominal şaft gücü, hat gerilimi,
   frekans, kutup sayısı, nominal hız, verim, güç faktörü, VFD verimi.
2. **Eşdeğer Devre** — R₁, R₂', X₁, X₂', Xm (per-faz, statora indirgenmiş).
3. **Yük Profili** — Günlük/yıllık çalışma saatleri ve 4 yük modu için pay (%),
   Q/Qn oranı ve motor verimi. Pay toplamı 100% olmazsa uyarı verir.
4. **Ekonomi** — Elektrik tarifesi, VFD kurulum maliyeti, CO₂ emisyon faktörü.

### Çıktılar

- **Özet kartları**: yıllık tasarruf, oran, kazanç, geri ödeme süresi, CO₂ azalımı, 10-yıl net.
- **Şebeke Gücü grafiği**: yük noktası başına throttling vs VFD karşılaştırması.
- **Yıllık Enerji grafiği**: yıllık enerji dağılımı.
- **Sürekli Eğriler**: Q/Qn'nin tam aralığında (0.1–1.0) iki kontrol stratejisinin
   sürekli güç eğrileri ve tasarruf bölgesi.
- **Detay Tablo**: tüm yük modları için sayısal değerler + toplam satırı.
- **Devre Doğrulama**: eşdeğer devreden hesaplanan I₁, Pag, Pmech ve nameplate ile
   karşılaştırma.

### Diğer

- **Varsayılana dön** butonu rapordaki değerlere geri döner.
- **CSV dışa aktar** sonuçları CSV olarak (UTF-8-BOM, ; ayraçlı) kaydeder.
- Matplotlib navigasyon araç çubukları her grafikte (zoom, pan, PNG kaydet).
- Hatalı girdiler (nn ≥ ns gibi) hata mesajı verir.

## Hesaplama yöntemi

### Eşdeğer devre (Bölüm 3.3)

Yaklaşık devre kullanılır — mıknatıslama dalı stator terminaline taşınır.
Faz gerilimi V₁ = V_LL/√3, toplam empedans R = R₁ + R₂'/s, X = X₁ + X₂',
ardından I₁ = V₁/|Z|, Pag = 3·I₁²·R₂'/s, Pmech = Pag·(1−s).

### Throttling kontrolü (Bölüm 3.5)

Motor sabit hızda çalışır; valf kayıpları dahil pompa şaft gücü için lineer yaklaşım:

```
P_throttle = P_pump_n · (0.40 + 0.60 · Q/Qn)
P_grid_A   = P_throttle / η_motor
```

### VFD kontrolü (Bölüm 3.6)

Motor hızı debiyle orantılı olarak ayarlanır. Pompa şaft gücü kübik afinite yasasına uyar:

```
P_pump = P_pump_n · (Q/Qn)³
P_grid_B = P_pump / (η_motor(Q/Qn) · η_VFD)
```

η_motor azalan hızla düşer (varsayılan: 0.91 / 0.89 / 0.85 / 0.78).

### Yıllık enerji ve ekonomi

```
E_i      = P_grid_i · h_i             her yük modu için
ΔE       = Σ E_A − Σ E_B
ΔC       = ΔE · tariff
T_payback = VFD_cost / ΔC             yıl
ΔCO₂     = ΔE · co2_factor            kg → ton
Net_10y  = ΔC · 10 − VFD_cost
```

## Doğrulama

`test_calculations.py` çekirdek modülün rapordaki değerleri tam olarak ürettiğini
doğrular. Rapor varsayılan değerleriyle:

| Metrik | Rapor | Bu uygulama |
|---|---|---|
| Yıllık tasarruf | 44 677 kWh | 44 667 kWh |
| Tasarruf oranı | 43.9 % | 43.9 % |
| Yıllık kazanç | 125 096 TL | 125 068 TL |
| Geri ödeme | ~4.3 ay | 4.3 ay |
| CO₂ azalımı | 19.7 t | 19.7 t |

Kalan minik farklar rapordaki ara yuvarlamalardan kaynaklanır.

## Genişletme

Çekirdek (`vfd_core.py`) GUI'den tamamen bağımsızdır.
Başka bir arayüze (web, CLI, Jupyter) bağlamak için:

```python
from vfd_core import (MotorParams, CircuitParams, LoadMode,
                       OperatingProfile, EconomicParams, VFDAnalyzer)

m = MotorParams(Pn=11.0, P_pump_n=10.0, nn=1450)
a = VFDAnalyzer(m, CircuitParams(), OperatingProfile(), EconomicParams())
result = a.annual_analysis()
print(result["energy_saving"], "kWh/yıl")
```
