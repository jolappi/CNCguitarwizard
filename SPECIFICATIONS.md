# CNCguitarwizard – Prototype001

Lyhyt, tämänhetkinen valmistusspeksi. Kaikki mitat ovat millimetrejä, ellei
toisin mainita.

## Kaula ja otelauta

| Kohta | Speksi |
| --- | --- |
| Skaala | 609,6 mm / 24" |
| Kätisyys | Vasenkätinen (runko peilattu; kaula on symmetrinen) |
| Nauhat | 24 |
| Satulaleveys | 42 mm |
| Leveys 24. nauhalla / kannassa | 56 mm |
| Profiili | Ohut, pyöristetty D / Wizard-henkinen |
| Kokonaispaksuus 1. nauhalla | 17 mm, sisältää otelaudan |
| Kokonaispaksuus 12. nauhalla | 19 mm, sisältää otelaudan |
| Otelauta | Erillinen, 6 mm paksu, 430 mm säde |
| Otelaudan pää | 4 mm 24. nauhan jälkeen; samassa tasossa kannan lopun kanssa |
| Satulahylly | Kiinteä 5 mm ennen otelautaa; ei saa muuttua |
| Nauhaurat | 0,6 mm × 2,7 mm |
| Inlayt | Piikkilankakuvio, 2 mm syvät; välit 3, 5, 7, 9, 15, 17, 19, 21 yksittäin, 12 ja 24 kaksoismerkillä |

## Kanta ja kiinnitys

| Kohta | Speksi |
| --- | --- |
| Kannan puupaksuus | 20 mm otelaudan alla |
| Tasainen kiinnitysalue | Säädettävä, vähintään 40 mm; Prototype001: 54 mm |
| Kannan alapuoli | Tasainen runkoon kiinnittämistä varten |
| Liitos | Kapeneva, pyöristetty D-profiilista kannan suoralle alueelle |
| Heel root | Säädettävä; oletus 45 mm |
| Keskiscoop | Säädettävä; oletus 1,5 mm sisäänpäin |

Tasainen kiinnitysalue säilyy kokonaan tasaisena. Pyöristetty siirtymä tehdään
ennen sitä, myös sivusuunnassa.

## Satulan pään U-liitos

Kaulan pään U-muoto tehdään pystyakselisella sylinterillä. U-sylinterin ja
D-profiilin liittymä on yhtenäinen, pyöreä juuripinta: D-profiilin muotojen
tulee lähteä sylinteristä sekä kaulan suuntaan että sivuille. Pyöristys tehdään
vain U-sylinterin kahdelle pystysivulle, niissä kohdissa joissa sylinterin
sivuseinä liittyy jo olemassa olevaan kylkipyöristykseen; keskimmäinen kaari
ja uloimmat päät jätetään ennalleen. Se ei ole erillinen ura. Satulahylly
pysyy aina kiinteänä 5 mm:nä. Tällä 5 mm alueella keskikohta pysyy tasaisena,
mutta reunojen D-profiili jatkuu pituussuunnassa kaulan päähän asti ennen
liittymistä U-sylinteriin.

## Lapa

| Kohta | Speksi |
| --- | --- |
| Muoto | Oma, moderni kapeneva 3+3-malli |
| Pituus | 150 mm |
| Kulma | 8° |
| Paksuus | Säädettävä 14–16 mm; oletus 16 mm |
| Hartialeveys | 65 mm |
| Kärjen leveys | 40 mm |
| Virittimet | 6 × 10 mm läpireikää |
| Reunapuuta viritinreiällä | Vähintään 8 mm |
| Reikäviiste | 45°, 0,2 mm |

Kaulan ja lavan takaliitos on jatkuva, matala ja peukalolle vapaa. Satulahylly
säilyy 5 mm:nä kaikissa lapaliitoksen muutoksissa.

## Kaularauta ja kohdistus

| Kohta | Speksi |
| --- | --- |
| Kaularauta | Kaksitoiminen 440 × 6 × 9 mm |
| Säätö | Kannan puolen spoke wheel |
| Kohdistus | 2 × 6 mm kohdistustappi kaksipuoliseen koneistukseen |

## Runko

Runko on jäljitetty omasta `assets/reference/omarunko.dxf`-piirustuksesta
(`presets/_omarunko_outline.py`); muodot ovat piirustuksen omia, eivät
likiarvoja. Koordinaatisto on kaulan: X satulasta perään, Y sivulle, yläpinta
Z = 0. Rungon piirteet (ääriviiva, kolot, potikat, jakki) seuraavat kannan
päätä ja tallan piirteet (tallalevyn kolo, tallamikki) mensuuria, joten
mensuurin tai nauhamäärän muutos pitää kaulan taskussaan ja tallan
mensuurilla.

