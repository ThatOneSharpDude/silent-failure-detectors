# Freeze and submit — 20 September 2026

Everything below is mechanical. Budget 20 minutes.

## 1. Refreeze the data (one constant)

In `make_extract.py`, the only line that changes:

```python
CUTOFF = "2026-09-20"
```

Then run it. It reads the private store, so run it with that store present:

```bash
py make_extract.py
```

It prints the row count and the number of pricing days, and rewrites everything in `data/`.

## 2. Update the paper to match

```bash
py reproduce.py
```

Every line marked `MISMATCH` is a figure in the abstract that moved. The `data=` column is the new
truth. Update two places for each one:

* `SSAC_ABSTRACT_final.md` — the printed figure
* `reproduce.py` — the `paper=` argument in the matching `check(...)` call

Re-run until it reports zero mismatches. **Do not submit while any line reads MISMATCH.**

Figures that will move: n, graded, prop rows, the no-close percentages, both ROI numbers, and the
capture-failure count. Two should NOT move:

* **failures where our rung was still quoted** — this is zero, and it is the central claim. If it
  becomes non-zero, something real has changed and the paragraph needs rewriting, not editing.
* **the declined share** — ~87%. A large move here means the gate's behaviour changed mid-window.

## 3. Check the word count

```bash
py -c "import io,re;print(len(re.findall(r'\S+', io.open('SSAC_ABSTRACT_final.md',encoding='utf-8').read())))"
```

Limit is 500. Trim, do not append.

## 4. Sanity pass

```bash
py run_detectors.py     # expect exit 1 with two ALARMs — that is correct
git status              # data/ should show modified CSVs and nothing else
```

Confirm nothing under `data/` carries a real calendar date:

```bash
grep -rIE '(19|20)[0-9]{2}-[0-9]{2}-[0-9]{2}' data/
```

`CUTOFF.txt` is the one intended match — it names the freeze date and nothing else. Any other hit is
a leak; stop and fix it before pushing.

## 5. Push, then submit

```bash
git add -A
git commit -m "freeze data at 2026-09-20 for submission"
git push
```

Then submit the abstract through the portal with the repository URL in the code/data field.

## Standing checks before you send

- [ ] `reproduce.py` reports zero mismatches
- [ ] abstract is at or under 500 words
- [ ] no key, token, credential or private filesystem path anywhere in the repo
- [ ] the limitation paragraph still says the instrumentation postdates the system
- [ ] neither ROI figure is described anywhere as evidence of edge

## If you skip the refreeze

Submitting the current freeze (2026-08-24) is valid — it is internally consistent and reproduces
cleanly today. The only cost is a shorter window: 45 pricing days instead of roughly 72. Do that
rather than submit a freeze whose paper and data disagree.
