# Brilliant-move comparison: data and reproduction

[Read the report](REPORT.md) · [Interactive boards](https://mobilemaia.org/research/brilliant-moves/) · [Complete classical results](CLASSICS.md)

We compare Mobile Maia’s existing En Croissant-derived Brilliant detector with
the proposed Open Brilly Finder integration. The report explains the purpose,
results and planned adoption for Mobile Maia 2.7. This is research evidence,
not Android release qualification.

## Three comparisons

| Comparison | Games | Mainline plies | Baseline positions | Reference |
| --- | ---: | ---: | ---: | --- |
| Classics, Fast/Balanced/Thorough | 9 | 492 | 1,503 | 14 explicitly published `!!` moves |
| Online, Fast | 42 | 3,364 | 3,406 | 51 recorded Chess.com review Brilliants on 1,692 selected-account moves |
| Ginger, Fast | 27 | 1,837 | 1,864 | 32 captured gallery Brilliants on 922 Ginger moves |

All three comparisons use the actual app analyzer and both actual Dart classifiers,
sharing identical baseline scores. Each retains its normal provisional,
confirmation and final checks. The runner asserts that confirmations do not
change graph scores or baseline principal variations. No model, cutoff or
classification rules were changed for any comparison.

The online games come from seven titled-player accounts. Six games per account
were selected by a fixed hash before analysis. Thirty-six selected games were
upstream development games; six Witty_Alien games were held out upstream,
although other games from that account were used in training. Results describe
this source collection, not independent population accuracy. Primary counts use
recorded November 22, 2026 Game Review labels, not the gallery labels; agreement
with the gallery is reported separately in `online/summary.json`.

The independent [Ginger follow-up](ginger/REPORT.md) excludes any game or played
position-and-move pair matching the published development candidate data. Its
[overlap audit](ginger/overlap-audit.json) records three excluded games. It uses
the captured gallery as its reference, rather than the November 22 reviews.

## Pins and engine settings

- App: Preview [`096591bd8d42759e5a3f3a288d56d7c93245d6d1`](https://github.com/Dash1971/maia-chess-android-preview/tree/096591bd8d42759e5a3f3a288d56d7c93245d6d1); [implementation PR #284](https://github.com/Dash1971/maia-chess-android-preview/pull/284).
- Classical plan/registry/runner: `52065e0c57b788875687f41ace29cb252c92b242`.
- Online plan/sample/runner: `a3c44bf2ba76021db8a8688881f1dc80748318df`.
- Ginger plan/sample: `6844202bf606211c11a27b777560cf009293f30f`.
- Open Brilly Finder: `59cab58a8b63387d9775252f03a6875fe451f697`; model SHA-256 `992a792a646b11e612486c4fe26796fc38ee47f395f2220b00d26db65ba1e27d`; unchanged cutoff `0.8193002847777424`. Model weights are not copied here.
- Existing Homebrew Stockfish 18, macOS ARM64; binary 113,875,192 bytes; SHA-256 `ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374`. No engine binary is distributed.
- One search thread, 64 MiB hash, MultiPV2, fresh engine/session per game and mode. Positions within each game use the normal warm session.
- Fast depth 12 / 500 ms; Balanced 14 / 1,000 ms; Thorough 16 / 1,500 ms. Time caps can change results on another host. Achieved depths, nodes and times are recorded.
- Each detector keeps the normal six-search-unit annotation-confirmation budget. All published awards are final app labels, not raw model scores.

## Evidence map

- [Classical registry](data/annotation-registry.json), [PGN](data/games.pgn), [source receipts](data/game-score-sources.json), [access/normalization record](data/annotation-access-receipt.json), [full runs](data/engine-runs.json), [summary](data/summary.json).
- [Online plan](online/PLAN.md), [selection](online/selection.json), [source receipts](online/source-receipts.json), [legal games](online/games.json), [reference PGN](online/review-labels.pgn), [full native runs](online/engine-runs.json.gz), [all game-level counts](online/summary.json).
- [Existing-detector PGN](online/old-awards.pgn) and [Open Brilly Finder PGN](online/new-awards.pgn) include final `!!` awards on both players’ moves. Primary tables score only the selected account’s moves.
- [Chessbrah illustrations](online/spotlights.json) were chosen from the completed sample. Their moves and results are checked against the raw runs; they are illustrations, not extra tests.
- `data/story.json` supplies the shared narrative for the website and `REPORT.md`. The earlier classics-only interpretation remains historical in `data/editorial.json`.
- `web/results.json` and `web/online-results.json` are recorded viewer data. `web/website-files.json` bounds and hashes the website imports. The viewer runs no engine/model and stores no user data.
- `figures/` and [artwork notices](THIRD_PARTY.md) document actual legal positions and their rendering source.

Missing human annotations are not negative labels. Classical source `!` becoming
model `!!` is not counted as agreement with a published `!!`. Online awards
outside the recorded review’s Brilliant labels are counted as disagreements,
not automatically bad moves. Chess.com labels can change between reviews.

The classics’ source receipts disclose notation corrections and US Chess PDF
access limits. Their original registry hash identifies the contributing source
collection; the combined nine-game registry is fixed at the classical plan pin.
The frozen selection PGN contains the game scores; `review-labels.pgn` is the
derived export with the 51 recorded `!!` symbols. All three labeled exports
are parsed back and checked against the raw labels before publication.

The online selection records missing promotion suffixes resolved from legal
PGN moves. There were no other UCI mismatches in the eligible pool.

The shared shallow-search inconsistency at Opera15.Bxd7+ is retained: both
detectors grade it Blunder in Fast, Mistake in Balanced, unmarked in Thorough.
Balanced recommends it before the move (+6.39) then lowers its score (+3.10);
Thorough gives +8.32/+8.47. This is separate from the Brilliant model.

The [Ginger report](ginger/REPORT.md) includes every game, reference move and
additional award, with separate labeled PGNs. Its raw searches are retained in
`ginger/engine-runs.json.gz`; `tools/check_ginger.py` independently recounts all
results from the recorded labels.

## Reproduce

Use an existing Preview checkout at the app pin, the shared Flutter SDK, and a
Stockfish 18 executable. Follow the checkout’s disk and cleanup rules. Prepare
cached packages with `flutter pub get --offline`; a fresh checkout should use
`GIT_LFS_SKIP_SMUDGE=1`. Python tools need `chess==1.11.2` and `Pillow==12.1.0`
in one disposable environment. No Android build or model download is needed.

From this study directory, with ordinary Python/Flutter paths substituted:

```sh
python tools/fetch_online_sources.py --output /task/scratch/upstream
python tools/select_online.py --upstream /task/scratch/upstream
python tools/run_study.py --app /path/to/pinned-preview \
  --flutter /path/to/shared/flutter/bin/flutter \
  --stockfish /path/to/stockfish18 --output /task/scratch/online-runs.json \
  --games online/games.json --plan a3c44bf2ba76021db8a8688881f1dc80748318df \
  --qualities fast
python tools/summarize_online.py --runs /task/scratch/online-runs.json
python tools/summarize.py --runs data/engine-runs.json
python tools/build_article.py
python tools/check_study.py
python tools/check_online.py
```

The classical runner defaults to all three modes and `data/games.json` when
`--games`, `--plan` and `--qualities` are omitted. To repeat the original
classical collection, use a new output path and preserve the existing evidence.

Native time-limited results need not be byte-identical across hosts. Preserve
the original recorded output; do not replace it with a more flattering run.
Keep task-owned environments, fetched source collections and generated Flutter
output in disposable scratch and clean them after retaining compact evidence.
Preserve the shared SDK, caches and other work. Website publication uses its
separate web-only Pages workflow.
