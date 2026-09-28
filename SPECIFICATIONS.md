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
| Vinot nauhat | Valinnainen `fret_slant_angle` (oletus 0°, enintään 10°): nauhat, otelaudan satulapää ja loppupää kallistuvat keskilinjan ympäri, diskanttipää kohti tallaa positiivisella kulmalla. Nauhajako pysyy tarkkana keskilinjalla; talla ja mikit pysyvät ennallaan |
| Multiscale | Valinnainen `bass_scale_length`: `scale_length` on silloin diskanttimensuuri ja `bass_scale_length` bassomensuuri (pidempi, enintään 1,15-kertainen); `perpendicular_fret` (oletus 7, 0 = satula) on kohtisuorassa. Jokainen nauha on suora ja osuu jokaisella kielellä tarkalleen oikeaan kohtaan; keskilinja saa mensuurien keskiarvon. Talla voi olla mikä tahansa: se pysyy suorana keskilinjan mensuurin kohdalla ja tallapalat säädetään kunkin kielen mensuuriin (säätövaran on riitettävä puoleen mensuurierosta kumpaankin suuntaan). Poikkeus on Tune-o-matic, jonka säätövara on liian pieni: sen tolpat (kohta, jolla kielet lepäävät) käännetään aina nauhojen mukaan, stop tail pysyy paikallaan. Hardtailin läpivientireiät voi kääntää samoin (`body_bridge_follows_fan`). Mikkien kääntö on valinta (`body_pickups_follow_fan`): auto kääntää ne paitsi Tune-o-maticin kanssa, yes aina, no ei koskaan |
| Satulahylly vinolla satulalla | Pitenee satulapään vinouden verran, jotta satulalle jää 5 mm siltäkin puolelta, jolla satulapää on taaimpana; hylly on tasainen koko pituudeltaan |
| Inlayt vinoilla nauhoilla | Seuraavat nauhoja: blockit kallistuvat nauhojen mukana, piikkilanka kääntyy nauhojen kulmaan, pisteet siirtyvät nauhojen väliselle linjalle |
| Inlayt | 2 mm syvät välissä 3, 5, 7, 9, 15, 17, 19, 21 (12 ja 24 kaksois-); tyyli `inlay_style`: piikkilanka (oletus), pyöreä dotti (Ø 6) tai Gibson-tyylinen kapeneva blokki (yksi/väli, 60 % nauhavälistä, 5 mm reunasta) |

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

## Soitin

Lomakkeen ensimmäinen valinta on soitin: sähkökitara (oletus), 7-kielinen,
8-kielinen tai bassokitara (`Prototype001Parameters.for_instrument`).

7-kielisen oletukset: 25,5" (647,7 mm) skaala, satula 48 mm, kanta 66 mm,
otelaudan säde 400 mm, 7 viritintä rivissä (tai 4+3 / 3+4) ja seitsemän
kielen läpimenevä hardtail. 8-kielisen: 27" (685,8 mm) skaala, satula 55 mm,
kanta 76 mm, 8 viritintä rivissä (tai 4+4) ja kahdeksan kielen hardtail.
Kitaran humbuckerit ja singlet pitenevät 12 mm jokaista kuudennen yli
menevää kieltä kohden, ja runko levenee keskilinjasta saman verran
(`body_widening`, tyhjänä 12 mm / lisäkieli), jotta leveämpi kanta ja mikit
mahtuvat. Kahler 7300, Floyd Rose ja Tune-o-matic on mitoitettu kuudelle
kielelle, joten ne eivät ole valittavissa 7- ja 8-kielisille.
 Basson oletukset:
4 kieltä, 34" (863,6 mm) skaala, 21 nauhaa, satula 38 mm ja kanta 62 mm,
paksuudet 21 / 23 mm ja kanta 22 mm, otelaudan säde 305 mm, kielijako 10 mm
satulassa ja 19 mm tallassa, neljä 19 mm viritinreikää rivissä 38 mm välein
ja 20 mm reunasta, Precision-mikki kaulassa ja Jazz-mikki tallalla,
nelikielinen läpimenevä talla ja Jazz Bass -henkinen runko. Mikkityypit ovat
valittavissa kummallekin paikalle (humbucker, Jazz Bass, Precision Bass,
bassohumbucker tai ei mikkiä). Bassoarvot ovat lähtöarvoja.

## Kaulan kiinnitys

