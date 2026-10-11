# Mobile Maia research

Independent research supporting design decisions in [Mobile Maia](https://github.com/Dash1971/maia-chess-android) and [Mobile Maia Preview](https://github.com/Dash1971/maia-chess-android-preview).

Research reports, datasets and reproduction tools live in this repository, separate from application source and release distributions. App READMEs contain brief decision summaries and links here.

## Studies

### Temperature and Top-P sampling

[Read the report](studies/maia3-sampling/REPORT.md) · [Evidence and reproduction guide](studies/maia3-sampling/README.md)

Lower sampling settings made Maia stronger in the tested matches but reduced opening variety. The report covers the original 1.0/1.0, 0.5/0.9 and greedy comparisons, plus the 1.0/0.95 follow-up. Recorded games, human opening references, diagnostics, figures and reproduction tools are included. Results describe these experiments, rather than a universal Elo guarantee or an upstream recommendation.

The original app-repository publication remains available for older app versions.

### Move-history input — 9 October 2026

[Read the report](studies/move-history-2026-10-09/REPORT.md) · [Evidence and reproduction guide](studies/move-history-2026-10-09/README.md)

History improved average human-move prediction but strongly reinforced copying in a low-Elo Stonewall test. The recommendation is to keep history off by default; an [experimental opt-in setting](https://github.com/Dash1971/maia-chess-android-preview/issues/101) is proposed separately.

The study includes 20,160 main human-game positions, 4,000 opening positions, 384 tactical diagnostics and 1,000 targeted Stonewall opening trials. It does not establish a change in full-game Elo or claim an explicit upstream recommendation against history.

## Attribution and licence

This is independent Mobile Maia research, not an official Maia-team publication. Sources, model hashes and methodological limits are documented per study. Original code and documentation are licensed under [AGPL-3.0-only](LICENSE); third-party models, datasets and software retain their upstream terms.
