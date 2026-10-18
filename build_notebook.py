"""Builds NYC_Taxi_Analysis.ipynb (chart-first version).

Run:  python3 build_notebook.py
Then: jupyter nbconvert --to notebook --execute --inplace NYC_Taxi_Analysis.ipynb
Then: python3 build_html.py
"""
import nbformat as nbf
from pathlib import Path

HERE = Path(__file__).parent
INSIGHTS = (HERE / "insights.md").read_text()
TAKE = {}
takeaways_path = HERE / "takeaways.py"
if takeaways_path.exists():
    exec(takeaways_path.read_text(), TAKE)
T = lambda key: TAKE.get("TAKEAWAYS", {}).get(key, "")

cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip("\n").replace("$", r"\$")))
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip("\n")))
def takeaway(key):
    t = T(key)
    if t:
        md(f"**Takeaway:** {t}")

# ================================================================ Title
md("""
# NYC Taxi Trips, March 2019: Demand, Fares and Tipping

**Goal:** understand how taxi demand, fares and tips vary by time, place, taxi type and payment method, and turn that into practical recommendations.

**Data:** `taxis` sample from [seaborn-data](https://github.com/mwaskom/seaborn-data), real NYC Taxi & Limousine Commission trip records (6,433 trips).

**Contents:** 1 Setup · 2 Explore · 3 Clean · 4 Analyse · 5 Key charts · 6 Findings and recommendations
""")

# ================================================================ 1. Setup
md("""
## 1. Dataset and setup

| Column | Meaning | Column | Meaning |
|---|---|---|---|
| `pickup`, `dropoff` | trip start / end time | `tolls` | tolls paid (USD) |
| `passengers` | passenger count | `total` | total charged incl. surcharges |
| `distance` | miles | `color` | `yellow` (street hail) or `green` (outer boroughs) |
| `fare` | metered fare (USD) | `payment` | `credit card` or `cash` |
| `tip` | tip (USD) | `*_zone`, `*_borough` | TLC taxi zone and borough |
""")

code("""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats

# Palette: categorical slots 1-2 from a colour-blind-validated set, plus neutral ink/grid tones.
# Blue = normal / yellow cabs.  Orange = problem, flagged, or green cabs.
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
DIVERGING = LinearSegmentedColormap.from_list("div", [ORANGE, "#f2f2f0", BLUE])

mpl.rcParams.update({
    "figure.dpi": 110, "figure.facecolor": "white", "axes.facecolor": "white",
    "font.size": 10.5, "text.color": INK, "axes.labelcolor": MUTED,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "xtick.color": MUTED, "ytick.color": MUTED, "legend.frameon": False,
})
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")

def style(ax, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.grid(axis=grid, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    return ax

def label_bars(ax, fmt="{:,.0f}", horizontal=False, pad=3, size=9.5):
    # Direct value labels on bars (no grid-reading needed)
    for p in ax.patches:
        if horizontal:
            v = p.get_width()
            if np.isnan(v): continue
            ax.annotate(fmt.format(v), (v, p.get_y() + p.get_height() / 2), xytext=(pad, 0),
                        textcoords="offset points", va="center", fontsize=size, color=INK)
        else:
            v = p.get_height()
            if np.isnan(v): continue
            ax.annotate(fmt.format(v), (p.get_x() + p.get_width() / 2, v), xytext=(0, pad),
                        textcoords="offset points", ha="center", va="bottom", fontsize=size, color=INK)

def headroom(ax, factor=1.15, horizontal=False):
    lo, hi = ax.get_xlim() if horizontal else ax.get_ylim()
    (ax.set_xlim if horizontal else ax.set_ylim)(lo, hi * factor)

LOCAL = "data/taxis.csv"
URL = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/taxis.csv"
raw = pd.read_csv(LOCAL if __import__("os").path.exists(LOCAL) else URL)
print(f"Loaded {raw.shape[0]:,} rows x {raw.shape[1]} columns")
raw.head()
""")

# ================================================================ 2. Explore
md("## 2. Explore the raw data")

code("""
print("Duplicate rows:", raw.duplicated().sum())
pd.DataFrame({"dtype": raw.dtypes.astype(str), "missing": raw.isna().sum(), "unique": raw.nunique()})
""")