Neljä kaulapulttia rungon takaa: holkkiupotus Ø 14 mm, 5 mm syvä, ja sen
pohjasta Ø 5 mm pulttireikä kaulataskuun. Paikat kaulan suunnassa tulevat
rungon muodosta (`neck_bolts`), muuten 32 mm välein heel-päädyn lähellä.
Takimmaiset pultit ovat niin lähellä kaulataskun päätä kuin 3 mm puuta
pultin reiän ja kaulan pään välissä sallii (`body_neck_bolt_end_wall`,
5,5 mm päädystä), jotta pultit ovat mahdollisimman kaukana toisistaan
kaulan suunnassa ja pitävät kaulan paremmin; lähemmäs ei mikään pultti
saa tulla.
Poikittain jokainen pultti siirretään niin lähelle kaulan reunaa kuin voi,
jotta ne pysyvät kaukana kaularaudasta: reiän ja kaulan reunan väliin jää
5 mm (`body_neck_bolt_edge_wall`), tai cutawayn kohdalla holkin ja rungon
reunan väliin 1 mm puuta. Holkki saa ulottua kaulataskun ohi, mutta sen on
oltava rungossa. Kaularaudan kanavaan tai mutterin taskuun jää vähintään
3 mm ja holkkien väliin 1 mm. Design by Jone -rungossa diskanttipuolen pultit
ovat syvän cutawayn takia kannan pään lähellä (x = −24 ja −6). Piirtoeditorissa
pultteja voi raahata kaulan suunnassa.

## Kontrollit ja kannet

Kontrollikolot valitaan (`body_controls`): Design by Jone -manteli kahdella
potikalla (oletus), Gibson-tyylinen kolo neljällä potikalla, takakolo kolmella
potikalla rivissä, Telecaster-tyylinen kontrollilevy rungon päälle upotettuna
(2 potikkaa ja teräkytkimen aukko) tai ei kontrolleja. Takakoloissa on
myös pyöreä kytkinkolo. Kolot ajetaan omissa ohjelmissaan
(`Body_back_controls.nc`, Telellä `Body_top_controls.nc`). Jos Gibson- tai
rivikolo osuisi syvään yläpuolen koloon (esim. Floydin hienosäätimien
kolo) niin, ettei välissä jää puuta, kolo potikoineen ja kansineen siirtyy
lähimpään vapaaseen paikkaan, enintään 20 mm ulospäin ja kaulan suunnassa. Kansien ruuvit
(4 kontrollikanteen, 3 kytkinkanteen) merkitään kansiupotuksen reunalle Ø 3 mm,
1 mm syvä. Jokainen kansi ja kontrollilevy saa oman `Cover_<nimi>.nc`
-ohjelmansa pleksistä tai muovista leikattavaksi: 3 mm terä, reiät ja aukot
ensin, sitten ulkoreuna 0,2 mm upotusta pienempänä neljällä pidikkeellä;
nollapiste kannen keskellä levyn pinnalla.

Valinnainen 9 V:n paristokotelo (`body_battery_box`, oletuksena pois)
jyrsitään takaa samaan `Body_back_controls.nc`-ohjelmaan: 56 × 30 mm kolo
(r 5), 22 mm syvä takapinnasta, ja sen ympärillä 7 mm leveämpi
kansiupotus (70 × 44 mm). Kansi kiinnitetään kahdella ruuvilla kolon
päistä ja leikataan omana `Cover_battery_cavity.nc`-ohjelmanaan. Kotelon
paikka on rungon muodossa (`battery_offset`, `battery_y`,
`battery_angle_degrees`), ja jokaisella pohjalla se on oletuksena niin
lähellä kontrollikoloa (kolojen väli 18–32 mm), jotta
johdon reikä jää lyhyeksi; editorissa kotelon voi raahata. Pariston johdon kanava
ohjainkoloon porataan käsin. Kahden takakolon kansiupotukset eivät saa
mennä päällekkäin, eikä mikään reikä saa avautua paristokoteloon.

## Mikit

Mikkikokoonpano valitaan (`body_pickups`): kitaralle HH (oletus), HSH, HSS, H,
SSS tai SS, bassolle PJ (oletus), JJ, P tai MM; "custom" ottaa jokaisen
paikan (kaula, keski, talla) tyypin omasta parametristaan. Single coil -kolo
on 20 × 88 mm pyöreäpäinen; keskimikki on oletuksena kaula- ja tallamikin
välisen raon keskellä (`body_middle_pickup_offset` siirtää sen), tallan
single coil on 10° kulmassa diskanttipää tallaa kohti
(`body_bridge_single_coil_angle`), ja piirtoeditorissa
sitä voi raahata kaulan suunnassa.

