# Brilliant moves gained and lost

Preview 2.7 draft comparison · November 28, 2026

## Mobile Maia engine tests

**Four distinct moves account for 10 gained and 6 withdrawn awards across 821 recorded move snapshots.** Each diagram shows the actual before/after position. The arrow marks the played move.

These reuse 17 recorded runs of six games, not 821 unique games. No new engine analysis was run for this review. Model scores are not probabilities.

### 11...Na4 — gained

Byrne–Fischer, 1956

![11...Na4 before and after](figures/01-gained.png)

| Engine/mode | Previous | New | Model score |
| --- | --- | --- | ---: |
| SF18 · Fast | Brilliant !! | Brilliant !! | 0.9865 |
| SF18 · Balanced | Interesting !? | Brilliant !! | 0.9380 |
| SF18 · Thorough | Brilliant !! | Brilliant !! | 0.9860 |
| SF Light · Fast | Brilliant !! | Brilliant !! | 0.9860 |
| SF Light · Balanced | Brilliant !! | Brilliant !! | 0.9863 |
| SF Light · Thorough | Brilliant !! | Brilliant !! | 0.9853 |

### 15...Nxc3 — gained

Byrne–Fischer, 1956

![15...Nxc3 before and after](figures/02-gained.png)

| Engine/mode | Previous | New | Model score |
| --- | --- | --- | ---: |
| SF18 · Fast | Interesting !? | Brilliant !! | 0.8933 |
| SF18 · Balanced | Interesting !? | Brilliant !! | 0.9499 |
| SF18 · Thorough | Interesting !? | Brilliant !! | 0.9569 |
| SF Light · Fast | Interesting !? | Brilliant !! | 0.9635 |
| SF Light · Balanced | Interesting !? | Brilliant !! | 0.9602 |
| SF Light · Thorough | Interesting !? | Brilliant !! | 0.9702 |

### 19...Ne2+ — lost

Byrne–Fischer, 1956

![19...Ne2+ before and after](figures/03-lost.png)

| Engine/mode | Previous | New | Model score |
| --- | --- | --- | ---: |
| SF18 · Fast | Brilliant !! | Interesting !? | Gate not met |
| SF18 · Balanced | Brilliant !! | Interesting !? | Gate not met |
| SF18 · Thorough | Brilliant !! | Interesting !? | Gate not met |
| SF Light · Fast | Brilliant !! | Interesting !? | Gate not met |
| SF Light · Balanced | Brilliant !! | Interesting !? | Gate not met |
| SF Light · Thorough | Brilliant !! | Interesting !? | Gate not met |

The Exchange offer gate rejects this position: it does not leave a non-pawn piece capturable for a static-exchange gain of at least two pawns. Tree inference is not run; zero here is the no-candidate sentinel.

### 13.Rxd7 — gained

Opera game, 1858

![13.Rxd7 before and after](figures/04-gained.png)

| Engine/mode | Previous | New | Model score |
| --- | --- | --- | ---: |
| SF18 · Fast | Unmarked | Brilliant !! | 0.8440 |
| SF18 · Balanced | Unmarked | Brilliant !! | 0.8537 |
| SF18 · Thorough | Unmarked | Brilliant !! | 0.8569 |

## Labeled reference cases

The selected 360-case regression subset contains 57 recorded Brilliant labels. It is not a held-out accuracy test. The new integration recovers 24 labels and loses one; it removes two previous outside-label awards and adds two different ones. “No Brilliant label” describes the fixture, not an independent judgment that the move is unworthy.

<details>
<summary>Gained — recorded Brilliant label (24)</summary>

### 12.Nxf7 · `164532229312:23`

Interesting !? → Brilliant !! · Model score 0.9783 · Cutoff 0.8193

![12.Nxf7, case 164532229312:23, before and after](figures/05-gained.png)

### 29...Rexd5 · `159959851695:58`

Interesting !? → Brilliant !! · Model score 0.9836 · Cutoff 0.8193

![29...Rexd5, case 159959851695:58, before and after](figures/06-gained.png)

### 15...Bxf3 · `164721239428:30`

Interesting !? → Brilliant !! · Model score 0.9670 · Cutoff 0.8193

![15...Bxf3, case 164721239428:30, before and after](figures/07-gained.png)

### 12.Rxe7 · `174283146070:23`

Good ! → Brilliant !! · Model score 0.9162 · Cutoff 0.8193

![12.Rxe7, case 174283146070:23, before and after](figures/08-gained.png)

### 8.Bxe6 · `184105420416:15`

Interesting !? → Brilliant !! · Model score 0.9881 · Cutoff 0.8193

![8.Bxe6, case 184105420416:15, before and after](figures/09-gained.png)

### 19.Rxe7 · `167644814241:37`

Interesting !? → Brilliant !! · Model score 0.9434 · Cutoff 0.8193

![19.Rxe7, case 167644814241:37, before and after](figures/10-gained.png)

### 10.Bxf7+ · `166088573276:19`

Interesting !? → Brilliant !! · Model score 0.9807 · Cutoff 0.8193

![10.Bxf7+, case 166088573276:19, before and after](figures/11-gained.png)

### 41...Qxf3 · `167684805790:82`

Interesting !? → Brilliant !! · Model score 0.9650 · Cutoff 0.8193

![41...Qxf3, case 167684805790:82, before and after](figures/12-gained.png)

### 26...Qf7 · `168788226486:52`

Interesting !? → Brilliant !! · Model score 0.9786 · Cutoff 0.8193

![26...Qf7, case 168788226486:52, before and after](figures/13-gained.png)