code("""
fig, axes = plt.subplots(2, 2, figsize=(11.5, 7))

# Missing values per column
miss = raw.isna().sum().loc[lambda s: s > 0].sort_values()
ax = axes[0, 0]
ax.barh(miss.index, miss.values, color=ORANGE, height=0.6)
label_bars(ax, horizontal=True); headroom(ax, 1.2, True)
ax.set_title("Missing values by column"); ax.set_xlabel(f"Rows missing (of {len(raw):,})"); style(ax, "x")

# Payment method, including the missing ones
pay = raw["payment"].fillna("Missing").value_counts()
ax = axes[0, 1]
ax.barh(pay.index[::-1], pay.values[::-1], height=0.6,
        color=[ORANGE if i == "Missing" else BLUE for i in pay.index[::-1]])
label_bars(ax, horizontal=True); headroom(ax, 1.2, True)
ax.set_title("Payment method"); ax.set_xlabel("Trips"); style(ax, "x")

# Passenger count: zero passengers is not a real trip
pc = raw["passengers"].value_counts().sort_index()
ax = axes[1, 0]
ax.bar(pc.index.astype(str), pc.values, width=0.65, color=[ORANGE if i == 0 else BLUE for i in pc.index])
label_bars(ax); headroom(ax, 1.12)
ax.set_title("Passengers per trip"); ax.set_xlabel("Passengers"); ax.set_ylabel("Trips"); style(ax)

# Pickup borough
bo = raw["pickup_borough"].fillna("Missing").value_counts()
ax = axes[1, 1]
ax.barh(bo.index[::-1], bo.values[::-1], height=0.6, color=[ORANGE if i == "Missing" else BLUE for i in bo.index[::-1]])
label_bars(ax, horizontal=True); headroom(ax, 1.2, True)
ax.set_title("Pickup borough"); ax.set_xlabel("Trips"); style(ax, "x")

fig.legend(handles=[Patch(color=BLUE, label="Valid"), Patch(color=ORANGE, label="Missing or suspicious")],
           loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.02))
plt.tight_layout(rect=(0, 0.03, 1, 1)); plt.show()
""")

code("""
# Hidden problems that describe() cannot reveal
chk = raw.copy()
chk["pickup"] = pd.to_datetime(chk["pickup"]); chk["dropoff"] = pd.to_datetime(chk["dropoff"])
chk["duration_min"] = (chk["dropoff"] - chk["pickup"]).dt.total_seconds() / 60
extras = chk["total"] - chk["fare"] - chk["tip"] - chk["tolls"]

issues = pd.Series({
    "Zero passengers": (chk["passengers"] == 0).sum(),
    "Zero distance": (chk["distance"] == 0).sum(),
    "Zero or negative duration": (chk["duration_min"] <= 0).sum(),
    "Pickup before 1 March": (chk["pickup"] < "2019-03-01").sum(),
    "Total below fare+tip+tolls": (extras < 0).sum(),
}).sort_values()

fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.8), gridspec_kw={"width_ratios": [1.3, 1]})
ax = axes[0]
ax.barh(issues.index, issues.values, color=ORANGE, height=0.6)
label_bars(ax, horizontal=True); headroom(ax, 1.15, True)
ax.set_title("Impossible or suspicious records"); ax.set_xlabel("Rows"); style(ax, "x")

tip_by_pay = chk.groupby("payment")["tip"].mean()
ax = axes[1]
ax.bar(tip_by_pay.index.str.title(), tip_by_pay.values, color=[ORANGE, BLUE], width=0.55)
label_bars(ax, fmt="${:.2f}"); headroom(ax, 1.2)
ax.set_title("Average tip by payment method"); ax.set_ylabel("USD")
ax.text(0, 0.55, "Cash tips are\\nnever recorded", ha="center", va="bottom", color=INK, fontsize=9.5)
style(ax)
plt.tight_layout(); plt.show()
""")

md("""
**Found:** 44 payments and ~45 zones missing, 96 zero-passenger trips, 51 zero-distance trips, 6 zero-length trips. Cash tips are *not recorded* (not zero), so **tipping can only be analysed for card trips**.
""")

# ================================================================ 3. Clean
md("## 3. Clean and preprocess")

