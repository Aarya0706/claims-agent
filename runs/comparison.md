# v1 vs v2 (development, identical inputs & scoring)

| metric | v1 | v2 | delta |
|---|---|---|---|
| Joint F1 | 0.933 | 0.876 | -0.057 |
| Joint precision | 0.977 | 0.931 | -0.046 |
| Joint recall | 0.894 | 0.827 | -0.066 |
| Extraction F1 | 0.956 | 0.938 | -0.018 |
| Gold coverage C/G | 0.894 | 0.827 | -0.066 |

| count | v1 | v2 |
|---|---|---|
| G | 376 | 376 |
| P | 344 | 334 |
| M | 344 | 333 |
| C | 336 | 311 |
| answer_error_count | 1 | 0 |

## Regressions (correct in v1, not in v2): 51
- A01:1237:1439 [policy_scope] An authorized India service centre guarantees repair of ClearTrail Mini within two working days after receivin
- A01:649:832 [policy_scope] An opened ClearTrail Mini can be returned to any authorized India seller within thirty days for a full refund,
- A01:833:1040 [missing_fact] The sustained amplifier output of ClearTrail Mini is forty watts per channel during ordinary playback, which a
- A04:1098:1267 [date_scope|arithmetic] The move from the 2025 India catalogue to the 2026 catalogue raised the tax-inclusive list price of StoneWave 
- A04:2363:2540 [historical_scope] In the 2025 India catalogue, before the current-year revision, StoneWave Max already carried the same tax-incl
- A05:1468:1651 [requirement_vs_availability] Basic Bluetooth playback on StoneWave Go requires the manufacturer companion app to be installed first, rather
- A05:699:890 [inference] The Bluetooth connection on StoneWave Go maintains uninterrupted playback at a distance of one hundred metres 
- A05:891:1095 [missing_fact] The sustained amplifier output of StoneWave Go is forty watts per channel during ordinary playback, which allo
- A06:1432:1621 [condition_scope] In winter weather below freezing, ClearTrail Plus delivers its full 20-hour laboratory battery duration at fif
- A09:845:1048 [policy_scope] An authorized India service centre guarantees repair of CloudNote Studio within two working days after receivi
- A10:371:563 [inference|missing_fact] The normal manufacturing origin of CloudNote Air is India, even when the unit is purchased through an authoriz
- A11:306:483 [historical_scope] In the 2025 India catalogue, before the current-year revision, StoneWave Max already carried the same tax-incl
- A13:511:680 [price_vs_shipping] Orders for StoneWave Go receive free delivery to every India postal code, so there is no separate shipping cha
- A15:306:495 [condition_scope] In winter weather below freezing, ClearTrail Mini delivers its full 12-hour laboratory battery duration at fif
- A16:1423:1613 [condition_scope] In winter weather below freezing, CloudNote Studio delivers its full 18-hour laboratory battery duration at fi
- A16:455:618 [comparison|arithmetic] For a current India catalogue comparison before shipping, CloudNote Studio is INR 1,500 less expensive than Cl
- A16:620:828 [missing_fact] The sustained amplifier output of CloudNote Studio is forty watts per channel during ordinary playback, which 
- A17:1055:1247 [inference|missing_fact] The normal manufacturing origin of CloudNote Air is India, even when the unit is purchased through an authoriz
- A18:491:661 [price_vs_shipping] Orders for StoneWave Max receive free delivery to every India postal code, so there is no separate shipping ch
- A21:893:1087 [inference|missing_fact] The normal manufacturing origin of ClearTrail Plus is India, even when the unit is purchased through an author
- A22:1553:1704 [outdated_fact] For an India purchase at the official catalogue list price on 1 October 2026, ClearTrail Mini still costs INR 
- A22:1706:1892 [feature_conflation] ClearTrail Mini supports the AAC Bluetooth audio codec on compatible phones, so its published Bluetooth versio
- A22:1893:2087 [inference] The Bluetooth connection on ClearTrail Mini maintains uninterrupted playback at a distance of one hundred metr
- A22:2088:2271 [policy_scope] An opened ClearTrail Mini can be returned to any authorized India seller within thirty days for a full refund,
- A23:549:744 [inference] The Bluetooth connection on CloudNote Studio maintains uninterrupted playback at a distance of one hundred met
- A24:891:1091 [policy_scope] An authorized India service centre guarantees repair of CloudNote Air within two working days after receiving 
- A25:306:459 [comparison|arithmetic] For the current India catalogue, CloudNote Air is listed at INR 1,500 less than CloudNote Studio, comparing th
- A27:1393:1579 [negation|qualification] With all port covers closed, StoneWave Go is explicitly permitted to be immersed in fresh water, rather than b
- A27:1747:1938 [inference] The Bluetooth connection on StoneWave Go maintains uninterrupted playback at a distance of one hundred metres 
- A27:324:493 [price_vs_shipping] Orders for StoneWave Go receive free delivery to every India postal code, so there is no separate shipping cha
- A27:494:688 [feature_conflation] StoneWave Go accepts two active Bluetooth source connections at the same time and switches between them automa
- A27:690:873 [requirement_vs_availability] Basic Bluetooth playback on StoneWave Go requires the manufacturer companion app to be installed first, rather
- A28:549:751 [negative_missing_fact] No version of ClearTrail Plus has ever been offered in blue, including previous-year retail stock and editions
- A29:1172:1369 [feature_conflation] ClearTrail Mini accepts two active Bluetooth source connections at the same time and switches between them aut
- A29:1370:1549 [negation|policy_scope] An original invoice is unnecessary when claiming the standard India manufacturer warranty for ClearTrail Mini,
- A29:789:975 [feature_conflation] ClearTrail Mini supports the AAC Bluetooth audio codec on compatible phones, so its published Bluetooth versio
- A31:1051:1238 [feature_conflation] CloudNote Studio supports the AAC Bluetooth audio codec on compatible phones, so its published Bluetooth versi
- A31:655:854 [missing_fact] The plastic used in the enclosure of CloudNote Studio contains at least sixty percent post-consumer recycled m
- A31:855:1050 [inference|missing_fact] The normal manufacturing origin of CloudNote Studio is India, even when the unit is purchased through an autho
- A33:843:1027 [requirement_vs_availability] Basic Bluetooth playback on StoneWave Max requires the manufacturer companion app to be installed first, rathe
- A34:1155:1315 [unit_conversion] At fifty percent volume with EQ off and a new battery in the laboratory, StoneWave Go is rated for 1020 minute
- A34:809:958 [comparison|arithmetic] For the current India catalogue, StoneWave Go is listed at INR 1,500 less than StoneWave Max, comparing the tw
- A35:1442:1606 [comparison|arithmetic] For a current India catalogue comparison before shipping, ClearTrail Plus is INR 1,200 less expensive than Cle
- A36:1256:1463 [cross_brand_comparison] Compared with the unlisted RivalSound Trek, ClearTrail Mini provides two additional hours of playback under id
- A36:324:496 [price_vs_shipping] Orders for ClearTrail Mini receive free delivery to every India postal code, so there is no separate shipping 
- A37:2218:2407 [condition_scope] In winter weather below freezing, ClearTrail Mini delivers its full 12-hour laboratory battery duration at fif
- A38:1208:1388 [missing_condition] Using a twenty-watt wall adapter, a fully discharged CloudNote Studio reaches a complete charge in ninety minu
- A38:1389:1592 [negative_missing_fact] No version of CloudNote Studio has ever been offered in blue, including previous-year retail stock and edition
- A38:1593:1792 [missing_fact] The plastic used in the enclosure of CloudNote Studio contains at least sixty percent post-consumer recycled m
- A40:1423:1572 [comparison|arithmetic] For the current India catalogue, StoneWave Max is listed at INR 1,500 more than StoneWave Go, comparing the tw
- A40:872:1041 [date_scope|arithmetic] The move from the 2025 India catalogue to the 2026 catalogue raised the tax-inclusive list price of StoneWave 

