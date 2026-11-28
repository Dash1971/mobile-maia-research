# Ginger: Fast, Balanced and Thorough

The same 27 games, 32 captured gallery brillies and 922 Ginger moves.
Both classifiers use the same engine evidence within each mode.
Fast is the original published run; Balanced and Thorough use fresh searches.

| Mode | En Croissant (adapted): gallery !! found | Open Brilly Finder: gallery !! found | Adapted / new awards outside gallery |
|---|---:|---:|---:|
| Fast | 7 / 32 | 20 / 32 | 5 / 1 |
| Balanced | 6 / 32 | 23 / 32 | 4 / 1 |
| Thorough | 8 / 32 | 24 / 32 | 6 / 1 |

Open Brilly Finder recovers more gallery labels in every mode, with fewer awards outside the gallery. This sample supports keeping the app’s current search settings and unchanged model cutoff; it does not justify forcing every mode to the training search setup.

## What changes with the mode

| Mode | Gallery labels gained over adapted En Croissant | Labels lost | All adapted / new Brilliant awards |
|---|---:|---:|---:|
| Fast | 14 | 1 | 12 / 21 |
| Balanced | 18 | 1 | 10 / 24 |
| Thorough | 17 | 1 | 14 / 25 |

The model and cutoff are unchanged. These are final app awards after normal
grading precedence, previous-iteration checks and bounded confirmations.
Deeper search can change an evaluation and a label. The table measures the
observed effect; it does not assume deeper evidence always improves a score.

## Raw model-score shifts on the same targets

These shifts cover only gallery targets that are piece-offer candidates in
both modes. They are baseline model scores before the app reliability guards,
not probabilities or final Brilliant awards.

| Compared with Fast | Common candidates | Median score change | Minimum / maximum change | Cutoff crossed up / down |
|---|---:|---:|---:|---:|
| Balanced | 32 | +0.000797 | -0.0751 / +0.7605 | 3 / 1 |
| Thorough | 32 | +0.000045 | -0.0188 / +0.8369 | 3 / 0 |

## Search evidence

| Mode | Nonterminal positions | Completed depth: number of positions | New Brilliant candidates omitted from confirmation budget |
|---|---:|---|---:|
| Fast | 1862 | 9: 8, 10: 64, 11: 202, 12: 1588 | 0 |
| Balanced | 1862 | 8: 2, 9: 4, 10: 3, 11: 15, 12: 77, 13: 130, 14: 1631 | 0 |
| Thorough | 1862 | 11: 8, 12: 32, 13: 89, 14: 126, 15: 138, 16: 1469 | 0 |

Search requests: Fast 12 / 500 ms, Balanced 14 / 1,000 ms, Thorough 16 /
1,500 ms. Time limits can stop an iteration before the requested depth.
The app retains its existing completeness and annotation-agreement guards.
Evidence-depth and budget diagnostics cover both players; award totals count
only Ginger’s moves. All runs use one thread, 64 MiB hash, MultiPV 2 and normal within-session hash
reuse. Each classifier keeps its normal six-search-unit confirmation budget.

## Every captured gallery move

Each cell is adapted En Croissant / Open Brilly Finder: !! means a final
Brilliant award, and — means no Brilliant award.

