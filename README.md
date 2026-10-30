# GeGeGe no Kitarou: Fukkatsu! Tenma Daiou English translation

Unofficial English fan translation of **GeGeGe no Kitarou: Fukkatsu! Tenma Daiou** (Super Famicom, Bandai, 1993): the source text and tools
that build the patch.

**Just want to play?** Download the patch from [Releases](../../releases) and follow its README. This repository holds
no game data you can play; you need your own dump of the Japanese game.

**Found a bug?** [Report it](../../issues/new/choose): untranslated text, typos, overflow, crashes. Attaching a savestate
helps most.

## Translation status

| Part | Status |
|---|---|
| Cutscene captions and the intro letter | Translated |
| In-stage dialogue | Translated |
| Title screen, menus, options, partner select, game over | Translated (title logo romanised: "GeGeGe no Kitaro" / "Fukkatsu! Tenma Daio") |
| Chapter cards, boss names, HUD icon, city signs | Translated (the invented alien script on two boss names and two captions is kept as drawn, as in the original) |
| Staff roll | Translated (name readings are best guesses; corrections welcome) |

Known issues: none known; [report one](../../issues/new/choose).

## What's here

| Path | What it is |
|---|---|
| `script/` | Every text block: original Japanese and English. Translation fixes go here. |
| `glossary.md` | Binding names, terms and style rules. |
| `tools/` | Python build chain: extract, insert, lint, release. |
| `tests/` | pytest suite (ROM-dependent tests skip when the ROM is absent). |
| `docs/re/` | Reverse-engineering notes. |
| `docs/decisions.md`, `docs/status.md` | Rulings with their reasons; current progress and open bugs. |
| `docs/fonts.md` | Fonts used and their licences. |
| `AGENTS.md` | Instructions for coding agents (`CLAUDE.md` points to it). |
| `.claude/agents/` | Subagent types (translator, reviewer, visual QA, playtester) with only the tools each needs. |

## Build your own patched ROM

Needs Python 3.12+ and your own dump of the Japanese game.

```sh
git clone https://github.com/minhnhattonthat/gegege-no-kitarou-fukkatsu-tenma-daiou-en
cd gegege-no-kitarou-fukkatsu-tenma-daiou-en
# copy your dump to: rom/kitarou.sfc
#   (No-Intro "Gegege no Kitarou - Fukkatsu! Tenma Daiou (Japan).sfc", 1048576 bytes,
#    SHA-1 0451530f6acb855583192d6257182b8d99ec9aa5; the build refuses any other dump, see rom.sha1)
python -X utf8 tools/build.py                          # -> build/kitarou_en.sfc
python -X utf8 tools/check.py                          # tests + text lint
```

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)

## Licence

Tools and English translation: MIT. The original Japanese text in `script/` is Bandai's and is included only so
the translation can be checked against it. GeGeGe no Kitarou is (c) Mizuki Pro / Toei Animation and the game (c)
Bandai; this project is not affiliated with them.
Do not share patched ROMs.

The translation was made with extensive AI assistance (Claude by Anthropic). Corrections are very welcome.
