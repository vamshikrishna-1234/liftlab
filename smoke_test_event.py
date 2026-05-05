from liftlab.events import apply_event_targeting, list_events
from liftlab.data import generate_population

df = generate_population(50_000, 42)
print("Events:", list_events())

for ev in ["Super Bowl 2026", "Easter 2026", "None - full population"]:
    name = "None - full population" if "None" in ev else ev
    if name not in list_events():
        name = list_events()[0] if "None" in ev else ev
    df2, info = apply_event_targeting(df, name)
    print(f"\n[{name}] Filtered {info['n_before']:,} -> {info['n_after']:,} "
          f"({info['drop_pct']:.1f}% dropped)")
print("\nOK")
