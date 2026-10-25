# Gegege no Kitarou: Fukkatsu! Tenma Daiou (SNES) English translation

Skill: translate-retro-game; `python tools/skill.py` prints its folder (`$SKILL` below). Read its SKILL.md before ROM, text or QA work. `"$(python tools/skill.py)"` works in bash and PowerShell; never paste a `plugins/cache/<hash>` path.

## Commands (run from repo root)
- Build:    `python -X utf8 tools/build.py`  -> build/kitarou_en.sfc (checks the dump against `rom.sha1` first)
- Check:    `python -X utf8 tools/check.py`  (tests + lint; the pre-commit hook runs this)
- Smoke:    `python -X utf8 "$(python tools/skill.py)/scripts/emu.py" build/kitarou_en.sfc --out work/qa/smoke --route tools/routes/boot.txt --smoke`
- Warp:     `python -X utf8 "$(python tools/skill.py)/scripts/emu.py" build/kitarou_en.sfc --out work/qa/warp --script tools/debug/warp.lua --var "SCENE='<name>'" --frames 900 --sheet` (scenes: `tools/debug/scenes.md`; never ask the user to play to a scene)
- Tour:     `python -X utf8 tools/debug/tour.py [ROM] [--only a,b]` (every scene, arrival check, sheets, `work/states/<scene>.mss`)
- Release:  `python -X utf8 tools/release.py` (patch + verify; never publish without the user)
- Clean:    `python -X utf8 tools/clean.py` (published projects: lists rebuildable/downloadable files; `--yes` deletes)

## Paths
- Original ROM: `rom/kitarou.sfc` (No-Intro dump renamed; gitignored; SHA-1 in `rom.sha1`, checked by `tools/check_rom.py`). LoROM, 1 MiB, no SRAM. Emulator: this repo's own copy in `tools/mesen/` (MesenCE 2.2.1, https://github.com/nesdev-org/MesenCE/releases/download/2.2.1/Mesen_2.2.1_Windows.zip, `fetch_emu.py mesen`; gitignored; settings in `tools/emu-config/`). Savestates: `work/states/`.
- Text: `script/`. Tables: `tbl/`. Glossary: `glossary.md`. RE notes index: `docs/re/README.md`. Fonts and their licences: `docs/fonts.md`.
- `tools/tbl.py`, `bps.py`, `romdiff.py` are copies from the skill so a clone builds without it.

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts here read and analyse, never `.replace()` and write back.
- Subagents: dispatch the `.claude/agents/` types (translator, reviewer, visual-qa, playtester), never general-purpose: their short tool list cuts each agent's start-up context from ~43k to ~9k tokens.
- The user's decisions, with the options and reasons: `docs/decisions.md`. Read it before asking the user anything; add each new ruling there the same session.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update `docs/status.md`.
- Never run `gh release create`; never change repo visibility. The run ends at a verified release zip in `release/`.

## Status
`docs/status.md`: done, next, open bugs. Update it at the end of every session.