code("""
df = raw.copy()
log = []

def record(step, rows, action):
    log.append({"step": step, "rows_affected": int(rows), "action": action})

# Types
df["pickup"] = pd.to_datetime(df["pickup"])
df["dropoff"] = pd.to_datetime(df["dropoff"])
record("Convert pickup/dropoff to datetime", len(df), "Type conversion")

# Duplicates
n_dup = df.duplicated().sum()
df = df.drop_duplicates()
record("Duplicate records", n_dup, "Dropped (none found)")

# Missing values: money fields are complete; gaps are labels, so rows are kept and labelled
for col in ["payment", "pickup_zone", "dropoff_zone", "pickup_borough", "dropoff_borough"]:
    n = df[col].isna().sum()
    df[col] = df[col].fillna("Unknown")
    record(f"Missing {col}", n, "Filled with 'Unknown' (row kept)")
for col in ["color", "payment", "pickup_borough", "dropoff_borough"]:
    df[col] = df[col].astype("category")

# Derived fields
df["duration_min"] = (df["dropoff"] - df["pickup"]).dt.total_seconds() / 60
df["other_charges"] = df["total"] - df["fare"] - df["tip"] - df["tolls"]

# Impossible records
bad_time = df["duration_min"] <= 0
bad_dist = df["distance"] <= 0
record("Zero/negative duration", bad_time.sum(), "Dropped (cannot be a real trip)")
record("Zero distance", bad_dist.sum(), "Dropped (no movement)")
df = df[~(bad_time | bad_dist)].copy()

df["speed_mph"] = df["distance"] / (df["duration_min"] / 60)
fast = df["speed_mph"] > 80
record("Speed over 80 mph", fast.sum(), "Dropped (data-entry error)")
df = df[~fast].copy()

neg_extra = df["other_charges"] < -0.01
record("Total below fare+tip+tolls", neg_extra.sum(), "Checked (none found)")
df = df[~neg_extra].copy()

zero_pass = df["passengers"] == 0
df["passengers"] = df["passengers"].replace(0, np.nan)
record("Zero passengers", zero_pass.sum(), "Set to NaN (trip kept)")

# Analysis features
df["hour"] = df["pickup"].dt.hour
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
df["weekday"] = pd.Categorical(df["pickup"].dt.day_name(), WEEKDAYS, ordered=True)
df["is_weekend"] = df["weekday"].isin(["Saturday", "Sunday"])
df["day_part"] = pd.cut(df["hour"], [-1, 5, 9, 15, 20, 23],
                        labels=["Night 0-5", "Morning 6-9", "Midday 10-15", "Evening 16-20", "Late 21-23"])
df["fare_per_mile"] = df["fare"] / df["distance"]
card = df["payment"] == "credit card"
df["tip_pct"] = np.where(card & (df["fare"] > 0), df["tip"] / df["fare"] * 100, np.nan)  # card trips only

print(f"{len(raw):,} rows before, {len(df):,} after: {len(raw) - len(df)} removed ({(len(raw) - len(df)) / len(raw) * 100:.1f}%)")
""")

code("""
lg = pd.DataFrame(log)
lg = lg[~lg["step"].str.startswith("Convert")].copy()
lg["removed"] = lg["action"].str.startswith("Dropped") & (lg["rows_affected"] > 0)
lg = lg.sort_values("rows_affected")

fig, ax = plt.subplots(figsize=(11, 4.6))
ax.barh(lg["step"], lg["rows_affected"], height=0.6, color=[ORANGE if r else BLUE for r in lg["removed"]])
label_bars(ax, horizontal=True); headroom(ax, 1.12, True)
ax.set_xlabel("Rows affected (steps overlap, so they do not add up to the rows removed)")
ax.set_title("What cleaning changed")
ax.legend(handles=[Patch(color=ORANGE, label="Rows removed"), Patch(color=BLUE, label="Fixed or checked, rows kept")],
          loc="lower right")
style(ax, "x"); plt.tight_layout(); plt.show()
""")

md("### Outliers: investigate before removing")

code("""
for col in ["fare", "distance", "tip", "duration_min"]:
    q1, q3 = df[col].quantile([0.25, 0.75])
    df[f"out_{col}"] = df[col] > q3 + 1.5 * (q3 - q1)   # IQR fence

specs = [("fare", "Fare ($)"), ("distance", "Distance (miles)"), ("tip", "Tip ($)"), ("duration_min", "Duration (min)")]
fig, axes = plt.subplots(2, 4, figsize=(12, 5.6))
for j, (col, lab) in enumerate(specs):
    ax = axes[0, j]
    ax.boxplot(df[col], vert=False, widths=0.5, patch_artist=True,
               boxprops=dict(facecolor=BLUE, alpha=0.35, edgecolor=BLUE), medianprops=dict(color=INK, lw=1.6),
               whiskerprops=dict(color=MUTED), capprops=dict(color=MUTED),
               flierprops=dict(marker="o", markersize=2.5, markerfacecolor=ORANGE, markeredgecolor="none", alpha=0.6))
    n_out = int(df[f"out_{col}"].sum())
    ax.set_title(f"{lab}\\n{n_out} outliers ({n_out / len(df) * 100:.0f}%)", fontsize=10.5)
    ax.set_yticks([]); style(ax, "x")
    ax = axes[1, j]
    ax.hist(np.log1p(df[col]), bins=30, color=BLUE, edgecolor="white", linewidth=0.5)
    ax.set_xlabel(f"log(1 + {lab.split(' (')[0].lower()})")
    ax.set_title(f"skew {df[col].skew():.1f} to {np.log1p(df[col]).skew():.1f}", fontsize=10,
                 color=MUTED, fontweight="normal"); style(ax)
axes[0, 0].set_ylabel("Raw values"); axes[1, 0].set_ylabel("After log transform")
plt.tight_layout(); plt.show()
""")