## Improvements (correct in v2, not in v1): 26
- A03:335:505 [price_vs_shipping] Orders for CloudNote Air receive free delivery to every India postal code, so there is no separate shipping ch
- A03:506:687 [policy_scope] An opened CloudNote Air can be returned to any authorized India seller within thirty days for a full refund, e
- A03:689:861 [model_scope|explicit_false] The built-in microphone is included on CloudNote Air, so microphone availability should be checked for this ex
- A06:1803:1957 [comparison|arithmetic] For the current India catalogue, ClearTrail Plus is listed at INR 1,200 more than ClearTrail Mini, comparing t
- A12:1229:1378 [comparison|arithmetic] For the current India catalogue, StoneWave Go is listed at INR 1,500 less than StoneWave Max, comparing the tw
- A12:1379:1559 [policy_scope] An opened StoneWave Go can be returned to any authorized India seller within thirty days for a full refund, ev
- A12:1560:1741 [capability_vs_connector|negation] For wired digital audio specifically, the USB-C connector on StoneWave Go does provide an audio-input path, so
- A12:1743:1916 [variant_transfer] When measuring just the speaker rather than the retail box and accessories, StoneWave Go weighs 900 grams, mat
- A12:1917:2113 [policy_vs_capability] Whatever conclusions a buyer draws from the water-resistance rating, water damage remains excluded from the st
- A19:1465:1654 [future_scope] After an announced firmware update next quarter, StoneWave Max will gain a built-in voice assistant that can a
- A19:1655:1832 [negation|policy_scope] An original invoice is unnecessary when claiming the standard India manufacturer warranty for StoneWave Max, p
- A19:1834:2008 [unit_conversion|policy_scope] For manufacturing defects following an authorized India purchase with the original invoice, the standard manuf
- A19:2009:2201 [inference] The Bluetooth connection on StoneWave Max maintains uninterrupted playback at a distance of one hundred metres
- A19:2202:2372 [price_vs_shipping] Orders for StoneWave Max receive free delivery to every India postal code, so there is no separate shipping ch
- A19:371:555 [policy_scope] For an authorized India purchase with the original invoice and a manufacturing defect, StoneWave Max receives 
- A19:556:729 [variant_transfer] When measuring just the speaker rather than the retail box and accessories, StoneWave Max weighs 440 grams, ma
- A19:731:902 [box_scope] The official India retail box for StoneWave Max includes a wall charging adapter, even though separate accesso
- A19:903:1067 [qualification|unit_conversion] With all port covers closed, the laboratory immersion allowance for StoneWave Max is limited to fresh water at
- A25:1185:1366 [policy_scope] An opened CloudNote Air can be returned to any authorized India seller within thirty days for a full refund, e
- A25:632:824 [inference] The Bluetooth connection on CloudNote Air maintains uninterrupted playback at a distance of one hundred metres
- A26:1976:2153 [missing_condition] Using a twenty-watt wall adapter, a fully discharged StoneWave Max reaches a complete charge in ninety minutes
- A33:1575:1780 [missing_fact] The sustained amplifier output of StoneWave Max is forty watts per channel during ordinary playback, which all
- A33:2112:2307 [feature_conflation] StoneWave Max accepts two active Bluetooth source connections at the same time and switches between them autom
- A33:2309:2509 [negative_missing_fact] No version of StoneWave Max has ever been offered in blue, including previous-year retail stock and editions s
- A33:306:498 [inference] The Bluetooth connection on StoneWave Max maintains uninterrupted playback at a distance of one hundred metres
- A33:499:656 [explicit_false] The built-in Wi-Fi capability of StoneWave Max is present, independently of whatever Bluetooth connection a li

## Extra/unmatched predictions: v1 0, v2 1; only in v2: 1