## Lapa

| Kohta | Speksi |
| --- | --- |
| Muoto | Oma, moderni malli; `headstock_style` valitsee 3+3 (oletus), 6 rivissä bassopuolella tai diskanttipuolella (`6_inline`, `6_inline_reverse`) tai 4+2 / 2+4. Reunat seuraavat viritinreikiä 15 mm:n päässä (`tuner_edge_offset`), mutta rivityyleissä aihioon jää varapuu: 6 rivissä Strat-lobelle vastakkaisella puolella (hartia 71, kärki 62 mm), 4+2:ssa Music Man -muodolle (hartia 76, kärki 45 mm) |
| Pituus | 150 mm; kasvaa automaattisesti, kun viritinrivi tarvitsee (6 rivissä 195 mm) |
| Kulma | 8° (`headstock_angle`, 0–90°). Lapa on aina 16 mm paksu. Satula liimataan sekä otelaudan päähän että kaulaan: kaulassa on satulan kokoinen 5 mm tasainen istukka liimapinnan tasossa (vinolla satulalla tasalevyinen kaistale satulalinjan takana), ja sen takaa kaula laskee 12 mm siirtymällä (`headstock_face_transition`) lavan pintaan ilman porrasta: kallistetulla lavalla pehmeä S-kaari, suoralla lavalla Strat-tyylinen kovera kuppi 4 mm alas. Lavan pinta on aina kohtisuorassa kaulaan nähden ja kallistus alkaa istukan takareunasta; vinolla satulalla vain siirtymä seuraa satulaa. 0° on suora Fender-tyylinen lapa, jonka pinta jyrsitään satulahyllyn takaa 4 mm liimapinnan alle (`headstock_face_drop`), jolloin 16 mm lapa on 20 mm:n alaosassa otelaudan alapinnasta ja kielet saavat kulman virittimille |
| Paksuus | Säädettävä 14–16 mm; oletus 16 mm |
| Hartialeveys | reikien mukaan (3+3: 61,7 mm; 65 mm reunalla, jolla ei ole virittimiä) |
| Kärjen leveys | reikien mukaan (3+3: 42,5 mm; 40 mm reunalla, jolla ei ole virittimiä) |
| Virittimet | 6 × 10 mm läpireikää; rivissä 25,4 mm jaolla 50 mm:stä alkaen; rivityyleissä tapit kielten suorilla linjoilla (kielet eivät taitu satulassa): kuutosrivi kulkee vinosti keskilinjan yli ja sen reuna seuraa tappeja 15 mm:n päässä, 4+2:n pari lavan juuressa rivin kahta ensimmäistä vastapäätä; bassopuoli −Y (`headstock_bass_side`) |
| Reunapuuta viritinreiällä | Vähintään 8 mm |
| Reikäviiste | 45°, 0,2 mm |

Lavan reunat voi myös piirtää (`headstock_outline = "drawn"`): web-sovelluksen
lavaeditorissa raahataan kummankin reunan kahvoja ja kärkeä, kun virittimien
reiät pysyvät lavatyylin mukaisilla paikoillaan. Jokaisen reiän keskipisteen
on jäätävä vähintään `tuner_edge_offset` (15 mm, bassolla 20 mm) reunasta;
editori näyttää suoja-alueet ja build hylkää liian lähelle tulevan reunan.

Kaulan ja lavan takaliitos on jatkuva, matala ja peukalolle vapaa. Satulahylly
säilyy 5 mm:nä kaikissa lapaliitoksen muutoksissa.

## Kaularauta ja kohdistus