code("""
# Are the extreme fares real?  The odd $52 spike, and normal vs outlier fares compared
flat = df[df["fare"] == 52]
touches_jfk = flat["pickup_zone"].str.contains("JFK") | flat["dropoff_zone"].str.contains("JFK")
cmp = df.groupby("out_fare")[["distance", "fare_per_mile"]].median()

fig, axes = plt.subplots(1, 3, figsize=(12, 3.9), gridspec_kw={"width_ratios": [1.7, 1, 1]})
ax = axes[0]
bins = np.arange(0, 82, 2)
heights, edges, patches = ax.hist(df["fare"].clip(upper=80), bins=bins, color=BLUE, edgecolor="white", linewidth=0.6)
k = int(np.where(edges == 52)[0][0])
patches[k].set_facecolor(ORANGE)
ax.annotate(f"$52 flat fare\\n{len(flat)} trips, {touches_jfk.mean() * 100:.0f}% touch JFK", (53, heights[k]),
            xytext=(58, heights.max() * 0.4), color=INK, arrowprops=dict(arrowstyle="-", color=MUTED))
ax.set_xlabel("Fare (USD, capped at 80)"); ax.set_ylabel("Trips"); ax.set_title("The spike at $52"); style(ax)

for ax, col, title, fmt in [(axes[1], "distance", "Median distance (miles)", "{:.1f}"),
                            (axes[2], "fare_per_mile", "Median fare per mile ($)", "${:.2f}")]:
    ax.bar(["Normal", "Outlier"], cmp[col].values, color=[BLUE, ORANGE], width=0.55)
    label_bars(ax, fmt=fmt); headroom(ax, 1.15)
    ax.set_title(title); style(ax)
fig.text(0.01, -0.02, "Outlier fares are long trips that cost less per mile, so they are genuine trips (airport and long-haul), not errors. They are kept.",
         color=MUTED, fontsize=9.5)
plt.tight_layout(); plt.show()
""")

# ================================================================ 4. Analyse
md("## 4. Exploratory analysis")

code("""
df[["passengers", "distance", "duration_min", "fare", "tip", "tolls", "total", "fare_per_mile", "speed_mph"]].describe().T
""")

md("### 4.1 Who rides?")

code("""
known = df[df["payment"] != "Unknown"]

fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
ax = axes[0]
bor = (df["pickup_borough"].astype(str).value_counts(normalize=True) * 100).drop("Unknown", errors="ignore")
ax.barh(bor.index[::-1], bor.values[::-1], color=BLUE, height=0.6)
label_bars(ax, fmt="{:.0f}%", horizontal=True); headroom(ax, 1.2, True)
ax.set_title("Pickup borough"); ax.set_xlabel("% of trips"); style(ax, "x")

ax = axes[1]
ps = (df["passengers"].value_counts(normalize=True).sort_index() * 100)
ax.bar(ps.index.astype(int).astype(str), ps.values, color=BLUE, width=0.65)
label_bars(ax, fmt="{:.0f}%"); headroom(ax, 1.15)
ax.set_title("Passengers per trip"); ax.set_xlabel("Passengers"); ax.set_ylabel("% of trips"); style(ax)

ax = axes[2]
col_share = df["color"].value_counts(normalize=True).mul(100).reindex(["yellow", "green"])
ax.bar(["Yellow cab", "Green cab"], col_share.values, color=[BLUE, ORANGE], width=0.55)
label_bars(ax, fmt="{:.0f}%"); headroom(ax, 1.15)
ax.set_title("Taxi type"); ax.set_ylabel("% of trips"); style(ax)
plt.tight_layout(); plt.show()
""")
takeaway("who")

md("### 4.2 Where do trips go?")

code("""
zones = df.loc[df["pickup_zone"] != "Unknown", "pickup_zone"].value_counts().head(10)[::-1]
routes = (df[(df["pickup_zone"] != "Unknown") & (df["dropoff_zone"] != "Unknown")]
          .assign(route=lambda d: d["pickup_zone"] + " to " + d["dropoff_zone"])["route"].value_counts().head(8)[::-1])
same = (df["pickup_borough"].astype(str) == df["dropoff_borough"].astype(str)).mean() * 100

fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1.25]})
ax = axes[0]
ax.barh(zones.index, zones.values, color=BLUE, height=0.65)
label_bars(ax, horizontal=True); headroom(ax, 1.15, True)
ax.set_title("Top 10 pickup zones"); ax.set_xlabel("Trips"); style(ax, "x")
ax = axes[1]
ax.barh(routes.index, routes.values, color=BLUE, height=0.65)
label_bars(ax, horizontal=True); headroom(ax, 1.15, True)
ax.set_title("Top 8 routes"); ax.set_xlabel("Trips"); style(ax, "x")
plt.tight_layout(); plt.show()
print(f"{same:.0f}% of trips start and end in the same borough")
""")
takeaway("where")

