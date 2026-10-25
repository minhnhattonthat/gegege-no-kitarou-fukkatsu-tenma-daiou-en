# Translation reviewer brief - Gegege no Kitarou: Fukkatsu! Tenma Daiou

You review a JP->English fan translation. Read-only: no edits, no git, no subagents. Mechanical validity (ids,
alien tokens, glyphs, width, glossary terms) is already enforced by `tools/tl.py check` - judge translation quality.
Return the report as your final message: subagents cannot write files, so the controller saves it.

## Inputs (paths in your dispatch)
- Pairs file (`tools/tl.py pairs`): every entry as `>> id | scene | notes`, `JP:`, `EN:` in play order. Read ALL of it.
  Caption pages (20_NNN) are wrapped by tool, so ignore line breaks; ` / ` separates lines of the intro letter
  (20_001, one English line per Japanese line) and items of a graphics label (G*).
- `glossary.md` (rulings and style rules at the top), `docs/synopsis.md` (plot and the speaker of every page).

## Judge
- Accuracy: mistranslation, omission, addition, wrong speaker or addressee, reversed meaning. Quote the JP and say
  what it means.
- Consistency: glossary names/terms exactly; honorifics (Kitaro-san, Yumeko-chan) stable; voices as in the glossary.
- Things players caught that reviewers missed: jokes/wordplay losing their punch; abbreviated names or terms;
  stock phrases that read awkwardly in English.
- Naturalness: would a fan-translation reader stumble?
- Staff-roll name readings are known guesses (labels.json notes); flag only a clearly wrong reading.
- `{alienN}` tokens are an invented alien script kept as drawn; do not ask to translate them.

## Report
### Issues
#### Critical (meaning reversed, wrong speaker)
#### Important (clear mistranslation, glossary inconsistency, abbreviation)
#### Minor (style - deferred to one polish pass)
Each: `id - JP gist - problem - suggested EN`.
### Assessment
Approved | Needs fixes - one sentence why.
