# Freeze and submit

**STATUS 2026-09-28:** frozen at CUTOFF 2026-09-20 (72 pricing days, store read 2026-09-28T04:57:57Z).
`reproduce.py` reports 0 MISMATCH; the abstract is 491 words on the strict count. The abstract now
cites this repository, so step 5 (publish) must happen BEFORE step 6 (submit). The private checker
`nhl-betting/reproduce.py` no longer reads the live store: it runs this repo's `reproduce.py` and also
fails if any frozen figure is missing from the abstract text.

Everything below is mechanical. Budget 20 minutes.

## What the portal actually requires (checked 30 Aug 2026)

Two stages, and they ask for different things:

| stage | due | what is submitted |
|---|---|---|
| Abstract | **1 Oct 2026, 11:59pm EST** | abstract only — under 500 words *including the title*, up to two tables/figures combined, sections Introduction / Methods / Results / Conclusion |
| Full manuscript | **4 Dec 2026** (only if invited) | the paper, **plus a link to a public repository containing the data** |

Announcements: finalists and posters late January 2027; conference 25–26 February 2027.

Three things this changes:

1. **The repository is a Dec 4 requirement, not an Oct 1 one.** Publishing on 20 September is
   entirely safe — the repo is not part of the abstract submission. It is ready early, not late.
2. **The repo is mandatory if invited**, so it is not optional work: *"All papers will be required to
   submit a link to the team's GitHub repository, or another open-source repository, with the data
   used to conduct the research."* Code is encouraged but not required — we ship it anyway, because
   reproducibility is one of the four judging criteria.
3. **Review is blinded at the final stage**: *"Final reviews will occur without knowledge of the
   names of the authors."* See the December section at the bottom — it does not affect September.

Judging criteria, verbatim: **novelty of research, academic rigor / validity of model,
reproducibility, application**. Finalists are additionally judged on interest / impact.

### Word count — already compliant

The limit counts the title. Measured on `SSAC_ABSTRACT_final.md`:

* **491 words** counting the results table (2026-09-28 refreeze)
* **440 words** not counting it (the table falls under the separate two-tables-or-figures allowance)

Re-measured after the 2026-09-20 refreeze: **491 with the table, 440 without.** Re-measure after
any edit with the command in Step 3; it is the stricter of the two counts.

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
* **the declined share** — 93% at the 09-20 freeze (87% at 08-24). It moved because the gates
  tightened mid-window; that is stated in the README limitations.

## 3. Check the word count

```bash
py -c "import io,re;t=io.open('SSAC_ABSTRACT_final.md',encoding='utf-8').read();w=lambda s:len(re.findall(r'[A-Za-z0-9][^\s]*',s));L=t.splitlines();print('with table   :',w(t));print('without table:',w(chr(10).join(l for l in L if not l.strip().startswith('|'))))"
```

Limit is 500 **including the title**. Judge it on the *with table* number — that is the strict
reading, and it currently sits at 499.

Do not use a bare `\S+` word count here. It counts `#`, `##` and the table's `|` separators as
words and reports 522 on an abstract that is actually compliant — which would send you trimming
good sentences to fix a problem that does not exist. The command above counts only tokens that
start with a letter or digit.

Trim, do not append.

## 4. Sanity pass

```bash
py run_detectors.py | grep -c "\[ALARM\]"   # expect 2. Do NOT check the exit code:
                                             # it is 1 by design AND 1 on a crash

git status              # data/ should show modified CSVs and nothing else
```

Confirm nothing under `data/` carries a real calendar date:

```bash
grep -rIE '(19|20)[0-9]{2}-[0-9]{2}-[0-9]{2}' data/
```

`CUTOFF.txt` is the one intended match — it names the freeze date and nothing else. Any other hit is
a leak; stop and fix it before pushing.

## 5. Publish

The repository does not exist on GitHub yet — this is the step that creates it, and it is the
decision to go public. Under the `ThatOneSharpDude` account:

```bash
gh repo create silent-failure-detectors --public --source=. --remote=origin \
   --description "Three measurement failures on a live betting book, reproduced from the data, plus the detectors that would have caught them"
git add -A
git commit -m "freeze data at 2026-09-20"
git push -u origin main
```

Then verify the public view actually works for someone who is not you:

```bash
cd /tmp && rm -rf sfd-check && git clone https://github.com/ThatOneSharpDude/silent-failure-detectors sfd-check
cd sfd-check && py reproduce.py | grep -c MISMATCH   # expect 0
py run_detectors.py | grep -c "\[ALARM\]"            # expect 2 (exit code cannot tell an alarm from a crash)
```

A clone that cannot reproduce is worse than no repository, and this is the only way to catch a file
that was present locally but never committed.

## 6. Submit the abstract (by 1 Oct)

Paste the abstract into the portal. **The repository URL is not requested at this stage** — it is
required only with the full manuscript on 4 December. Including it anyway is optional; see below
before you do.

## Standing checks before you send

- [ ] `reproduce.py` reports zero mismatches
- [ ] abstract is at or under 500 words
- [ ] no key, token, credential or private filesystem path anywhere in the repo
- [ ] the limitation paragraph still says the instrumentation postdates the system
- [ ] neither ROI figure is described anywhere as evidence of edge

## December, if invited — the blinding question

*"Final reviews will occur without knowledge of the names of the authors."* The 4 December
submission requires a repository link, and this repository currently carries your name in three
places: the README byline, the LICENSE copyright, and every commit's author metadata. Handing a
blinded reviewer a link that names the author defeats the blinding they are trying to maintain.

This does **not** affect September. Decide it in December, when it is actually live.

If you choose to blind it for the review window, all three need doing — the README alone is not
enough, because the account and the commits still identify you:

```bash
sed -i 's/^\*\*Fox Camann\*\*.*/**Author name withheld during blind review.**/' README.md
sed -i 's/Copyright (c) 2026 Fox Camann/Copyright (c) 2026 the author/' LICENSE
```

Commit metadata cannot be edited without rewriting history, so if the commits must be anonymous the
practical route is a fresh repository with a single commit under a neutral identity. Note also that
the `ThatOneSharpDude` profile itself carries your real name — so even a name-free README is only
partial blinding while the repo sits on that account.

Restore afterwards, once decisions are out (late January):

```bash
git revert --no-edit <the-blinding-commit>
```

**The honest read:** the blinding is best-effort, not enforced — the committee asks for a public
repository and public repositories have owners, so they cannot expect perfect anonymity from one.
Your stated preference is that your name is visible because it is the credibility. That is a
defensible position and this section exists so it is a decision you made rather than one you
defaulted into.

## If you skip the refreeze

Submitting the current freeze (2026-08-24) is valid — it is internally consistent and reproduces
cleanly today. The only cost is a shorter window: 45 pricing days instead of roughly 72. Do that
rather than submit a freeze whose paper and data disagree.