| Kohta | Speksi |
| --- | --- |
| Kaularauta | Kaksitoiminen; kanava 6 mm leveä, 7,5 mm syvä, säätöpäässä porras 7,5 × 10,5 × 14 mm (leveys × syvyys × pituus) ja tasku 9 × 11 × 32 mm |
| Pituus | Kaularaudat myydään kokonaispituuksina 20 mm:n välein (300–600 mm, `truss_rod_stock_lengths`), ja vain ohuin osa pitenee. Oletuksena valitaan pisin kaulaan mahtuva vakiopituus (24-nauhainen 25,5" kitara 440 mm, 7-kielinen 480 mm, basso 600 mm); oman raudan pituus annetaan `truss_rod_rod_length`, ja liian pitkä hylätään suosituksen kera. Säätöpää pysyy paikallaan, lyhyemmän raudan ankkuripää siirtyy. Rauta, ura, pisin mahtuva ja suositus näkyvät build-raportissa ja web-yhteenvedossa |
| Säätö | Valittava (`truss_rod_adjustment`): kannan puolen spoke wheel (oletus) tai lavan puoli |
| Säätöholkki | Säädettävät mitat: pyöreä pää Ø 15 × 6 mm rungon puolella, kaulan puolella 12 mm pitkä Ø 9 mm reikä raudan akselilla; akseli 7,5 mm liimapinnasta (mitattu, `truss_rod_axis_depth`) |
| Kannan säätö | Holkin reikä porataan käsin (CNC ei aja vaakasuoraa porausta; mukana mallissa ja G-coden ohjeissa); rungon kaulataskun päähän lovi holkin päälle, 1 mm välys, 15,5 mm syvä |
| Lavan säätö | Kanava jatkuu satulan alta; mutteri 32 mm urassa lavan pinnassa, uralle Gibson-tyylinen kansi (3 ruuvia) levystä omana NC-ohjelmanaan |
| Satulan istukka | Kannan säädössä satulahylly on tasainen koko satulan leveydeltä (myös monimensuurin vinolla satulalla). Lavan säädössä raudan tasku kulkee satulan alta, joten G-koodin ohje pyytää liimaamaan taskuun raudan päälle puisen täytepalan (esim. 9 × 5 mm) satulahyllyn tasoon ennen satulan liimausta |
| Valinnaiset aukot | Holkin reikä (`truss_rod_sleeve_bore`) ja lavan ura kansineen (`truss_rod_trough`) ovat oletuksena mukana, mutta ne voi jättää pois |
| Jyrsintä | Porras ja tasku ajetaan terän säteen (3 mm) verran naapurikolon päälle ja tasku säätöpään suuntaan, jotta pyöreä terä ei jätä kulmiin ulkonemia raudan kanttisille paloille; kanavan ankkuripää jyrsitään sellaisenaan |
| Kohdistus | 2 × 6 mm kohdistustappi kaksipuoliseen koneistukseen |

## Runko

Rungon muoto valitaan (`body_shape`): oletuksena "Design by Jone", joka on
jäljitetty omasta `assets/reference/omarunko.dxf`-piirustuksesta
(`presets/_omarunko_outline.py`), tai "Your design", jonka ääriviiva
piirretään web-sovelluksessa raahaamalla spline-ohjauspisteitä; pohjaksi
voi ladata Design by Jone -rungon, Les Paul-, Stratocaster- tai Jackson
RR -henkisen muodon (Les Paul, Stratocaster, Jackson RR ja Jazz Bass ovat
mockuppeja, eivät alkuperäisiä ääriviivoja) tai Jazz Bass -henkisen
muodon (basson oletus, myös mockup) (oletus Stratocaster); editorissa voi myös raahata kontrollikoloa
(potit mukana), yksittäisiä potteja, kytkinkoloa ja jakkia sekä liu'uttaa
mikkikoloja kaulan suunnassa, kun taas kaulatasku ja talla pysyvät
paikallaan. Kytkinkolon, pottien ja
jakin paikat kuuluvat muotoon; kolojen muodot ovat piirustuksen omia, eivät
likiarvoja. Koordinaatisto on kaulan: X satulasta perään, Y sivulle, yläpinta
Z = 0. Rungon piirteet (ääriviiva, kolot, potikat, jakki) seuraavat kannan
päätä ja tallan piirteet (tallalevyn kolo, tallamikki) mensuuria, joten
mensuurin tai nauhamäärän muutos pitää kaulan taskussaan ja tallan
mensuurilla.

| Kohta | Speksi |
| --- | --- |
| Paksuus | 44 mm laatta; reunat ja viisteet valinnaisia (alla) |
| Kaulatasku | Kaulan oma kapeneva ääriviiva + 0,15 mm välys/puoli, 79,5 mm pitkä, päättyy kannan päähän, 20 mm syvä; avautuu sarvien väliin |
| Mikkikolot | DXF:n humbucker-kolo korvakkeineen, 41 × 85,9 mm, 22 mm syvä; keskipisteet x = 491,7 ja 587,9 |
| Säätöruuvien syvennykset | Ø 6 mm, 8 mm kolon pohjan alle, ±39,95 mm keskilinjasta |
| Talla | Vaihdettava (`body_bridge`): oletus Kahler 7300 (ruuvattava, levyn kolo 55 × 65 × 25 mm); vaihtoehdot Floyd Rose Original valmistajan jyrsintäpiirustuksen mukaan (tapit Ø10 k/k 73,91, 11,9 mm skaalaviivan edellä; 95,25 mm leveä upotus, joka kapenee 71,12 mm:iin 42,44 mm:n kohdalla (pituus 79,38), jyrsitään kokonaan 6,73 mm syväksi ja syvennetään 11,18 mm:iin etummaisen 15,88 mm tappihyllyn takaa porrastaskuna sen sisällä; pohjassa 20,96 × 82,85 × 29,59 block-kolo, joka avautuu jousikoloon; takana jousikolo 123,19 × 56,64 × 16,13 + 28,19 mm syvä block-tasku ja 2 mm kansiura 8 mm kolon ulkopuolelle, johon tulee kuuden ruuvin levystä leikattava kansi omana `Cover_floyd_rose_spring_cavity.nc`-ohjelmanaan (piirustus on 44,45 mm rungolle; paksummassa rungossa jousikolo ja block-tasku syvenevät erotuksen verran, jotta block-kolo avautuu aina läpi); upotus 3,56 mm leveämpi vipupuolella), Tune-o-matic + stop bar (4 × Ø11,2 reikää) ja hardtail (6 string-through + 5 esiporausta). Floyd Rose -mitat valmistajan piirustuksesta, muut lähtöarvoja — tarkista laitteesta |
| Potikkakolo | DXF:n manteli tallan takana, takaa 36 mm (8 mm puuta kanteen), kansiura 2 mm |
| Kytkinkolo | DXF:n ympyrä Ø 44 yläsakaran juuressa, takaa 36 mm, kansiura Ø 59,5 × 2 mm |
| Akselireiät | Kytkin Ø 12,7; potikat 2 × Ø 10 kohdissa (642, 86) ja (682, 87) |
| Jakki | Ø 12,5 poraus reunasta (742, 107,5) suuntaan 202,5°, 55 mm, päättyy potikkakoloon |

## Reunat ja viisteet

Kaikki valinnaisia ja oletuksena pois: reunojen pyöristys päältä ja takaa
(`body_top_edge_radius`, `body_back_edge_radius`), pyöristyksen sijaan
reunanauhan ura (`body_*_binding_width` / `_depth`, syvyys oletuksena 6 mm),
soittokäden viiste päälle bassopuolen takakaaren kohdalle
(`body_arm_contour_*`, oletuksena 60 mm leveä ja 240 mm pitkä) ja mahaviiste
taakse bassopuolen yläkaaren kohdalle (`body_belly_cut_*`, 70 × 260 mm).
Viisteet kapenevat reunaa pitkin molempiin päihin. Viisteet ja pyöristykset
ajetaan ball nose -terällä omissa ohjelmissaan (`Body_top_edges.nc`,
`Body_back_edges.nc`), reunanauhan ura pääterällä ääriviivan jälkeen.
FreeCAD-mallissa ne ovat 1 mm porrastuksina.

## Omat suunnitelmat

Web-sovelluksen **Save design** tallentaa kaikki asetukset, myös soittimen,
piirretyn rungon ja lavan reunat, JSON-tiedostoksi omalle koneelle.
**Load design** lataa tiedoston takaisin lomakkeeseen ja editoreihin. Asetukset,
joita käytössä oleva versio ei tunne, ohitetaan ja luetellaan. Mitään ei
tallenneta palvelimelle.

## CNC

| Kohta | Speksi |
| --- | --- |
| Kone / ohjain | TwoTrees H40 / GRBL; G-koodin murre valittavissa (`post_processor`): GRBL (oletus), LinuxCNC, Mach3/4 / UCCNC, Marlin, Fanuc-tyyppinen teollisuusohjain tai KOSY / nccad (`.knc`-tiedostot, syöttö nccad:n yksiköissä mm/min ÷ 6, kara releellä 6), ja karan kiihdytysodotus (`spindle_dwell`, sekunteina, kirjoitetaan kunkin murteen yksiköissä) |
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
| Kaulan aihio | Paksuus lasketaan tarpeesta (kaulan tai lavan syvin kohta liimapinnasta; `blank_thickness` voi pakottaa paksumman). Suora lapa: 20 mm lankku riittää. Kallistettu lapa kahdella tavalla: (1) yksi paksu lankku (8°: 36,6 mm) tai (2) kaulan 20 mm lankku + lavan alle liimattava pala (8°: 152 × 78 × 16,6 mm, 33 mm satulasta aihion päähän); samat ohjelmat, liimatussa Z-nolla palan alapintaan. Yläpinta = otelaudan liimapinta; 2 mm nahka pitää kaulan kehyksessä |
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