code("""
by_borough = (df[df["pickup_borough"] != "Unknown"].groupby("pickup_borough", observed=True)
              .agg(trips=("fare", "size"), median_distance=("distance", "median"),
                   median_fare=("fare", "median"), median_fare_per_mile=("fare_per_mile", "median"))
              .sort_values("median_fare"))

fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
for ax, col, title, fmt in [(axes[0], "median_distance", "Median distance (miles)", "{:.1f}"),
                            (axes[1], "median_fare", "Median fare ($)", "${:.2f}"),
                            (axes[2], "median_fare_per_mile", "Median fare per mile ($)", "${:.2f}")]:
    ax.barh(by_borough.index, by_borough[col], color=BLUE, height=0.6)
    label_bars(ax, fmt=fmt, horizontal=True); headroom(ax, 1.22, True)
    ax.set_title(title); style(ax, "x")
plt.tight_layout(); plt.show()
""")
takeaway("borough")

md("### 4.3 When do trips happen?")

code("""
dd = df[df["pickup"] >= "2019-03-01"]
per_day = dd.groupby(dd["pickup"].dt.normalize()).size().rename("n").reset_index()
per_day["weekday"] = pd.Categorical(per_day["pickup"].dt.day_name(), WEEKDAYS, ordered=True)
avg_day = per_day.groupby("weekday", observed=True)["n"].mean()
speed_hr = df.groupby("hour")["speed_mph"].median()
part = df["day_part"].value_counts().sort_index()

fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.9))
ax = axes[0]
ax.bar([d[:3] for d in avg_day.index], avg_day.values, color=BLUE, width=0.65)
label_bars(ax); headroom(ax, 1.15)
ax.set_title("Average trips per day"); ax.set_ylabel("Trips (sample)"); style(ax)

ax = axes[1]
ax.plot(speed_hr.index, speed_hr.values, color=BLUE, linewidth=2)
for h, va in [(speed_hr.idxmax(), "bottom"), (speed_hr.idxmin(), "top")]:
    ax.scatter([h], [speed_hr[h]], s=40, color=BLUE, edgecolor="white", linewidth=1.5, zorder=3)
    ax.annotate(f"{speed_hr[h]:.0f} mph at {h}:00", (h, speed_hr[h]), xytext=(0, 9 if va == "bottom" else -12),
                textcoords="offset points", ha="center", va=va, fontsize=9.5)
ax.set_ylim(0, speed_hr.max() * 1.25); ax.set_xticks(range(0, 24, 4))
ax.set_title("Median speed by hour"); ax.set_xlabel("Pickup hour"); ax.set_ylabel("mph"); style(ax)

ax = axes[2]
ax.barh(part.index[::-1], part.values[::-1], color=BLUE, height=0.6)
label_bars(ax, horizontal=True); headroom(ax, 1.18, True)
ax.set_title("Trips by part of day"); ax.set_xlabel("Trips"); style(ax, "x")
plt.tight_layout(); plt.show()
""")
takeaway("time")

md("### 4.4 Tipping (card payments only)")

code("""
cc = df[(df["payment"] == "credit card") & (df["fare"] > 0)].copy()
cc["dist_band"] = pd.cut(cc["distance"], [0, 1, 2, 5, 10, 100], labels=["<1", "1-2", "2-5", "5-10", "10+"])

def grouped(ax, table, fmt, ylabel=None):
    x = np.arange(len(table.index)); w = 0.38
    ax.bar(x - w / 2 - 0.01, table["yellow"], w, color=BLUE, label="Yellow cab")
    ax.bar(x + w / 2 + 0.01, table["green"], w, color=ORANGE, label="Green cab")
    ax.set_xticks(x); ax.set_xticklabels(table.index)
    label_bars(ax, fmt=fmt, size=9); headroom(ax, 1.15)
    if ylabel: ax.set_ylabel(ylabel)
    style(ax)

fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.1))
rates = cc.groupby("color", observed=True).apply(lambda g: pd.Series({
    "Trips with no tip": (g["tip"] == 0).mean() * 100, "Trips tipping 20%+": (g["tip_pct"] >= 20).mean() * 100})).T
grouped(axes[0], rates, "{:.0f}%", "% of card trips")
axes[0].set_title("Tipping behaviour"); axes[0].legend(loc="upper left", fontsize=9)

by_dist = cc.pivot_table(index="dist_band", columns="color", values="tip_pct", aggfunc="median", observed=True)
grouped(axes[1], by_dist, "{:.0f}", "Median tip, % of fare")
axes[1].set_title("Median tip by distance"); axes[1].set_xlabel("Trip distance (miles)")

by_part = cc.groupby("day_part", observed=True)["tip_pct"].median()
axes[2].bar([p.split()[0] for p in by_part.index], by_part.values, color=BLUE, width=0.6)
label_bars(axes[2], fmt="{:.0f}%"); headroom(axes[2], 1.4); axes[2].set_ylim(0, 40)
axes[2].set_title("Median tip by time of day (all cabs)"); axes[2].set_ylabel("% of fare"); style(axes[2])
plt.tight_layout(); plt.show()
""")
takeaway("tip")

