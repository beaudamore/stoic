# Stoic LoRA: Augmentation Roadmap

Findings and recommended changes from the 2026-08-24 corpus audit. Ordered by impact per
unit of effort, not by how interesting they are.

Two kinds of change appear below and they cost very different amounts:

- **Source-data changes** touch `data/source-clean/` or the generated JSONL directly. Some
  are free; adding new source text requires a **datagen regeneration** — the OpenRouter
  API stage in `notebooks/datagen/`, which is where the money and hours go. Training
  itself is cheap by comparison.
- **Notebook changes** alter how future data is generated and do nothing to the JSONL
  already on disk.

---

## 1. Seneca is missing his most important work — fix this first

**This is the single highest-impact item in this document.**

Seneca accounts for roughly 70% of the Stoic training data. The *Epistulae Morales*
(Letters to Lucilius) — his 124 letters, the most quoted and most voice-defining Stoic
prose in existence — are **not in the corpus**.

Evidence: zero `LETTER`/`EPISTLE` section headers across every file in
`data/source-clean/Seneca, Lucius Annaeus/`, and only 22 scattered mentions of
"Lucilius", his own addressee.

Meanwhile, of the 3.4 MB in that folder:

| File | Size | Issue |
|---|---|---|
| The Tragedies of Seneca | 745K | Verse drama. Senecan tragedy is bombastic dramatic verse — a completely different register from the epistolary philosophy the persona is meant to speak in. |
| Octavia Praetexta + A Translation of Octavia | 222K | **Pseudo-Seneca.** Near-universally judged not his — it depicts his own death. Also duplicated across two files. |
| Two Tragedies (Medea, Daughters of Troy) | 116K | More drama, and probably duplicates content already inside the 745K tragedies file. |
| Between Heathenism and Christianity | 56K | A 19th-century scholarly monograph **about** Seneca. Not by him at all. |

That is roughly **33% of the Seneca corpus** as drama, pseudepigrapha, and secondary
literature. *On Benefits* also appears in two separate files.

So the persona is currently learning partly from verse tragedy and a Victorian academic,
while the prose that actually defines his voice is absent.

**Recommended:**

1. Add the *Epistulae Morales* — Richard Gummere's Loeb translation (1917–25) is public
   domain and available from Project Gutenberg.
2. Remove the tragedies, both Octavia files, and *Between Heathenism and Christianity*.
3. De-duplicate *On Benefits*.
4. Regenerate the Seneca portion of the corpus.

Expected effect: the Seneca voice becomes recognisably the Seneca people quote —
letters, practical counsel, the direct address to a friend — instead of a blend of
philosophy, tragedy, and commentary.

---

## 2. Epicurus removed (done, 2026-08-24)

Epicurus was removed from the corpus. He founded the Garden, the Stoics' principal rival
school: pleasure rightly understood as the goal of life, against the Stoic claim that
virtue alone suffices. Including him in a *Stoic personas* model taught precisely the
school-blending that the DPO `voice_drift` rejections exist to punish.

He was also far too thin to learn a voice from — 111 of 25,232 SFT rows (0.4%) and 9 of
1,800 DPO pairs.

Removal used `data/scripts/remove_persona.py`, which filters by **speaker**, never by
substring. That distinction is the whole job: Seneca quotes Epicurus constantly, and a
naive text filter would have deleted **1,612 rows of authentic Seneca**. The script reads
the DPO `persona` field or parses `"You are <Name>,"` from the system prompt.

```
rows removed (spoken by epicurus):        481
rows PRESERVED that merely mention him: 1,612
```

Originals are preserved under `data/training-data/stoic_persona/_removed_epicurus_*/`
with a manifest. Re-adding him means uncommenting one line in `PERSONA_FOLDERS` in
`notebooks/datagen/stoic_datagen_sft.ipynb` — his `PERSONA_METADATA` and `OPENER_CUES` entries are still
there but inert.

Corpus after removal, and now naturally balanced:

```
seneca           17,704      a 3000-row cap now yields a clean 1000/1000/1000
epictetus         4,193
marcus_aurelius   3,224
```

---

## 3. Machiavelli stays excluded

His corpus is in `source-clean/` (3.1 MB) and he is deliberately not a persona. He is not
a Stoic and is opposed to Stoicism on its central claim: his *virtù* is not moral virtue
but effective capacity, and it exists to **master** fortuna rather than accept it as
indifferent. *The Prince* ch. 15 says a ruler must "learn how not to be good."

The Roman-republican material and the Livy commentary are probably why the corpus was
collected alongside the Stoics. Aesthetic adjacency, philosophical opposition.

The exclusion is documented in `PERSONA_FOLDERS` in `notebooks/datagen/stoic_datagen_sft.ipynb`.

---

## 4. Recommended new speaker: Musonius Rufus

The clearest addition. Epictetus's own teacher, unambiguously Stoic, with a genuine
surviving corpus (*Lectures and Fragments*).

He fills a gap none of the current three cover: practical, almost blue-collar Stoicism —
on food, clothing, furniture, exile, manual labour, and famously the argument that women
should study philosophy on the same terms as men. In a speaking circle he is the one who
gives concrete instruction where Marcus is introspective and Seneca is rhetorical.

Distinct voice, real corpus, no school-mixing problem.

**Smaller additions:**

- **Hierocles** — *Elements of Ethics* fragments. His "concentric circles" of belonging
  is thematically ideal for a circle-of-speakers product.
- **Cleanthes** — only the *Hymn to Zeus* survives intact. Too small for a LoRA; better
  used as a quotation source inside another persona's prompt.

**Deliberately not recommended:**

- **Zeno and Chrysippus** — survive only as fragments quoted by others. Training on them
  means training on Diogenes Laërtius's voice, not theirs.
- **Cicero** — *De Officiis* transmits Stoic ethics faithfully, but Cicero was an
  Academic skeptic. This is the Epicurus problem again in a more tempting form.
- **Cato the Younger** — left no writings. Everything attributed to him is other people
  depicting him.

---

## Priority order

1. Fix the Seneca corpus (§1) — biggest quality win, and the diagnosis is already done.
2. Add Musonius Rufus (§4) — new voice, clean fit.
3. Hierocles, if a fourth practical voice is wanted.

Items 1 and 2 both require a datagen regeneration, so they should be batched into a
single run rather than done separately.

See also: `../../docs/datagen_notebook_guidelines.md` for the sentence-aware chunking
standard, and `../../docs/multimodal_and_hybrid_base_models.md` for LoRA scoping on the
Qwen3.8 base.
