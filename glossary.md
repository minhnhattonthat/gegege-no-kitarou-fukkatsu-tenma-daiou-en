# Glossary - Gegege no Kitarou: Fukkatsu! Tenma Daiou (SNES)

Binding for every translator and reviewer. Agents propose additions in reports; only the controller edits this file.
`tests/test_script.py` enforces the tables: a page whose Japanese holds a JP term (longest match first) must hold
its EN form; an `Avoid` spelling fails anywhere.

## Rulings (asked of the user once; options and reasons in docs/decisions.md)
- Honorifics: kept, hyphenated (Kitaro-san, Yumeko-chan). Name order: Western (Yumeko Tendo).
- Romanisation source: official English (Drawn & Quarterly's Kitaro manga: Kitaro, Medama Oyaji, Nezumi Otoko,
  Neko Musume), else Hepburn without macrons.
- Credits: English (roles translated, names in Hepburn of the most common reading; uncertain ones in labels.json).
- Register: plain, natural English; light Japanese flavour (yokai, honorifics). Sound: "Waaah!", "Heh heh...".
- Abbreviations: none; full names and terms, engine work first (D4).

## Style rules
- Punctuation map: 「」 -> “...” (curly), 『』 -> ‘...’, ・・・ -> ..., ！？ -> ?!, apostrophe ’ (curly).
- A page split mid-sentence (20_029 -> 20_030) keeps the open quote on the first page and the close on the second.
- Alien script tokens {alien1}-{alien4} stay as written (drawn with the original glyphs).
- Voices: Kitaro - polite, earnest, calls Medama Oyaji "Father". Medama Oyaji - old-fashioned elder ("Go now!").
  Nezumi Otoko - sleazy, "Heh heh...". Shisa - polite, calls Kitaro "Kitaro-san". Jigoku Doji - brash young
  hero. Nurarihyon - smug villain. Space yokai - grandiose ("the Great King").

## Characters
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| 鬼太郎 | Kitaro | | | Kitarou |
| 目玉のオヤジ | Medama Oyaji | | Kitaro's eyeball father | Daddy Eyeball |
| とうさん | Father | | Kitaro to Medama Oyaji | |
| ねずみ男 | Nezumi Otoko | | | Rat Man, Ratman |
| 猫娘 | Neko Musume | | | Cat Girl |
| 子泣きじじい | Konaki Jiji | | | |
| 砂かけばばあ | Sunakake Babaa | | | |
| シーサー | Shisa | | Okinawan lion-dog partner | Shiisaa |
| 地獄童子 | Jigoku Doji | | | |
| ユメコ | Yumeko | | 天童ユメコ = Yumeko Tendo | |
| 天童 | Tendo | | | |
| ぬらりひょん | Nurarihyon | | | |
| エンマ大王 | Great King Enma | | judge of the dead | |
| 天魔大王 | Great King Tenma | | final boss, title | |
| 大王 | Great King | | the space yokai's master | |
| たんたん坊 | Tantanbo | | | |
| 白山坊 | Hakusanbo | | | |
| がしゃどくろ | Gashadokuro | | | |
| 山天狗 | Yama-Tengu | | | |
| 見上げ入道 | Miage-Nyudo | | | |
| 水虎 | Suiko | | | |
| 雷 | Kaminari | | boss banner 2-2 | |
| だるま | Daruma | | | |
| フランケンシュタイン | Frankenstein | | | |
| オオカミ男 | Wolfman | | | |
| ドラキュラ | Dracula | | | |
| 魔女 | Witch | | | |
| バックベアード | Backbeard | | | |
| やまたのおろち | Yamata no Orochi | | | |
| 天狐 | Tenko | | | |

## Places
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| 地獄 | Hell | | | |
| 地上界 | surface world | | | |
| 死人列車 | Train of the Dead | | | |

## Items / skills / terms
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| 石臼 | Millstone | | the time-travel millstone, capitalised | |
| 宝珠 | Orb | | wish-granting jewel, capitalised | |
| 宇宙妖怪 | space yokai | | | |
| 妖怪 | yokai | | plural yokai | youkai |
| 裁判 | trial | | | |

## Decisions from earlier batches
- 20_048 1999年 -> "1999" (date card over the picture).
- Staff-roll readings unverified (status.md, non-blocking): Hepburn of the most common reading.