| Kohta | Speksi |
| --- | --- |
| Paksuus | 44 mm tasainen laatta (ei vielä käsi-/vatsaviisteitä) |
| Kaulatasku | Kaulan oma kapeneva ääriviiva + 0,15 mm välys/puoli, 79,5 mm pitkä, päättyy kannan päähän, 20 mm syvä; avautuu sarvien väliin |
| Mikkikolot | DXF:n humbucker-kolo korvakkeineen, 41 × 85,9 mm, 22 mm syvä; keskipisteet x = 491,7 ja 587,9 |
| Säätöruuvien syvennykset | Ø 6 mm, 8 mm kolon pohjan alle, ±39,95 mm keskilinjasta |
| Talla | Kahler 7300, ruuvattava: ei tappireikiä eikä jousikoloa; levyn kolo 55 × 65 mm, 25 mm syvä |
| Potikkakolo | DXF:n manteli tallan takana, takaa 36 mm (8 mm puuta kanteen), kansiura 2 mm |
| Kytkinkolo | DXF:n ympyrä Ø 44 yläsakaran juuressa, takaa 36 mm, kansiura Ø 59,5 × 2 mm |
| Akselireiät | Kytkin Ø 12,7; potikat 2 × Ø 10 kohdissa (642, 86) ja (682, 87) |
| Jakki | Ø 12,5 poraus reunasta (742, 107,5) suuntaan 202,5°, 55 mm, päättyy potikkakoloon |

## CNC

| Kohta | Speksi |
| --- | --- |
| Kone / ohjain | TwoTrees H40 / GRBL |
| Yleisterä | 6 mm päätyjyrsin, enintään 3 mm Z-askel |
| Nauhauraterä | 0,6 mm, vain nauhauriin, enintään 1 mm Z-askel |
| Viimeistelyvara | 0,30 mm |
| Työjärjestys | Kalibrointilevy → testipalikka → Prototype001 |
| Rungon G-koodi | `Body_index_pins.nc` → `Body_top.nc` → käännä keskilinjan ympäri tapeille → `Body_back.nc` |
| Nollapiste | X/Y kohdistustappi 1, Z aihion yläpinta kummassakin asetuksessa; jokainen ohjelma alkaa ja päättyy tapin päällä |
| Kohdistustapit | 2 × Ø6 keskilinjalla aihion hukkapuussa: tappi 1 sarvien välissä kaulataskun edessä, tappi 2 perän lovessa — eivät koskaan valmiissa kappaleessa; ≥ terä + 3 mm puuta joka leikkaukseen, ≥ 8 mm aihion reunasta; paikat `build.json`:ssa |
| Tarkistus | jokainen ohjelma ajaa ennen karan käynnistystä tappi 1 → tappi 2 → tappi 1 turvakorkeudella |
| Aihio | vähintään 496 × 324 × 44 mm (ääriviiva + 15 mm joka puolelle) |
| Ääriviiva | puolet paksuudesta + 0,5 mm kummaltakin puolelta; takapuolella 6 kpl 8 × 4 mm pidiketappia |
| Jakin poraus | käsin/porausjigillä reunasta (ei G-koodissa) |
| Kaulan G-koodi | `Neck_index_pins` → `Neck_top` (kaularauta, lavan pinta 8°, viritinreikien merkit) → käännä → `Neck_back_rough` (6 mm tasa) → `Neck_back_finish` (6 mm pallo, 0,75 mm askel) → `Neck_back_outline` (tapit) |
| Kaulan aihio | 40 mm paksu, höylätty; yläpinta = otelaudan liimapinta; 2 mm nahka pitää kaulan kehyksessä |
| Viritinreiät | vain 0,5 mm keskimerkit lavan pintaan — porataan pylväsporalla 8° kiilalla kohtisuoraan lapaan |
| Otelaudan G-koodi | `Fretboard_index_pins` → `Fretboard_radius` (pallo) → `Fretboard_inlays` (1 mm) → `Fretboard_slots` (0,6 mm, 3 × 0,9 mm sädettä seuraten) → `Fretboard_outline` (tapit) |
| Otelaudan aihio | 7 mm; harja 1 mm aihion pinnan alle |

## Mallinnuksen tämänhetkinen tila

- FreeCAD on ensimmäinen CAD-backend; geometria pidetään mahdollisimman
  CAD-riippumattomana.
- Build tuottaa `.FCStd`-, `.step`-, Python/Macro- ja JSON-raporttitiedostot.
- Otelauta, nauhaurat, inlayt, kaularautakanava, viritinreiät, kanta, lapa ja
  runko koloineen ovat mallinnettuina; STEP sisältää kaulan, otelaudan ja
  rungon erillisinä solideina.
- Rungosta puuttuvat vielä johtokanavat kolojen välillä, kansilevyt ja
  reunapyöristykset.
- Rungon 2.5D-G-koodi, kaulan 3D-rouhinta ja pallojyrsinviimeistely sekä
  otelaudan säde, inlayt, nauhaurat ja ääriviiva syntyvät samasta
  parametrijoukosta ilman FreeCADia (`cncguitarwizard.cam`); yhteensä 13
  ohjelmaa. Yksinkertaistukset: satulahyllyn U-muoto, lavan juuren
  pyöristykset ja spoke wheel -kolo eivät ole G-koodissa.
- Kaulan lapa-pään tarkastusmuoto on 12 mm syvä sylinterillä tehty U.
  D-muodon ja U:n liittymä pyöristetään vain sylinterin kahdelta
  pystysivulta, missä ne kohtaavat nykyisen kylkipyöristyksen. U:n keskikaari,
  päät, keskipiste, säde, syvyys ja 5 mm satulahylly eivät muutu.

## Periaatteet

- Vain millimetrit.
- Parametrinen, toistettava ja valmistus ensin.
- CAD, CAM ja lopulta G-koodi samasta parametrijoukosta.
- **Measure twice. Generate once.**