md("### 4.5 What moves with what?")

code("""
slope, intercept = np.polyfit(df["distance"], df["fare"], 1)
r2 = np.corrcoef(df["distance"], df["fare"])[0, 1] ** 2
print(f"Fare = ${intercept:.2f} + ${slope:.2f} per mile   (R-squared = {r2:.2f})")

num_cols = ["distance", "duration_min", "fare", "tip", "tolls", "total", "passengers"]
spearman = df[num_cols].corr(method="spearman")
""")

md("### 4.6 Are the differences statistically real?")

code("""
y = cc.loc[cc["color"] == "yellow", "tip_pct"]; g = cc.loc[cc["color"] == "green", "tip_pct"]
p1 = stats.mannwhitneyu(y, g).pvalue

ct = pd.crosstab(known["color"], known["payment"])
chi2, p2, _, _ = stats.chi2_contingency(ct)
cramers_v = np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1)))

rho, p3 = stats.spearmanr(cc["distance"], cc["tip_pct"])

wd = df.loc[~df["is_weekend"], "fare"]; we = df.loc[df["is_weekend"], "fare"]
p4 = stats.mannwhitneyu(wd, we).pvalue

groups = [grp["fare"].values for _, grp in df[df["pickup_borough"] != "Unknown"].groupby("pickup_borough", observed=True)]
h_stat, p5 = stats.kruskal(*groups)

tests = pd.DataFrame([
    ("Fare differs by borough", f"H = {h_stat:.0f}", p5),
    ("Tip % differs, yellow vs green", f"median {y.median():.0f}% vs {g.median():.0f}%", p1),
    ("Tip % falls with distance", f"rho = {rho:.2f}", p3),
    ("Payment mix differs, yellow vs green", f"Cramer's V = {cramers_v:.2f}", p2),
    ("Fare differs, weekday vs weekend", f"median {wd.median():.2f} vs {we.median():.2f} USD", p4),
], columns=["test", "effect", "p"])
tests["strength"] = np.minimum(-np.log10(tests["p"]), 60)

fig, ax = plt.subplots(figsize=(11, 3.9))
ypos = np.arange(len(tests))
ax.barh(ypos, tests["strength"], color=BLUE, height=0.55)
ax.axvline(-np.log10(0.05), color=ORANGE, linewidth=1.8, linestyle="--")
ax.annotate("p = 0.05", (-np.log10(0.05), len(tests) - 0.45), xytext=(5, 0), textcoords="offset points", color=ORANGE, fontsize=9.5)
ax.set_yticks(ypos); ax.set_yticklabels([f"{t}\\n{e}" for t, e in zip(tests["test"], tests["effect"])], fontsize=10)
for i, p in enumerate(tests["p"]):
    ax.annotate("p < 1e-60" if p < 1e-60 else f"p = {p:.1e}", (tests["strength"][i], i), xytext=(5, 0),
                textcoords="offset points", va="center", fontsize=9.5)
ax.set_xlim(0, 72); ax.invert_yaxis()
ax.set_xlabel("Strength of evidence, -log10(p). Longer bar = stronger. Past the dashed line = statistically significant.")
ax.set_title("All five tests; the weekday vs weekend gap is significant but tiny")
style(ax, "x"); plt.tight_layout(); plt.show()
""")
takeaway("tests")

# ================================================================ 5. Key charts
md("## 5. Key charts")

md("### 5.1 Fares and distances are right-skewed")
code("""
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for ax, col, bins, xlabel in [(axes[0], "fare", np.arange(0, 82, 2), "Fare (USD)"),
                              (axes[1], "distance", np.arange(0, 21, 0.5), "Trip distance (miles)")]:
    ax.hist(df[col].clip(upper=bins[-1]), bins=bins, color=BLUE, edgecolor="white", linewidth=0.6)
    med = df[col].median()
    ax.axvline(med, color=INK, linewidth=1.5, linestyle="--")
    ax.text(med, ax.get_ylim()[1] * 0.95, f"  median {med:.1f}", color=INK, va="top", fontsize=10)
    ax.set_xlabel(xlabel); ax.set_ylabel("Trips"); style(ax)
axes[0].set_title("Most fares are small, with a long tail")
axes[1].set_title("Most trips are short")
plt.tight_layout(); plt.show()
""")
takeaway("hist")