| Game | Move | Fast: adapted / new | Balanced: adapted / new | Thorough: adapted / new |
|---|---|---|---|---|
| [188136844746](https://www.chess.com/game/live/188136844746) | 38...Qd2 | !! / !! | !! / !! | !! / !! |
| [189854753175](https://www.chess.com/game/live/189854753175) | 35.Qxh5 | — / — | — / — | — / — |
| [189853553123](https://www.chess.com/game/live/189853553123) | 12...Nxe4 | — / !! | — / !! | — / !! |
| [189853553123](https://www.chess.com/game/live/189853553123) | 34...Rxf2+ | — / — | — / — | — / — |
| [187896748818](https://www.chess.com/game/live/187896748818) | 14...Nxd4 | — / !! | — / !! | — / !! |
| [187459649420](https://www.chess.com/game/live/187459649420) | 27.Bxe7 | — / — | — / — | — / — |
| [187457958048](https://www.chess.com/game/live/187457958048) | 18.Nd5 | — / !! | — / !! | — / !! |
| [187353132044](https://www.chess.com/game/live/187353132044) | 20.Nb4 | — / — | — / — | — / — |
| [187353132044](https://www.chess.com/game/live/187353132044) | 22.Rxd7+ | — / !! | — / !! | !! / !! |
| [187352976104](https://www.chess.com/game/live/187352976104) | 13...Bxh2+ | !! / !! | !! / !! | !! / !! |
| [187352976104](https://www.chess.com/game/live/187352976104) | 15...Bh2+ | — / !! | — / !! | — / !! |
| [187352976104](https://www.chess.com/game/live/187352976104) | 16...Qe8 | — / — | — / — | — / — |
| [187352976104](https://www.chess.com/game/live/187352976104) | 20...Rh1+ | — / !! | — / !! | — / !! |
| [187106742030](https://www.chess.com/game/live/187106742030) | 29...Qa5 | !! / !! | !! / !! | !! / !! |
| [187104408324](https://www.chess.com/game/live/187104408324) | 18.Ne4 | — / — | — / !! | — / !! |
| [187052146336](https://www.chess.com/game/live/187052146336) | 18...fxg3 | !! / !! | !! / !! | !! / !! |
| [188642299209](https://www.chess.com/game/live/188642299209) | 26...Rxf2 | — / !! | — / !! | — / !! |
| [186895306980](https://www.chess.com/game/live/186895306980) | 21...Rxg5 | — / !! | — / !! | — / !! |
| [186807227802](https://www.chess.com/game/live/186807227802) | 14...Nxe4 | !! / — | !! / — | !! / — |
| [186804298306](https://www.chess.com/game/live/186804298306) | 18.Nxe4 | !! / !! | !! / !! | !! / !! |
| [186798917398](https://www.chess.com/game/live/186798917398) | 17.Nd6 | — / !! | — / !! | — / !! |
| [186787690334](https://www.chess.com/game/live/186787690334) | 14...Bg4 | — / — | — / — | — / — |
| [186786230002](https://www.chess.com/game/live/186786230002) | 26.Nf5 | — / — | — / — | — / — |
| [186771033900](https://www.chess.com/game/live/186771033900) | 24.Nxc5 | !! / !! | — / !! | — / !! |
| [186706231870](https://www.chess.com/game/live/186706231870) | 14.Nd5 | — / !! | — / !! | — / !! |
| [186704873752](https://www.chess.com/game/live/186704873752) | 28.Nh5 | — / !! | — / !! | — / !! |
| [186701606880](https://www.chess.com/game/live/186701606880) | 6...a4 | — / — | — / !! | — / !! |
| [186700377930](https://www.chess.com/game/live/186700377930) | 16...Nxf2 | — / !! | — / !! | — / !! |
| [186700239458](https://www.chess.com/game/live/186700239458) | 16...Rxf3 | — / — | — / !! | !! / !! |
| [186659807318](https://www.chess.com/game/live/186659807318) | 19.Rxh5 | — / !! | — / !! | — / !! |
| [186573944216](https://www.chess.com/game/live/186573944216) | 22...Nf4 | — / — | — / !! | — / !! |
| [186573774294](https://www.chess.com/game/live/186573774294) | 23.Qe7 | — / !! | — / — | — / !! |

## Scope and reproduction

This sample was selected for containing gallery brillies. Awards outside the
captured gallery are disagreements, not proven false positives. These results
do not establish precision across ordinary games or calibrate the model.
Each game/mode has one recorded desktop pass. Time-limited searches and host
load can change lines and labels on a fresh run; the retained evidence makes
this exact comparison reproducible without rerunning the engine.
They test the app’s current mode behavior rather than reproduce the training
search distribution. They do not measure Android speed or memory.

[Plan](PLAN.md) · [Original sample and overlap audit](../REPORT.md) ·
[All counts and scores](summary.json) · [Raw searches](engine-runs.json.gz)

Use the shared Flutter host environment and desktop Stockfish 18. The runner
takes the existing Ginger runner input wrapped with the pinned provenance and
`qualities: ["balanced", "thorough"]`. Resume completed checkpoints with
`BRILLY_STUDY_RESUME=1`; a partial game/mode is rerun, never counted twice.
The 120-minute harness timeout does not change any engine search budget.

```sh
python tools/compare_ginger_modes.py --runs /path/to/ginger-balanced-thorough.json
```

No Android builds, Actions, LFS downloads, model changes or website deployment.
