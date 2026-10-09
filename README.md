# Mobile Maia research

Independent research supporting design decisions in [Mobile Maia](https://github.com/Dash1971/maia-chess-android) and [Mobile Maia Preview](https://github.com/Dash1971/maia-chess-android-preview).

Research reports, datasets and reproduction tools live in this repository, separate from application source and release distributions. App READMEs contain brief decision summaries and links here.

## Studies

### Move-history input — 9 October 2026

[Read the report](studies/move-history-2026-10-09/REPORT.md) · [Evidence and reproduction guide](studies/move-history-2026-10-09/README.md)

History improved average human-move prediction but strongly reinforced copying in a low-Elo Stonewall test. The recommendation is to keep history off by default; an [experimental opt-in setting](https://github.com/Dash1971/maia-chess-android-preview/issues/101) is proposed separately.

The study includes 20,160 main human-game positions, 4,000 opening positions, 384 tactical diagnostics and 1,000 targeted Stonewall opening trials. It does not establish a change in full-game Elo or claim an explicit upstream recommendation against history.

## Attribution and licence

This is independent Mobile Maia research, not an official Maia-team publication. Sources, model hashes and methodological limits are documented per study. Original code and documentation are licensed under [AGPL-3.0-only](LICENSE); third-party models, datasets and software retain their upstream terms.