### 19.Rxg7+ · `169548062348:37`

Interesting !? → Brilliant !! · Model score 0.9867 · Cutoff 0.8193

![19.Rxg7+, case 169548062348:37, before and after](figures/14-gained.png)

### 18.Nxf6+ · `184153711551:35`

Interesting !? → Brilliant !! · Model score 0.9226 · Cutoff 0.8193

![18.Nxf6+, case 184153711551:35, before and after](figures/15-gained.png)

### 24...Nxf3+ · `146198437668:48`

Interesting !? → Brilliant !! · Model score 0.9854 · Cutoff 0.8193

![24...Nxf3+, case 146198437668:48, before and after](figures/16-gained.png)

### 27.Rxe4 · `171198260282:53`

Interesting !? → Brilliant !! · Model score 0.9785 · Cutoff 0.8193

![27.Rxe4, case 171198260282:53, before and after](figures/17-gained.png)

### 12.Bxf5 · `147571431566:23`

Interesting !? → Brilliant !! · Model score 0.9062 · Cutoff 0.8193

![12.Bxf5, case 147571431566:23, before and after](figures/18-gained.png)

### 10.Ne6 · `172749937408:19`

Interesting !? → Brilliant !! · Model score 0.9388 · Cutoff 0.8193

![10.Ne6, case 172749937408:19, before and after](figures/19-gained.png)

### 13...Bxh3 · `166587005254:26`

Interesting !? → Brilliant !! · Model score 0.9693 · Cutoff 0.8193

![13...Bxh3, case 166587005254:26, before and after](figures/21-gained.png)

### 16...Nd4 · `165665978762:32`

Interesting !? → Brilliant !! · Model score 0.8588 · Cutoff 0.8193

![16...Nd4, case 165665978762:32, before and after](figures/22-gained.png)

### 34.Nxg5 · `183549510985:67`

Interesting !? → Brilliant !! · Model score 0.9736 · Cutoff 0.8193

![34.Nxg5, case 183549510985:67, before and after](figures/23-gained.png)

### 26...Rxg2 · `165044515796:52`

Unmarked → Brilliant !! · Model score 0.9577 · Cutoff 0.8193

![26...Rxg2, case 165044515796:52, before and after](figures/24-gained.png)

### 14.Bxh6 · `170273353146:27`

Interesting !? → Brilliant !! · Model score 0.9639 · Cutoff 0.8193

![14.Bxh6, case 170273353146:27, before and after](figures/25-gained.png)

### 12...Bxa3 · `185540484714:24`

Interesting !? → Brilliant !! · Model score 0.9137 · Cutoff 0.8193

![12...Bxa3, case 185540484714:24, before and after](figures/26-gained.png)

### 13...Bxh2+ · `184554948912:26`

Interesting !? → Brilliant !! · Model score 0.9359 · Cutoff 0.8193

![13...Bxh2+, case 184554948912:26, before and after](figures/27-gained.png)

### 21.Rxg7 · `145419824932:41`

Interesting !? → Brilliant !! · Model score 0.9551 · Cutoff 0.8193

![21.Rxg7, case 145419824932:41, before and after](figures/28-gained.png)

### 14...Rxe3 · `167940763426:28`

Interesting !? → Brilliant !! · Model score 0.9829 · Cutoff 0.8193

![14...Rxe3, case 167940763426:28, before and after](figures/29-gained.png)

</details>

<details>
<summary>Gained — outside recorded Brilliant labels (2)</summary>

### 6.Ne5 · `dash/tjxdTRho:11`

Unmarked → Brilliant !! · Model score 0.9160 · Cutoff 0.8193

![6.Ne5, case dash/tjxdTRho:11, before and after](figures/32-gained.png)

### 14.Bxh6 · `dash/DEFZuyyq:27`

Interesting !? → Brilliant !! · Model score 0.9483 · Cutoff 0.8193

![14.Bxh6, case dash/DEFZuyyq:27, before and after](figures/33-gained.png)

</details>

<details>
<summary>Lost — recorded Brilliant label (1)</summary>

### 29.Qxf3 · `146250076136:57`

Brilliant !! → Interesting !? · Model score 0.7118 · Cutoff 0.8193

![29.Qxf3, case 146250076136:57, before and after](figures/20-lost.png)

</details>

<details>
<summary>Lost — outside recorded Brilliant labels (2)</summary>

### 32...Kxg6 · `180013382960:64`

Brilliant !! → Interesting !? · Model score 0.0858 · Cutoff 0.8193

![32...Kxg6, case 180013382960:64, before and after](figures/30-lost.png)

### 31...Rxe7 · `opp/172333987890:62`

Brilliant !! → Unmarked · Model score 0.0007 · Cutoff 0.8193

![31...Rxe7, case opp/172333987890:62, before and after](figures/31-lost.png)

</details>

## Sources and reproduction

[Complete positions, engine lines and scores](data/changed-moves.json) · [Reproduction](README.md) · [Artwork notices](THIRD_PARTY.md)

Application classifier: [Preview `04e903b`](https://github.com/Dash1971/maia-chess-android-preview/tree/04e903b1e4abe635d2168d01b027ecc24f240651). Model/reference: [Open Brilly Finder `59cab58`](https://github.com/Dash1971/open-brilly-finder/tree/59cab58a8b63387d9775252f03a6875fe451f697).

Only Brilliant-related changes are listed. Other retained awards and unchanged grades are outside this catalog. Graph evaluations are unchanged. Native mode rows include unchanged awards at the same four positions; Stockfish Light Opera-game runs were not recorded. Android qualification remains pending in Preview #284.
