# Demo recording script — Liftlab (for the YC application)

Total runtime: **~2:30**. Record on Loom (free) at 1080p, mic on, camera bubble in the corner.

> **Before recording** (one-time setup):
> 1. `streamlit run app.py` in PowerShell.
> 2. Open `http://localhost:8501` in Chrome (use a clean profile / incognito so no extensions pollute the screen).
> 3. Bump browser zoom to 110% so text is readable on YC partners' laptops.
> 4. In the sidebar, set: **Campaign name = Spring Grocery Push 2026**, **Population = 100,000**, all channels on, default dates, **Use LLM = OFF** (template is faster and deterministic for recording).
> 5. Quit Slack/notifications, full-screen the browser.

---

## Beat-by-beat script

### Beat 1 (0:00 – 0:15) — Hook
*Camera-on, looking at lens. Browser visible behind you with the Liftlab page loaded.*

> "Hi, I'm Vamshi. For the past few years I've worked inside the CRM team at one of the largest US grocers, running A/B tests and incrementality analyses for marketing campaigns that hit tens of millions of households. Every campaign analysis takes a 4-to-6-person team about two days. **Liftlab does it in seven seconds. Let me show you.**"

### Beat 2 (0:15 – 0:30) — Population
*Switch to full-screen browser.*

> "Step one: I generate a 100,000-household synthetic retail population, with the same attributes a real grocer works with — division, segment, persona, channel opt-ins, pre-period spend baselines."

**Click: "Generate population".**
*(Wait ~1 sec.)*

> "89,000 reachable households, $66 average weekly pre-period spend per HH."

### Beat 3 (0:30 – 0:50) — TVC split
> "Step two: a stratified 90/10 test/control split, balanced across segment, persona, channel mix, division — same approach the major retailers use to make sure their lift signal isn't poisoned by demographic skew."

**Click: "Create TVC split".**

> "80,766 test, 8,973 control. The balance check shows pre-period spend is within tenths of a percent across groups for every segment."

**Expand the balance-check expander; point to the `delta_%` column.**

### Beat 4 (0:50 – 1:15) — Campaign simulation
> "Step three is the campaign itself. In production, this is replaced by your actual delivery and transaction tables from BigQuery or Snowflake. For this demo I simulate a two-week campaign across email, push, and SMS — and I inject a known ground-truth lift on engaged test households so you can see the analysis layer recover it."

**Click: "Run campaign simulation".**

> "118,000 sends across the three channels, 19,000 opens, 2,300 clicks."

### Beat 5 (1:15 – 1:50) — Incrementality analysis
> "Step four: the actual analysis. Lift percentage, incremental net sales and units, p-values via Welch's two-sample t-tests, and segment-level breakdowns across every customer dimension."

**Click: "Analyze campaign".**

*Pause on the metrics row.*

> "**Net sales per household lifted 3.94%, p of point zero zero one one — highly significant. Eight hundred and forty-seven thousand dollars in incremental net sales, with about 135,000 incremental units.**"

**Click the "By segment" tab. Select `persona` from the dropdown.**

> "Now the segment view. Wellness customers responded with an 11.9% lift, p of point zero zero zero one. Family customers were flat — barely above noise. So the segment story is clear: this campaign worked for health-engaged customers, not for the family persona."

**Click "Ops efficiency" tab.**

> "Operational integrity check: 97% of control received nothing — the holdout is clean. 96.8% of test households received the right comm. Both healthy. This is the check that catches broken campaigns before the wrong number ships to a CMO."

### Beat 6 (1:50 – 2:20) — AI summary + Excel
> "Step five: the executive summary, auto-narrated."

**Click: "Generate AI summary".**

*Scroll slowly through the rendered markdown for ~10 seconds.*

> "Headline numbers, channel-by-channel engagement, the best and worst segments with p-values, the operational integrity check, and three recommended next experiments — all generated from the actual analysis output."

**Click: "Download full Excel report".**
**(Open the downloaded file briefly, scroll through the Executive Summary sheet, then the Incrementality sheet.)**

> "Multi-sheet Excel deliverable, ready to drop into the standard report template the brand team uses today."

### Beat 7 (2:20 – 2:30) — Close
*Switch back to camera.*

> "End-to-end pipeline: seven seconds. Same workflow that costs a tier-one retailer $200K of analyst time every year, and that mid-market CPG brands can't afford to run at all. **That's Liftlab.** Thanks."

---

## Things to NOT say in the recording

- Do **not** name your current employer.
- Do **not** show any non-synthetic data.
- Do **not** claim users / customers you don't have.
- Do **not** say "multi-agent framework" — say "warehouse-native agent" or "AI analyst" instead.

## Things to verify before uploading to YC

- [ ] Video is ≤ 3 minutes and ≤ 100 MB (Loom default works).
- [ ] Audio levels are even (test with headphones).
- [ ] Browser tabs in the background don't show personal/employer information.
- [ ] No notifications popped up mid-recording.
- [ ] The footer caption "All numbers shown are from a synthetic data generator" is visible in at least one frame.