md("### 5.2 Demand by hour")
code("""
fig, ax = plt.subplots(figsize=(11, 4))
counts = df.groupby("hour").size()
ax.bar(counts.index, counts.values, color=BLUE, width=0.72)
peak = counts.idxmax()
ax.annotate(f"Peak: {peak}:00, {counts.max()} trips", (peak, counts.max()), xytext=(peak - 6.5, counts.max() * 0.98),
            arrowprops=dict(arrowstyle="-", color=MUTED), color=INK)
ax.set_xticks(range(24)); ax.set_xlabel("Pickup hour"); ax.set_ylabel("Trips")
ax.set_title("Demand dips to a low at 4-5 am and builds to an evening peak")
style(ax); plt.tight_layout(); plt.show()
""")
takeaway("hour")

md("### 5.3 Daily trips through March")
code("""
daily = df[df["pickup"] >= "2019-03-01"].groupby(df["pickup"].dt.normalize()).size()
fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(daily.index, daily.values, color=BLUE, linewidth=2)
for d in daily.index[daily.index.dayofweek >= 5]:
    ax.axvspan(d - pd.Timedelta(hours=12), d + pd.Timedelta(hours=12), color=GRID, alpha=0.6, linewidth=0)
top = daily.idxmax()
ax.annotate(f"Busiest day: {top:%a %d %b}, {daily.max()} trips", (top, daily.max()),
            xytext=(10, 8), textcoords="offset points", color=INK)
ax.set_ylabel("Trips per day"); ax.set_ylim(0, daily.max() * 1.15)
ax.set_title("Daily trips in the sample (weekends shaded)")
style(ax); fig.autofmt_xdate(); plt.tight_layout(); plt.show()
""")
takeaway("daily")

md("### 5.4 When to be on the road: weekday x hour")
code("""
pivot = df.pivot_table(index="weekday", columns="hour", values="fare", aggfunc="size", observed=False).fillna(0)
fig, ax = plt.subplots(figsize=(11, 4))
sns.heatmap(pivot, cmap="Blues", linewidths=1, linecolor="white", cbar_kws={"label": "Trips"}, ax=ax)
ax.set_xlabel("Pickup hour"); ax.set_ylabel("")
ax.set_title("Demand by weekday and hour")
plt.tight_layout(); plt.show()
""")
takeaway("heatmap")

md("### 5.5 Fares by pickup borough")
code("""
sub = df[df["pickup_borough"] != "Unknown"].copy()
order = sub.groupby("pickup_borough", observed=True)["fare"].median().sort_values().index.tolist()
fig, ax = plt.subplots(figsize=(11, 4.2))
sns.boxplot(data=sub, y="pickup_borough", x="fare", order=order, color=BLUE, width=0.55, linewidth=1.2,
            fliersize=2.5, flierprops=dict(markerfacecolor=MUTED, markeredgecolor="none", alpha=0.5), ax=ax)
for patch in ax.patches:
    patch.set_alpha(0.85)
ax.set_xlabel("Fare (USD)"); ax.set_ylabel("")
ax.set_title("Fares are lowest in Manhattan and highest for Queens pickups")
style(ax, grid="x"); plt.tight_layout(); plt.show()
""")
takeaway("box")

md("### 5.6 Distance vs fare")
code("""
fig, ax = plt.subplots(figsize=(8.5, 5.5))
for color_name, c in [("yellow", BLUE), ("green", ORANGE)]:
    s = df[df["color"] == color_name]
    ax.scatter(s["distance"], s["fare"], s=14, alpha=0.4, color=c, edgecolor="white", linewidth=0.3,
               label=f"{color_name.title()} cab (n={len(s):,})")
xs = np.linspace(0, df["distance"].max(), 100)
ax.plot(xs, intercept + slope * xs, color=INK, linewidth=2, label=f"Fit: ${intercept:.2f} + ${slope:.2f}/mile")
ax.set_xlabel("Trip distance (miles)"); ax.set_ylabel("Fare (USD)")
ax.set_title("Fare grows almost linearly with distance")
ax.legend(loc="upper left"); style(ax, grid="both"); plt.tight_layout(); plt.show()
""")
takeaway("scatter")

md("### 5.7 Payment method and tipping")
code("""
fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [1, 1.1]})

share = (pd.crosstab(known["color"], known["payment"], normalize="index") * 100).loc[["green", "yellow"]]
ax = axes[0]
left = np.zeros(len(share))
for pay, c, tc in [("credit card", BLUE, "white"), ("cash", ORANGE, INK)]:
    ax.barh(share.index, share[pay], left=left, color=c, edgecolor="white", linewidth=2, height=0.55, label=pay.title())
    for i, v in enumerate(share[pay]):
        ax.text(left[i] + v / 2, i, f"{v:.0f}%", ha="center", va="center", color=tc, fontweight="bold")
    left += share[pay].values
ax.set_yticks(range(len(share))); ax.set_yticklabels([f"{c.title()} cab" for c in share.index])
ax.set_xlim(0, 100); ax.set_xlabel("% of trips")
ax.set_title("Green cabs take far more cash")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
style(ax, grid="x")

ax = axes[1]
bins = np.arange(0, 62, 2)
for color_name, c in [("yellow", BLUE), ("green", ORANGE)]:
    vals = cc.loc[cc["color"] == color_name, "tip_pct"].clip(upper=60)
    ax.hist(vals, bins=bins, density=True, histtype="step", linewidth=2, color=c,
            label=f"{color_name.title()} (median {vals.median():.0f}%)")
ax.set_xlabel("Tip as % of fare (card trips)"); ax.set_ylabel("Density")
ax.set_title("Yellow tips cluster at 20-30%; green often record none")
ax.legend(); style(ax)
plt.tight_layout(); plt.show()
""")
takeaway("payment")

md("### 5.8 Correlations")
code("""
fig, ax = plt.subplots(figsize=(7.5, 6))
sns.heatmap(spearman, annot=True, fmt=".2f", cmap=DIVERGING, vmin=-1, vmax=1, center=0,
            linewidths=2, linecolor="white", square=True, cbar_kws={"label": "Spearman correlation", "shrink": 0.8}, ax=ax)
ax.set_title("Distance, duration and fare move together; passengers are unrelated")
plt.tight_layout(); plt.show()
""")
takeaway("corr")

md("### 5.9 Fare per mile by trip length")
code("""
band = pd.cut(df["distance"], [0, 1, 2, 3, 5, 10, 100], labels=["<1", "1-2", "2-3", "3-5", "5-10", "10+"])
fpm = df.groupby(band, observed=True)["fare_per_mile"].median()
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(fpm.index.astype(str), fpm.values, color=BLUE, width=0.65)
label_bars(ax, fmt="${:.1f}"); headroom(ax, 1.1)
ax.set_xlabel("Trip distance band (miles)"); ax.set_ylabel("Median fare per mile (USD)")
ax.set_title("The base fare makes short trips cost more per mile")
style(ax); plt.tight_layout(); plt.show()
""")
takeaway("fpm")

# ================================================================ 6. Findings
md("## 6. Findings and recommendations")

code("""
tiles = [
    ("Trips analysed", f"{len(df):,}"),
    ("Median fare", f"${df['fare'].median():.2f}"),
    ("Typical trip", f"{df['distance'].median():.1f} mi, {df['duration_min'].median():.0f} min"),
    ("Pickups in Manhattan", f"{(df['pickup_borough'] == 'Manhattan').mean() * 100:.0f}%"),
    ("Peak hour", f"{counts.idxmax()}:00"),
    ("Fare explained by distance", f"{r2 * 100:.0f}%"),
    ("Trips paid in cash", f"{(known['payment'] == 'cash').mean() * 100:.0f}%"),
    ("Median card tip", f"{cc['tip_pct'].median():.0f}%"),
]
fig, axes = plt.subplots(2, 4, figsize=(12, 3.9))
for ax, (label, value) in zip(axes.ravel(), tiles):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.add_patch(plt.Rectangle((0.02, 0.04), 0.96, 0.92, transform=ax.transAxes, facecolor="#f3f3f0", edgecolor="none"))
    ax.text(0.5, 0.58, value, ha="center", va="center", fontsize=21, fontweight="bold", color=INK)
    ax.text(0.5, 0.22, label, ha="center", va="center", fontsize=10.5, color=MUTED)
plt.tight_layout(); plt.show()
""")

md(INSIGHTS)

md("""
## Appendix: method and limits

- **Tools:** Pandas and NumPy for wrangling, SciPy for tests, Matplotlib and Seaborn for charts. Cleaned data: `output/taxis_clean.csv`.
- **One month, ~6,400 trips:** patterns and ratios travel better than totals.
- **Association is not cause**, and cash tips are not recorded, so tip findings cover card payments only.
""")

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                  "language_info": {"name": "python"}}
out = HERE / "NYC_Taxi_Analysis.ipynb"
nbf.write(nb, out)
print("wrote", out)
