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
| Otelaudan reunanauha | Valinnainen (`fretboard_binding_width`, 0 = ei, enintään 3 mm): otelauta jyrsitään nauhan verran kapeammaksi kummaltakin pitkältä sivulta, ja nauha liimataan reunoihin, joten lauta ja nauha yhdessä ovat satulan ja viimeisen nauhan levyiset (kaula pysyy niissä). Nauhaurat jyrsitään laudan reunojen läpi, ja nauhojen kannat lyhennetään reunanauhan kohdalta. FreeCAD-mallissa nauhat ovat omana kappaleenaan (`FretboardBinding`) |
| Otelaudan pää | 4 mm 24. nauhan jälkeen; samassa tasossa kannan lopun kanssa |
| Satulahylly | Kiinteä 5 mm ennen otelautaa; ei saa muuttua (paitsi `nut_style` "slot": satula urassa otelaudan päässä, ks. alla) |
| Nauhaurat | 0,6 mm × 2,7 mm |
| Vinot nauhat | Valinnainen `fret_slant_angle` (oletus 0°, enintään 10°): nauhat, otelaudan satulapää ja loppupää kallistuvat keskilinjan ympäri, diskanttipää kohti tallaa positiivisella kulmalla. Nauhajako pysyy tarkkana keskilinjalla; talla ja mikit pysyvät ennallaan |
| Multiscale | Valinnainen `bass_scale_length`: `scale_length` on silloin diskanttimensuuri ja `bass_scale_length` bassomensuuri (pidempi, enintään 1,15-kertainen); `perpendicular_fret` (oletus 7, 0 = satula) on kohtisuorassa. Jokainen nauha on suora ja osuu jokaisella kielellä tarkalleen oikeaan kohtaan; keskilinja saa mensuurien keskiarvon. Talla voi olla mikä tahansa: se pysyy suorana keskilinjan mensuurin kohdalla ja tallapalat säädetään kunkin kielen mensuuriin (säätövaran on riitettävä puoleen mensuurierosta kumpaankin suuntaan). Poikkeus on Tune-o-matic, jonka säätövara on liian pieni: sen tolpat (kohta, jolla kielet lepäävät) käännetään aina nauhojen mukaan, stop tail pysyy paikallaan. Hardtailin läpivientireiät voi kääntää samoin (`body_bridge_follows_fan`). Yksikieliset tallat ovat kukin oman kielensä mensuurin kohdalla viuhkan tallalinjalla. Mikkien kääntö on valinta (`body_pickups_follow_fan`): auto kääntää ne paitsi Tune-o-maticin kanssa, yes aina, no ei koskaan |
| Lukkosatula | `locking_nut`: auto (oletus) ottaa Floyd Rose Original R2 -lukkosatulan (41,3 mm), kun tallana on Floyd Rose (7- ja 8-kielisellä Floydilla Floyd Rosen 7- tai 8-kielisen satulan), muuten tavallinen satula; none, r2, r3 (42,85 mm), r7 (47,6 mm, 6,30 mm korkea, 15,5 mm syvä, kaksi ruuvia 18,6 mm välein) tai r8 (53,8 × 15,7 mm, kolme ruuvia 13,3 mm välein) valitsevat suoraan; kukin vaatii vähintään yhtä leveän `nut_width`:n (web-lomake leventää satulan leveyden valittaessa). Satula ruuvataan päältä kahdella ruuvilla (R2/R3: 13,59 mm välein, 7,5 mm satulalinjan takana, 2,5 mm × 8 mm esiporaus käsin satulan läpi). Sen etureuna on satulalinjalla ja hylly jatkuu 16 mm taaksepäin, joten lavan pinta, siirtymä ja lavan puolen truss rod -tasku alkavat sen verran taempaa. Satulan yläpinta on 0,38 mm nauhojen yläpintaa ylempänä (`fret_height` 1,2 mm): R2:n hylly on 1,73 mm liimapinnan yläpuolella, joten otelauta jatkuu satulan alle ja jyrsitään siinä hyllyn korkeuteen; R3:n hylly jäisi alle 1 mm:n, joten se istuu kaulan omalla hyllyllä 0,48 mm shimmin päällä |
| Nollanauha | `nut_style` "zero_fret": satulalinjalle tulee nauha (mensuuri alkaa siitä), ja satula on vain kielten ohjain `zero_fret_gap` (3 mm) sen takana, urassa kuten "slot"-tyylissä ja viilattu hieman nollanauhan yläpinnan alle. Otelauta jatkuu satulalinjan ohi: väli, ura, reunus ja loivennus, yhteensä 12,5 mm. Nollanauhan ura jyrsitään `Fretboard_slots.nc`-ohjelmassa ensimmäisenä (`Zero fret slot`) ja leikataan FreeCAD-mallissa; plan-kuva ja lapaeditori piirtävät sen. Lukkosatulan (Floyd Rose, myös `locking_nut` "auto" Floyd-tallan kanssa) kanssa nollanauha säilyy: lukkosatula on `zero_fret_gap` (3 mm) nollanauhan takana ja sen yläpinta 0,25 mm nauhojen yläpinnan alapuolella (muuten 0,38 mm yläpuolella), joten kielet lepäävät nollanauhalla ja satula vain lukitsee ne. Otelauta jatkuu täyskorkeana nollanauhan alla satulan etupintaan asti, ja satulan hylly jyrsitään siitä taaksepäin; ruuvit ovat puolen satulan syvyyden päässä sen etupinnasta. Satulan on yhä seisottava otelaudan päällä (hylly vähintään 1 mm); korkeampi satula (7- ja 8-kielisten 6 mm laudalla) antaa virheen ja neuvon: paksumpi lauta, korkeammat nauhat tai ei lukkosatulaa. Lapaeditorin omassa ruudussa on satulan tyyli (`nut_style`), ja editori piirtää satulan (hyllyllä, urassa otelaudan jatkeessa, nollanauhan takana tai lukkosatulana tummana) |
| Satula urassa (Fender/Telecaster) | `nut_style` "slot": otelauta jatkuu satulalinjan ohi, ja siihen jyrsitään `nut_thickness` (3,5 mm) levyinen ura `nut_slot_depth` (3 mm) harjan alapuolelle; satula liimataan uraan, etupinta satulalinjalla. Uran takana otelauta jatkuu täyskorkeana `nut_slot_lip` (3 mm) ja loivenee sitten liimapintaan `nut_slot_taper` (3 mm) matkalla, eli otelauta päättyy 9,5 mm satulalinjan taakse. Ura jyrsitään inlay-ohjelmassa 1 mm terällä, loivennus ääriviivaohjelmassa 0,5 mm portain tasaterällä (hiotaan tasaiseksi). Uran alle on jäätävä vähintään 1 mm otelautaa. Lukkosatula korvaa urassa olevan satulan (nollanauhan kanssa se tulee nollanauhan taakse, ks. Nollanauha). Lavan puolelta säädettävä kaularauta avataan silloin Fender-tyylisesti ilman kantta (ks. Spoke wheel) |
| Satulan viilausohjain | `nut_jig` (oletuksena pois) lisää ohjaimen satulan kieliurien viilaukseen, leikattuna levystä omana `Jig_nut_slots`-ohjelmanaan: kampa, jonka paksuus (`nut_jig_thickness`, 3 mm) on sen pituus kaulan suunnassa. Se seisoo otelaudalla etupinta satulan etupintaa vasten; alapinta seuraa otelaudan sädettä laudan reunojen välissä, ja kummassakin päässä 4 mm leveä jalka ulottuu 3 mm laudan reunan alle ja halaa sitä 0,05 mm:n välyksellä, joten ohjain asettuu kaulan keskelle (jalan ja alapinnan kulmasta poistettu 1,5 mm:n neliö, johon laudan reuna mahtuu). Yläreuna kulkee säteen mukaisena `nut_jig_height` (5 mm, noin satula-aihion korkeus) laudan yläpuolella. Ylhäältä tulee jokaisen kielen kohdalle satulalla pystysuora ura, kielen paksuinen (`nut_jig_gauges`, yksi per kieli tuumina 0,010 tai tuhannesosina 10, missä järjestyksessä tahansa, paksuin bassopuolelle; tyhjä = tavallinen sarja: kitara .010–.046, 7-kielinen .010–.059, 8-kielinen .010–.074, 740 mm:stä alkaen basso .045–.105, viisikielinen .045–.130, kuusikielinen .032–.130) + `nut_jig_slot_play` (0,05 mm), nauhojen korkeuteen asti (`fret_height`, vähintään 0,5 mm). Kielen satulaviila uran läpi aloittaa satulan uran oikeaan kohtaan; viilan kallistus lapaa kohti ja kääntö virittimen tappia kohti tehdään käsin. Vinolla tai viuhkasatulalla ohjain asettuu satulan etupinnan suuntaan (paikat ja reunat `hypot(1, vinous)`-kertaisina). Ei lukkosatulan (ei uria) eikä nollanauhan kanssa (nauha on ohjaimen paikalla); hylätään myös, jos uralle jää alle 1 mm ohjausta tai ura ulottuu 0,5 mm:n päähän laudan reunasta. Ohjelma: yksi terä `nut_jig_tool_diameter` (0,6 mm, nauhauraterän koko, sen kierrokset ja Z-askel), levy kaksipuolisella teipillä ilman pidikkeitä, nollapiste ohjaimen keskellä; ensin urat (terää kapeampi ura yhtenä vetona, leveämpi seinästä seinään enintään 0,8 × terä välein), sitten ääriviiva läpi. Ohjelman muistiinpanot luettelevat urien leveydet ja ne urat, joille terä on liian leveä (0,3 mm terä leikkaa .010-kielen uran omanlevyiseksi, noin 1,5 mm levyyn); vähintään 1,4 mm terä hylätään. FreeCAD-mallissa ohjain on oma kappaleensa (`NutSlotJig`) satulan edessä otelaudalla, kaulan kallistuksen mukana; STEP-tiedostoon sitä ei viedä |
| Telecaster-kaula | Lapaeditorin *Start from* → Telecaster neck (`NECK_TEMPLATES`): satula urassa, suora 0° lapa, 6 virittimen rivi (`6_inline`), Telecaster-lavan muoto piirrettynä (204 mm oletusrivin ympärillä, muokattavissa) ja kaularaudan säätö kantapäässä (vintage); `truss_rod_adjustment` headstock antaa modernin säädön satulan takaa |
| Lapapohjat | Lapaeditorin *Start from* → Stratocaster neck, Gibson style neck, Flying V neck, Explorer neck tai Mockingbird neck (`NECK_TEMPLATES`, mockuppeja tuotekuvista jäljitettyinä, kuusikieliselle): Stratocaster suora 0° lapa satula urassa, virittimet 22,5 mm välein 51 mm:stä ja virittimien puoleinen reuna suorana tappien linjassa; Gibson 17° 3+3 "open book" -yläreunalla; Flying V 17° 3+3 kapeneva lapa pyöristettyyn kärkeen; Explorer 17° 6 rivissä "hockey stick" -lapa, jonka kärki kääntyy diskanttipuolelle (kärki muotoiltu käsin täyteläisemmäksi) ja virittimet ovat alkuperäisen tapaan 18,7 mm välein suorana rivinä jyrkkää reunaa pitkin (`tuner_inline_offsets`: rivin tappien paikat keskiviivasta annettuina, kielet taittuvat satulalla tapeille; tyhjä = tapit kielten linjoilla); Mockingbird B.C. Richin 3+3 -lapa, jonka yläreuna nousee keskeltä kärkeen (kärki piirretty käsin korkeammaksi); 3+3-lapojen virittimien asemat alkuperäisen mukaan. |
| Lavan loft | FreeCAD-malli lavasta on yksi pehmeä lofti poikkileikkausten läpi kärjestä satulaan; leikkaukset ovat enintään 3 mm:n päässä toisistaan (`MAX_HEADSTOCK_SECTION_GAP`), joten jyrkästi kääntyvä piirretty kärki mallinnetaan piirretyn mukaisena eikä lofti kierry kiemuralle |
| Runkopohjan lataus | Runkoeditorin *Start from* -valinta lataa pohjan heti (*Load* lataa sen uudelleen, peruutus palauttaa valinnan). Edellisen pohjan muodon ulkopuoliset arvot (Alexi Hexedin yksi mikki, yksi volume, Floyd Rose ja porrastettu kansi) palaavat oletuksiin, jos ne ovat yhä sellaisina kuin pohja ne jätti; itse muutettu arvo säilyy |
| Kaulapohjan lataus | *Start from* -valinta lataa kaulapohjan heti (myös `headstock_style`; *Load* lataa sen uudelleen, peruutus palauttaa valinnan), ja pohjan asettamatta jättämät virittimien ja kärjen asetukset palaavat oletuksiin (`NECK_TEMPLATE_RESETS`), joten edellisen pohjan virittimien paikat tai kärki eivät jää voimaan |
| Lapaeditori ja vanha piirros | Piirretty lapa on sen reunat: sovitetun ääriviivan leveyksiä ei tarkisteta sille, joten pitkä `headstock_length` ei estä piirrettyä lavaa. Tallennettu piirretty lapa, johon virittimet eivät enää mahdu (mensuurin tai satulan muutos siirtää rivin tappeja reunaa kohti), tai jonka reunat ristevät, aukeaa lapaeditoriin: ongelma näkyy punaisella, kaiverrus piirretään lavalle kunnes reunat korjataan, ja *Start over* palauttaa aina sovitetun lavan |
| Lavan virheet | Lapa, jota ei voi piirtää, nimeää korjattavan asetuksen: sovitettu ääriviiva kapenee kärjessä olemattomiin (3+3:n reunat suppenevat, joten `headstock_length` kauas virittimien ohi, oletuksella noin 370 mm: lyhennä sitä, tuo viimeinen viritin lähemmäs satulaa tai anna `headstock_tip_width`), tai satulan, juuren, olkapään tai kärjen leveys ei ole positiivinen. Lapaeditori kertoo myös, jos `tuner_inline_offsets` ei sovi tyylin riviin tai lukkosatula on kaulaa leveämpi |
| Satulahylly vinolla satulalla | Pitenee satulapään vinouden verran, jotta satulalle jää 5 mm siltäkin puolelta, jolla satulapää on taaimpana; hylly on tasainen koko pituudeltaan |
| Inlayt vinoilla nauhoilla | Seuraavat nauhoja: blockit kallistuvat nauhojen mukana, piikkilanka kääntyy nauhojen kulmaan, pisteet siirtyvät nauhojen väliselle linjalle |
| Inlayt | 2 mm syvät välissä 3, 5, 7, 9, 15, 17, 19, 21 (12 ja 24 kaksois-); tyyli `inlay_style`: piikkilanka (oletus) tai pyöreä dotti (Ø 6), joista 12. ja 24. nauhalla kaksi; piikkilanka 2 (`barbed_wire_2`): rakentajan piirroksesta (`barbedwiretrue.dxf`) jäljitetty piikkilangan solmu yhtenä palana, kaksi kierrettyä lankaa, kolme kierrettä ja neljä piikkiä, laudan poikki 80 % sen leveydestä, yksi jokaisella merkkinauhalla (myös 12. ja 24.), lyhyissä nauhaväleissä pienempänä 1,5 mm nauhoista; tai yksi otelaudan yli ulottuva kuvio nauhavälissä (60 % nauhavälistä, 5 mm reunasta, kapenee otelaudan mukana): Gibson-blokki, Les Paul -trapetsi (pitkä bassopuolella, diskanttipuoli 55 %), Jackson-sharktooth (kolmio, kärki diskanttipuolella), suunnikas, vinoneliö tai Gibson split block (blokki halkaistu lävistäjää pitkin kahdeksi palaksi 1,5 mm välein); tai oma piirretty kuvio (`custom`, ks. Piirretty inlay) |
| Piirretty inlay | `inlay_style` "custom": kuvio piirretään kerran ensimmäisen merkin nauhaväliin web-sovelluksen inlay-editorissa (*Inlay design*, lapaeditorin alla), kulmat `inlay_points`-listana `[pitkittäin, poikittain]`: pitkittäin 0 satulan puoleinen nauha ja 1 merkin oma nauha, poikittain osuus otelaudan puolikkaasta leveydestä bassoreunaa kohti (−1…1). Kulmat yhdistetään suorilla ja pyöristetään 1 mm. Jokainen merkki on sama kuvio sovitettuna omaan nauhaväliinsä ja otelaudan leveyteen siinä, eli merkit lyhenevät runkoa kohti ja levenevät otelaudan mukana. Vähintään 3 kulmaa, sivut eivät saa leikata toisiaan, ja jokaisen merkin jokaisen kulman on jäätävä 1 mm (`CUSTOM_CLEARANCE`) nauhaurista ja reunoista; muuten virhe kertoo nauhan. Editori näyttää katkoviivalla alueen, jossa kuvio mahtuu jokaiseen merkkiin (`custom_limits`: lyhin nauhaväli ja kapein kohta), ja raahaus pysähtyy siihen. Editori aloittaa valitun tyylin merkistä (`editable_points`), ensimmäinen muokkaus vaihtaa tyyliksi custom; *Start over* palauttaa blokin. Tyhjä `inlay_points` = blokki |

## Kanta ja kiinnitys

| Kohta | Speksi |
| --- | --- |
| Kannan puupaksuus | 20 mm otelaudan alla |
| Tasainen kiinnitysalue | Säädettävä, vähintään 40 mm; Prototype001: 54 mm |
| Kannan alapuoli | Tasainen runkoon kiinnittämistä varten |
| Kannan sivut | Suorakulmaiset: kiinnitysalueen poikkileikkaus on suorakaide (sivut pystysuoraan liimapinnasta täyteen syvyyteen, pohja tasainen reunoihin asti), joten kanta sopii kaulataskun suoriin seiniin ilman pyöristettyjä reunoja |
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
8-kielinen, bassokitara, 5-kielinen basso, headless-kitara tai
headless-basso (`Prototype001Parameters.for_instrument`). Headless-soittimissa
(`headless`) ei ole lapaa eikä virittimiä: kaula päättyy 35 mm satulan taakse
(`headless_length`, 25–80 mm) tasaiseen, satulan levyiseen päähän
liimapinnan tasossa, johon kielten kiinnitin ruuvataan, ja kielet viritetään
headless-tallasta (`HeadlessBridgeSpec`, `kind` "headless"): tallan ja
virittimien yhteinen levy ruuvataan kannen päälle neljällä ruuvilla
levyn kulmiin (pilottireiät 3 × 12 mm), levy 12 mm satulalinjan edessä,
90 mm pitkä ja 10 mm uloimpien kielten ulkopuolelle (kitara 6 × 10,5 mm,
basso 4 × 19 mm kielijako). Levy on tallan ala, jonka pleksi ja kaiverrus
väistävät, ja sen on mahduttava rungolle. Headless-kitarassa
tallamikki on 38 mm tallalinjan edessä, jotta se jää 6 mm irti levystä. Muut
arvot ovat kitaran ja basson. 5-kielinen basso on 4-kielisen
oletukset 47 mm satulalla (kielijako 9,5 mm), 18 mm kielijaolla tallassa,
77 mm kannalla, 4+1-lavalla (Jazz V -tyyli; myös 3+2, 2+3, 1+4 ja 5 rivissä)
ja viisikielisellä tallalla; sen Jazz-mikin kolo on Warmothin 5-kielinen
4-1/8" (104 mm).

7-kielisen oletukset: 25,5" (647,7 mm) skaala, satula 48 mm, kanta 66 mm,
otelaudan säde 400 mm, 7 viritintä rivissä (tai 4+3 / 3+4) ja seitsemän
kielen läpimenevä hardtail. 8-kielisen: 27" (685,8 mm) skaala, satula 55 mm,
kanta 76 mm, 8 viritintä rivissä (tai 4+4) ja kahdeksan kielen hardtail.
Kitaran humbuckerit ja singlet pitenevät 12 mm jokaista kuudennen yli
menevää kieltä kohden, ja runko levenee keskilinjasta saman verran
(`body_widening`, tyhjänä 12 mm / lisäkieli), jotta leveämpi kanta ja mikit
mahtuvat. Kahler 7300 ja Floyd Rose saa 6-, 7- ja 8-kielisinä
(`string_count` tallan omissa tiedoissa, pidetään soittimen kielimäärässä;
web-lomake pitää sen samana). Floydin leveydet seuraavat tappien väliä
samoin marginaalein kuin Floyd Rosen 6- ja 7-kielisissä
jyrsintäpiirustuksissa (seinät 8,89 / 12,45 mm tappien ulkopuolella,
lohkon kolo 8,94 mm tappiväliä leveämpi, hienosäätimien osa 2,79 mm
kapeampi): 7-kielinen tappiväli 84,58 mm, upotus 105,92 mm, lohkon kolo
93,52 mm ja hienosäätimet 81,79 mm; piirustuksen mukaan ei syvempää
lohkotaskua jousikolon pohjan alle (ohjeet kertovat, miten jousikolon
takapäätä syvennetään käsin, jos lohko koskee syvässä sukelluksessa).
8-kielisestä Floyd Rose ei julkaise jyrsintäpiirustusta: se on 7-kielinen
levennettynä FRT8:n 95,5 mm tappiväliin. Pituudet ja syvyydet ovat samat
kuin 6-kielisessä. Tyhjäksi jätetyt leveydet tulevat kielimäärästä
(`FloydRoseSpec.widths()`). Kahler 7327/7328:n (7 ja 8 kieltä) kolo on
20,32 mm leveämpi, 85,36 mm, kuten Kahlerin asennusohjeissa (3,400" vs.
2,600"). Tune-o-matic on mitoitettu kuudelle kielelle, eikä sitä voi
valita 7- ja 8-kielisille.

Yksikieliset tallat (`SingleStringBridgeSpec`, `kind` "single_string"):
jokaisella kielellä on oma pieni talla (oletuksena ABM 3710 -tyylinen
bassotalla 60 × 15 mm, 19 mm kielijako). Kukin ulottuu 15 mm kielensä
mensuuripisteen eteen, ja siinä on kaksi 3 × 12 mm ruuvin esiporausta
keskilinjalla 6 mm päistä sekä halutessa 4 mm kielen läpivienti 30 mm
mensuuripisteen takana. Multiscalessa jokainen talla on oman kielensä
mensuurin kohdalla viuhkan tallalinjalla, silti suorassa kieleensä nähden,
joten talla seuraa viuhkaa kääntymättä. Tallojen yhteinen ala on
tallan levy, jota pleksi väistää. Talla ei saa olla kielijakoa leveämpi.
Hardtailin voi asentaa myös top-load-tyyliin (`string_through` pois): kielet
kulkevat tallan takaosan läpi eikä runkoon porata läpivientejä
(useimmat bassotallat käyvät kumminkin päin). Jokaisen rungon läpi menevän
kielireiän (myös yksikielisten tallojen) alle porataan takaa holkin upotus
`body_string_ferrule_diameter` × `body_string_ferrule_depth` (kitara 8 × 6 mm
eli 5/16", basso 9,5 × 6,5 mm eli 3/8"; syvyys 0 = käsin) `Body_back`-ohjelmassa,
ja holkki peittää sen. Tallojen asennusmuistiinpanot (reitityspiirros, mitä
tarkistaa, mitä tehdään käsin) näkyvät `Body_top`-ohjelman
muistiinpanoissa. Sivuttain käsin porattavat reiät (CNC ei poraa
vaakasuoraan) mallinnetaan: Floydin trem-clawn kaksi ruuvia, 3,5 mm
pilotit 4,2 mm ruuveille (`claw_screw_diameter`) 30 mm syvälle
(`claw_screw_depth`) jousikolon kaulanpuoleiseen seinään kaulan suuntaan,
34 mm välein (`claw_screw_spacing`, Gotohin clawn) ja oletuksena kolon
puolessa välissä takapinnasta (`claw_screw_height`); ne näkyvät
FreeCAD-mallissa, plan-kuvassa ja DXF:n `SIDE_HOLES`-tasolla, ja ne
tarkistetaan pysymään rungossa ja irti muista koloista. 7- ja 8-kielisen Floydin piirroksessa ei
ole jousikoloa syvempää taskua; jos lohko koskee syvässä divessä, `block_pocket_depth`
28,19 (6-kielisen piirroksen) jyrsii sen kolon peräpäähän kannen alle.
 Basson oletukset:
4 kieltä, 34" (863,6 mm) skaala, 21 nauhaa, satula 38 mm ja kanta 62 mm,
paksuudet 21 / 23 mm ja kanta 22 mm, otelaudan säde 305 mm, kielijako 10 mm
satulassa ja 19 mm tallassa, neljä 19 mm viritinreikää rivissä 38 mm välein
ja 20 mm reunasta, Precision-mikki kaulassa ja Jazz-mikki tallalla (kolot
Warmothin piirustusten mukaan: J 96 × 20 mm, kummassakin kyljessä kaksi
pyöreää koloa, joissa ruuvien paikat mikin kylkien ulkopuolella (94,4 × 18,2 mm
mikki mahtuu niiden väliin); P kaksi 58 × 28,5 mm kelaa, joiden molemmissa päissä pyöreä
ruuvikorva, yhteensä neljä),
nelikielinen läpimenevä talla ja Jazz Bass -henkinen runko, jonka
kaulapultit ovat 56 mm välein kaulan suunnassa (`body_neck_bolt_spacing_x`;
kaulataskun suun puoleinen pari on lähellä rungon reunaa, ja taaempi pari
on 5 mm taskun päästä (`body_neck_bolt_end_wall`), jolloin sen holkit ovat
kokonaan taskun kohdalla). Stratocaster-pohjassa pultit ovat samoin, ja
Jackson RR -pohjassa etummainen pari on niin ulkona kuin kapeat siivet
sallivat (bassopuolella 50 mm, diskanttipuolella 44 mm kannan päästä). Mikkityypit ovat
valittavissa kummallekin paikalle (humbucker, Jazz Bass, Precision Bass,
bassohumbucker tai ei mikkiä). Bassoarvot ovat lähtöarvoja.

## Vasenkätinen

Kaikki runkopohjat ja oletuskaula on piirretty oikeakätisiksi: edestä
katsottuna lapa vasemmalla bassopuoli, pitkä sarvi ja kytkin ovat −Y:ssä,
säätimet ja jakki +Y:ssä. `handedness = "left"` (lomakkeen Instrument-
ryhmässä) rakentaa soittimen peilikuvan keskilinjan yli, ja suunnitelma
tallennetaan edelleen piirrettynä, joten sama suunnitelma ja pohja käyvät
kummallekin kädelle:

- rungon muoto (`mirrored_shape`): kytkin, potentiometrit, jakki ja sen
  suunta, säädinkolon siirto ja kulma, kaulapultit, paristokotelo ja sen
  kulma, piirretty suojalevy, kyynärviiste ja mahaviiste peilataan, ja
  piirretyt vakiomuodot (Design by Jone -ääriviiva, mantelikolo ja sen
  kansi) `mirrored`-lipulla;
- bassopuoli (`bass_sign`): mikit ja niiden vino, talla (Tune-o-maticin
  taaempi bassotolppa), viuhkanauhojen pitkä puoli, nauhat, otelaudan
  merkit, lavan virittimet, automaattinen suojalevy ja viisteet;
- Floyd Rosen vipupuoli (`treble_side`);
- piirretty lavan kärki ja lavan tekstin paikka. Teksti ladotaan
  uudestaan, sitä ei peilata: se kulkee kulmassa 180° −
  `headstock_engraving_angle`, joten se on oikeakätisen tekstin peilikuvan
  paikalla, kirjainten yläreuna samalla puolella, ja luettavissa.

Runko- ja lapaeditori piirtävät suunnitelman piirrettynä ja näyttävät sen
peilattuna vasenkätiselle (yksi käännetty SVG-ryhmä, jonka läpi myös
raahaus luetaan); editorin tekstin esikatselu on rakennettu teksti
peilattuna takaisin, joten se näkyy luettavana. Aiemmin koodi ja
dokumentit kutsuivat oletusta virheellisesti vasenkätiseksi.

## Liimattu kaula

`neck_joint = "set"` liimaa kaulan kantapään taskuun Gibson-tyylisesti
pulttaamisen sijaan: ei kaulapultteja eikä hylsyjä, ja tasku on vain
`set_neck_glue_gap` (0,05 mm) sivulle kantapäätä leveämpi tiukkaa
liimasaumaa varten (pulttikaulan tasku 0,15 mm). Kaulan kulma toimii
kuten pulttikaulassa (taskun pohja viettää; esim. Les Paulin 4°). Kaula
ei enää irtoa, joten kantapäästä säädettävä kaularauta vaatii
säätöpyörän, jota käännetään rungon loven kautta; kaulan muistiinpanot
neuvovat liimaamaan ja puristamaan kaulan paikalleen, kun se on valmis ja
nauhoitettu. Pitkää, kaulamikin alle ulottuvaa kielekettä (long tenon)
ei mallinneta.

## Läpikaula

`neck_joint = "neck_through"` jatkaa kaula-aihion rungon läpi: rungon
ääriviiva kahden liimalinjan `Y = ±neck_through_width / 2` välissä on
kaula-aihion **keskiosa**, niiden ulkopuolella kaksi **siipeä**
(`Wing_bass`, `Wing_treble`), jotka jyrsitään kukin omasta aihiostaan ja
liimataan keskiosan kylkiin. Tyhjä `neck_through_width` tekee keskiosasta
niin leveän, että mikkien ja tallan kolot ja reiät (ja kaulan kanta)
mahtuvat siihen 3 mm (`NECK_THROUGH_MARGIN`) puuta vierellään: kahdella
humbuckerilla 92 mm, Tune-o-maticin kanssa 99 mm. Rungossa ei ole
kaulataskua eikä kaulapultteja. Kaulan selkä pitää D-profiilinsa ja
laskeutuu sitten rungon paksuuteen `neck_through_heel_ramp` (40 mm)
matkalla, saavuttaen sen siinä, missä runko kohtaa kaulan kyljet. Kaulan
kulmaa ei ole (Tune-o-maticin automaattinen 2° on tässä 0), ja
kantapäästä säädettävä kaularauta vaatii säätöpyörän, koska kantapään
mutteri jäisi keskiosan sisään. Päätön kaula on toistaiseksi vain
pulttikaulana.

Jokainen osa jyrsitään vähän osaa suuremmasta aihiosta: se saa jokaisen
siihen ulottuvan kolon ja reiän kokonaan (liimalinjan ylittävä säädinkolo
jyrsitään kumpaankin osaan, toinen puoli kummankin hukkapuuhun),
kaareutuksen ja viisteet kokonaan, kaiverruksen ulottuvilta osin ja
reunan pyöristyksen ja reunanauhan ääriviivaa pitkin, joka jatkuu 12 mm
liimalinjan yli hukkapuuhun — liimapinnat jäävät suoriksi. Ääriviivan
profiili lopuksi leikkaa hukkapuun pois.

Kaula-aihio on läpikaulassa tasan rungon paksuinen ja ulottuu lavan
kärjestä rungon häntään (ohjaustapit lavan kärjen eteen ja keskiosan
hännän taakse). Sen selkä jyrsitään vain kaulan ja lavan leveydeltä ja
vain rungon alkuun asti; `Neck_back_outline` leikkaa koko ääriviivan
täyteen syvyyteen kielekkeineen. Keskiosan kolot jyrsitään rungon
ohjelmilla samoilla tapeilla (`Neck_block_top` ym. yläpuoli ylöspäin,
`Neck_block_back...` kaulan selän jälkeen). Siivet saavat rungon ohjelmat
omille aihioilleen (`Wing_bass_...`, `Wing_treble_...`), tapit kunkin
siiven keskilinjalle. FreeCAD-malli rakentaa rungon kokonaisena ja jakaa
sen liimalinjoja pitkin: `Neck_block` (yhtä puuta kaulan kanssa, oma
objektinsa, koska kaulan loftin pinnat ovat keskiosan ylä- ja alapinnan
tasossa ja yhdistäminen epäonnistuu), `Wing_bass` ja `Wing_treble`.
Plan-kuva ja runkoeditori piirtävät keskiosan vähän tummempana.


### Yksiosainen

`neck_joint = "one_piece"` jyrsii kaulan ja koko rungon samasta
aihiosta: kuin läpikaula, jonka keskiosa on koko runko, ilman siipiä ja
liimasaumoja. Aihio ulottuu lavan kärjestä rungon häntään ja on rungon
levyinen (oletuskitara 995 × 364 × 44 mm, Les Paul -pohja 1053 × 398 mm).
Kaula-aihion ohjelmat jyrsivät rungon kolot samoilla tapeilla
(`Neck_body_...`) ja koko ääriviivan täyteen syvyyteen. FreeCAD-mallissa
runko on yksi objekti (`Body (one piece with the neck)`). Samat
rajoitukset kuin läpikaulassa: ei kaulan kulmaa, ei kantapäähän jäävää
säätömutteria eikä päätöntä kaulaa.
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
potikalla rivissä, superstrat-takakolo (Ibanez RG / Jackson: 112 × 40 mm kolo,
jossa 5-asentoinen teräkytkin ja volume- ja tone-potikat; kytkin on 54 × 16 mm
syvemmässä taskussa, jonka päälle jää 4 mm kantta, sen vipu nousee kannesta
27 × 6,5 mm raon läpi, joka jyrsitään ylhäältä 1 mm taskuun asti, ja sen kaksi
#6-32-ruuvia menevät kannen läpi Ø 3,6 rei'istä 41,28 mm välein), yksi
volume-potikka (56 × 34 mm kolo; pyöreä kytkinkolo vain, jos mikkejä on
useampi), aktiivibasson takakolo neljällä potikalla 28 mm välein (130 × 44 mm,
tilaa esivahvistimelle; akku akkukoteloon), Telecaster-tyylinen kontrollilevy
rungon päälle upotettuna (2 potikkaa ja teräkytkimen aukko), Jazz Bass
-tyylinen levy (150 × 36 mm upotus, 112 × 26 mm kolo, 3 potikkaa 32 mm välein,
kaksi ruuvia 124,5 mm välein; `body_jack` "plate" tuo jakin levyyn potikoiden
taakse, eikä reunasta porata mitään) tai ei kontrolleja. Gibson-, manteli-,
rivi- ja yhden potikan koloissa on myös pyöreä kytkinkolo. Ohjainkolon voi kääntää (`control_angle_degrees`) kolon keskipisteen ympäri kansineen ja potikoineen (Tele-levy ruuveineen ja teräkytkimen aukkoineen); akun kotelolla ja jakilla on omat kulmansa, pyöreitä koloja ei käännetä. Runkoeditorissa kääntö tehdään Shift-raahauksella, ja uusi piirtopiste lisätään klikkaamalla ääriviivaa. Ohjainkoloa ja sen kantta voi venyttää tai lyhentää pituusakselinsa suunnassa (`control_stretch`, mm keskeltä molempiin päihin puoliksi); päät säilyttävät pyöristyksensä, leveys ei muutu, ja Gibson- ja rivikolon reunimmaiset potikat sekä Tele-levyn ruuvit, kytkinaukko ja takimmainen potikka siirtyvät päiden mukana. Liian lyhyeksi kutistettu kolo hylätään. Samoin kolon ja kannen voi leventää tai kaventaa poikittain (`control_stretch_across`); Gibson-kolon potikkarivit siirtyvät kauemmas toisistaan, ja rivikolon sekä Tele-levyn päät pysyvät puoliympyröinä. Kolon on oltava vähintään 16 mm leveä (minipotikan runko). Editorissa kannen päissä ja sivuilla on neliökahvat: kahvaa raahatessa vastakkainen pää tai sivu pysyy paikallaan. Mikkivalitsimeksi valitaan (`body_switch`)
3-asentoinen vipukytkin (oletus, 1/2" eli 12,7 mm reikä) tai mikro- eli
minivipukytkin (1/4" eli 6,35 mm reikä); `body_switch_shaft_hole_diameter`
antaa reiän käsin. Kolot ajetaan omissa ohjelmissaan
(`Body_back_controls.nc`, Telellä `Body_top_controls.nc`). Jos Gibson- tai
rivikolo osuisi syvään yläpuolen koloon (esim. Floydin hienosäätimien
kolo) niin, ettei välissä jää puuta, kolo potikoineen ja kansineen siirtyy
lähimpään vapaaseen paikkaan, enintään 20 mm ulospäin ja kaulan suunnassa. Kansien ruuvit
(4 kontrollikanteen, 3 kytkinkanteen) merkitään kansiupotuksen reunalle Ø 3 mm,
1 mm syvä. Jokainen kansi ja kontrollilevy saa oman `Cover_<nimi>.nc`
-ohjelmansa pleksistä tai muovista leikattavaksi: 3 mm terä, reiät ja aukot
ensin, sitten ulkoreuna 0,2 mm upotusta pienempänä neljällä pidikkeellä;
nollapiste kannen keskellä levyn pinnalla.

Yksittäisen elementin (esim. ensimmäisestä jyrsinnästä unohtunut
paristokotelo) voi jyrsiä erikseen: runkoeditorissa elementti raahataan
*Create NC file* -painikkeeseen, ja siitä tehdään omat ohjelmat
(`Feature_<nimi>_top` / `_back`, pienet reiät omanaan, kansi `Cover_…`),
joiden nollapiste on elementin keskellä eikä ohjaustapeissa. Takapuolen
elementti jyrsitään runko käännettynä keskilinjan ympäri kuten `Body_back`.
Myös pleksin voi raahata reunastaan *Create NC file* -painikkeeseen:
siitä tulevat ruuvien merkit runkoon pleksin keskeltä nollattuina ja
`Cover_pickguard`-ohjelma. Muualle raahattuna koko pleksi siirtyy.

Pleksi (`body_pickguard`, oletuksena pois) leikataan levystä
(`body_pickguard_thickness` 2,5 mm) omana `Cover_pickguard.nc`-ohjelmanaan.
Automaattisena se on 6 mm rungon ääriviivan sisäpuolella, jättää
kaulalle loven ja ulottuu tallaan asti (vähintään 3 mm viimeisen mikin
yli). Pidemmän sakaran
puolella pleksi ei seuraa sakaraa: reuna kulkee 8 mm mikkien ohi tallalta
kaulalle ja levenee tallaa kohti. Tyyli (`body_pickguard_style`)
määrää loput: `stratocaster` (oletus, mitattu Straton HH-pleksistä) –
kieleke kaulan vieressä 34 mm eteenpäin, reuna levenee 25 mm
ensimmäisen mikin päästä viimeisen mikin keskelle ja lyhyemmän sakaran
puolella pyöristetty häntä 55 mm tallan etureunan ohi; `superstrat` –
10 mm kaulan vieressä, reuna kaartuu mikkien välissä 5 mm sisään ja
levenee viimeisestä mikistä tallaa kohti 9 mm. Lyhyemmän
sakaran puolella pleksi seuraa rungon reunaa sakaran kärkeen ja
cutawayta pitkin takaisin kaulan loveen (ilman cutawayta se jatkuu
kaulan viereen niin pitkälle kuin puuta on); jos bassopuoli on tämä
puoli, reuna kaartuu 40 mm matkalla 8 mm mikkien ohi. V-mallissa
(Jackson RR) sakarat ovat tallan taakse ulottuvia siipiä: pidemmän siiven
puoli lasketaan pidemmäksi sakaraksi, ja lyhyemmän siiven puolella
pleksi jatkuu siipeä pitkin 100 mm tallan etureunan ohi, sisäreuna
V-loven mukaisesti ja pää pyöristettynä. Tallan kohdalla pleksi jatkuu
vähintään 12 mm tallan etureunan ohi tallan molemmin puolin.
Strato-pohjassa on valmiina piirretty pleksi, joka on jäljitetty Straton
HH-pleksin kuvasta ja sovitettu runkoon. Jazz Bass -pohjassa on sama
pleksi sovitettuna bassoon: venytetty kaulataskun päästä tallan
etureunaan, levennetty bassomikeille (kattaa kaikki bassojen
mikkiasetukset, myös 5-kielisellä), tallan ruuvien ohi ja yläreunasta
tuotu 6 mm rungon reunan sisäpuolelle; pieni sakara on muotoiltu
käsin editorissa. Design by Jone -pohjassa on sama pleksi Straton
mittakaavassa, ja se seuraa sakaran ja syvän cutawayn kohdalla rungon
reunaa 6 mm sisäpuolella; sitä on muotoiltu käsin niin, että sakaran
kärki kulkee rungon suuntaisesti ja potikat jäävät pleksin ulkopuolelle.
Jackson RR -pohjassa on editorissa piirretty pleksi: pidemmän siiven
puolella kapea kaista mikkien ohi, lyhyemmän siiven puolella pleksi
jatkuu siipeä pitkin kohti sen kärkeä (potikat menevät pleksin läpi).
Les Paul -pohjassa on samoin piirretty pleksi: diskanttipuolella
cutawayn sakaran ympäri, bassopuolella leveten tallaa kohti (ensimmäinen
potikka menee pleksin läpi). Piirretty pleksi on piirretty yhdelle
tallalle; muu talla kierretään: missä pleksi menisi tallan jyrsintöjen
ja reikien päälle (3 mm välys, mutta lovi alkaa aikaisintaan 3 mm
viimeisen mikin takaa), se leikataan suorakaiteen muotoisella lovella
tallan ympäri. Kahler 7300:n levy on joka suuntaan 5 mm jyrsintää
isompi (`plate_overhang`, editorissa katkoviivalla); pleksi jättää
tilaa koko levylle. Kaikki pleksit kiertävät kannasta säädettävän
kaularaudan säätökolon kaulataskun päässä (vähintään 2 mm välys), jotta
säätöpyörää voi kääntää pleksi paikallaan. *Auto pickguard* vaihtaa
kummankin automaattiseen. Piirretyn pleksin on peitettävä pleksiin asennettujen
kontrollien kolo, muuten rakentaminen pysähtyy virheeseen. Runkoeditorissa sen kahvoja voi raahata, reunaa
klikkaamalla lisätä pisteen ja Alt- tai oikealla klikkauksella poistaa
(`pickguard_points`, *Auto pickguard* palauttaa automaattisen); aukot ja
reiät näkyvät pleksissä. Pleksiin tulee suorakaiteen muotoinen, mikin kokoinen aukko
jokaiselle valitun mikkiasetuksen mikille (P-mikille yksi kummallekin
kelalle), reiät sen alle jääville potikoille ja kytkimelle sekä ruuvit
reunaa kiertäen (runkoon 1 mm merkit). Kontrolliasettelu `pickguard`
kiinnittää kolme potikkaa ja 5-asentoisen teräkytkimen pleksiin
Strat-tyyliin; niiden alle jyrsitään kolo rungon päältä, eikä takakoloa
tule, ja pleksi jatkuu tallan ohi kontrollien puolella ja ulottuu
kontrollien kohdalla 12 mm niiden ohi. Asettelu tuo pleksin mukanaan
(`body_pickguard` päällä tai ei; web-lomake laittaa sen päälle). Jos
piirretty pleksi ei peitä koloa (pohjien pleksit on piirretty niiden omille
takakoloille), tilalle tulee automaattinen pleksi, ja runkoeditori kertoo
siitä. Jos muodon potikoiden paikka vie kolon liian lähelle reunaa (pleksin
on ulotuttava 6 mm kolon yli 6 mm:n reunavaran sisällä) tai alle 3 mm:n
päähän kaulataskusta, mikeistä tai tallasta, kontrollit siirtyvät
lähimpään sopivaan paikkaan (enintään 40 mm) ja tarvittaessa kääntyvät
(enintään 30°, esim. Jackson RR:n siipeä pitkin). Ne mahtuvat pleksin alle
kaikilla pohjilla.

Humbuckerin kehys (`body_pickup_frame`, oletuksena pois) on levy
jokaisen humbuckerin ympärillä, leikattuna levystä
(`body_pickup_frame_thickness` 2,5 mm) omana `Cover_<asema>_pickup_frame.nc`-
ohjelmanaan: `ring` (tavallinen pyöristetty suorakaide 49 × 106 mm,
kulmat 6 mm, kuten mikkirengas), `horns` (päissä sarvet kaulaa kohti,
tallan puoli pyöreä) tai `hook` (bassopää koukulla, diskanttipäässä pitkä
sarvi). Kaksi jälkimmäistä on jäljitetty rakentajan piirroksesta (`humbframes.dxf`): viivat olivat
kynänvetoja, joten niiden ulkoreuna on otettu, ja piirros on skaalattu
niin, että sen kolo on humbuckerin, 70,5 mm kielten poikki (sarvikehys
57 × 163 mm, koukkukehys 57 × 146 mm). Kolo ei ole piirroksen vaan mikin
oma, sama kuin pleksin aukko (`pickup_openings`, 70,5 × 39 mm, 7- ja
8-kielisellä pidempi). Kehyksen ääriviiva on suljettu Catmull-Rom-käyrä
pisteidensä kautta (kuten runko), ja jokaisella mikillä on oma
(`body_neck_frame_points`, `body_middle_frame_points`,
`body_bridge_frame_points`; tyhjä = tyylin oma). Kehys kääntyy mikin
mukana, levenee 7- ja 8-kielisen mikin mukana ja peilautuu
vasenkätisessä. `body_pickup_frame_direction`: `auto` (oletus) sarvet
kaulaa kohti, käännettynä ympäri jos vain niin mahtuu; `neck` tai
`bridge`. Kiinnitys neljällä ruuvilla, kaksi kummankin mikin korvakkeen
ulkopuolella, kaulan suunnassa niin kaukana toisistaan kuin kehys antaa
(vähintään 8 mm) ja kehystä 4 mm joka puolella (renkaassa kulmissa,
±20 mm kaulan suunnassa ja 48 mm poikki):
3,2 mm reiät kehyksessä ja esiporaukset runkoon (`Body_top_small_holes`),
ja kaksi 6,5 mm reikää mikin korkeusruuvien kohdalla säätöä varten.
Kehyksen on oltava rungon tasaisella pinnalla (2 mm reunasta, tai 1 mm
pyöristyksen ohi), ulotuttava 1 mm aukon ohi joka puolella ja oltava irti
kaulasta (kaulataskusta; läpikaulassa otelaudan päähän asti), tallasta,
muista mikeistä ja kehyksistä, päällä olevista kontrolleista ja
kaularaudan säätölovesta. Tyylin kehys, joka ei mahdu kumminkaan päin,
sovitetaan automaattisesti: pisteet tihennetään 6 mm:n väleihin, este-
alueelle (1 mm marginaali) tai rungon reunan yli osuvat pisteet siirretään
lähintä tietä ulos (tai kohti aukkoa), väliin lisätään pisteitä missä
käyrä vielä osuu, ja muualla muoto säilyy; kaulamikin kehys lovetaan
näin kaularaudan säätöloven ja leikkauksen ympäri kaikilla pohjilla.
Piirrettyä kehystä ei sovita; runkoeditori piirtää sopimattoman kehyksen
punaisella syyn kera (esim. 7-kielisen hardtail-tallan edessä ei ole
tilaa), ja build hylkää sen. Kehyksen pisteet piirretään runkoeditorissa
muiden kahvojen päälle, joten niitä voi raahata kaulan ja reunan
vieressäkin. Runkoeditorissa kehyksen pisteitä
raahataan (reunaa klikkaamalla lisätään piste, Alt/oikea klikkaus
poistaa), ja tyylin vaihto palauttaa tyylin oman muodon.

Valinnainen 9 V:n paristokotelo (`body_battery_box`, oletuksena pois)
jyrsitään takaa samaan `Body_back_controls.nc`-ohjelmaan: 56 × 30 mm kolo
(r 5), 22 mm syvä takapinnasta, ja sen ympärillä 7 mm leveämpi
kansiupotus (70 × 44 mm). Kansi kiinnitetään kahdella ruuvilla kolon
päistä ja leikataan omana `Cover_battery_cavity.nc`-ohjelmanaan. Kotelon
paikka on rungon muodossa (`battery_offset`, `battery_y`,
`battery_angle_degrees`), ja jokaisella pohjalla se on oletuksena niin
lähellä kontrollikoloa (kolojen väli 18–32 mm), jotta
johdon reikä jää lyhyeksi; editorissa kotelon voi raahata. Pariston johdon kanava
ohjainkoloon porataan käsin. `body_battery_count` 2 tekee kotelon
kahdelle paristolle rinnakkain (18 V): kolo on 28 mm leveämpi, 56 × 58 mm
ja kansiupotus 70 × 72 mm. Kahden takakolon kansiupotukset eivät saa
mennä päällekkäin, eikä mikään reikä saa avautua paristokoteloon.
Paristokotelo ja ohjaimet sijoitetaan yhdessä, etteivät ne estä
toisiaan: jos piirretty kotelo estää ohjaimia pääsemästä paikkaan, jossa
ne eivät puhkea yläkoloihin, tai on itse niiden tiellä (kannet
päällekkäin tai pohja ylhäältä jyrsityn ohjainkolon päällä), ohjaimet
saavat paikan, jonka ne saisivat ilman koteloa, ja kotelo siirtyy
vähiten mahdollista niin, että se mahtuu kaiken muun väliin: ensin
lähistöltä 3 mm askelin 15° välein enintään 90 mm ja tarvittaessa
kääntyen enintään 30° (tai 90°), ja jos lähistöltä ei löydy, koko
rungosta 10 mm ruudukolla lähimmästä alkaen. Näin Jackson RR ottaa
Gibson-kolon, Floyd Rosen ja paristokotelon (kotelo siirtyy 3 mm),
superstrat-kolon (kotelo kääntyy 15°) tai aktiivibasson neljä pottia
(kotelo bassosiivelle). Paikallaan mahtuva kotelo pysyy paikallaan, eikä
rungon ulkopuolelle piirrettyä koteloa siirretä.

## Mikit

Mikkikokoonpano valitaan (`body_pickups`): kitaralle HH (oletus), HSH, HSS, H,
SSS tai SS, bassolle PJ (oletus), JJ, P, MM tai RR (kaksi Rickenbacker-tyylistä
bassohumbuckeria, 4003-koko: 90 × 36 mm palikka, kolo 92 × 38 mm, ruuvit
82 mm välein); "custom" ottaa jokaisen
paikan (kaula, keski, talla) tyypin omasta parametristaan. Single coil -kolo
on 20 × 88 mm pyöreäpäinen; keskimikki on oletuksena kaula- ja tallamikin
välisen raon keskellä (`body_middle_pickup_offset` siirtää sen), tallan
single coil on 10° kulmassa diskanttipää tallaa kohti
(`body_bridge_single_coil_angle`), ja piirtoeditorissa
sitä voi raahata kaulan suunnassa. Jokaista mikkiä voi lisäksi kääntää
oman keskipisteensä ympäri (`body_neck_pickup_angle`,
`body_middle_pickup_angle`, `body_bridge_pickup_angle`, enintään 45°
kumpaankin suuntaan, positiivinen kääntää diskanttipään tallaa kohti, single
coil -vinouden ja multiscalen viuhkan päälle): runkoeditorissa
Shift-raahaus kääntää mikkiä, ja kolo, korkeusruuvien upotukset ja
pickguardin aukko kääntyvät mukana. Keskipiste pysyy paikallaan, paitsi
että käännetty tallamikki pitää yhä välyksensä tallaan ja siirtyy tarvittaessa
kaulaa kohti.

Tallamikki on `body_bridge_pickup_offset`:n (21,73 mm) verran mensuurilinjan
edellä, mutta siirtyy itse eteenpäin niin, että sen kolon ja tallan lähimmän
kolon tai sen kohdalla olevan reiän reunan väliin jää
`body_bridge_pickup_clearance` (3 mm) puuta: Floyd Rosen upotus, hardtailin
Ø3 kiinnitysruuvien esiporaukset (10 mm mensuurin edellä; kolo päättyy 14,5
mm mensuurin edelle) ja Tune-o-maticin Ø11,2 tolppareiät (diskanttitolppa 1,6 mm mensuurin
takana; kolo päättyy 7,0 mm sen edelle). Kolo ei myöskään koskaan ulotu
satulalinjan yli (viuhkanauhoilla linja kallistuu nauhojen mukana); Kahlerin
kolo päättyy DXF:n mukaisesti 1,2 mm sen edelle. Käsin asetettu suurempi
etäisyys voittaa. Jos siirretty kolo osuisi seuraavaan mikkikoloon (keski-
tai kaulamikin), malli hylkää yhdistelmän `BodyGeometryError`-virheellä.

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
| Nimikaiverrus | Valinnainen (`headstock_engraving_text`): teksti kaiverretaan lavan pintaan 1 mm syvään (`headstock_engraving_depth`) V-terällä omassa ohjelmassaan `Headstock_engraving.nc` heti lavan pinnan jyrsinnän jälkeen, pintaa ja sen kulmaa seuraten. Fontti (`headstock_engraving_font`) on yksiviivainen (terä kulkee kirjaimen keskiviivaa): `sans` (oletus, oma yksinkertainen groteski: isot ja pienet kirjaimet, numerot ja vähän välimerkkejä), `script` (Hershey Script, kaunokirjoitus) tai `gothic` (Hershey Gothic English, fraktuura); kahdessa jälkimmäisessä myös ä, ö, å, ü ja é. Isojen kirjainten korkeus `headstock_engraving_height` (6 mm), keskikohta `headstock_engraving_x` / `_y` (oletus 20 mm satulan istukan takana keskilinjalla), suunta `headstock_engraving_angle` (90° = poikittain, luettavissa lapa ylöspäin). Lavan editorissa teksti näkyy sinisenä ja sitä voi raahata. Tekstin on oltava 2 mm irti lavan reunasta, satulan istukasta, viritinrei'istä ja kaularaudan säätökolosta, muuten rakentaminen pysähtyy virheeseen. FreeCAD-mallissa teksti on viivoina lavan pinnalla |

Lavan reunat piirretään (`headstock_outline = "drawn"`, oletus): web-sovelluksen
lavaeditori on auki, siinä raahataan kummankin reunan kahvoja ja kärkeä ja
uusi kahva lisätään klikkaamalla reunaa. Myös lavan päähän voi lisätä
pisteitä klikkaamalla (`headstock_tip_points`): kärki on pyöreä käyrä
kulmasta pisteiden kautta toiseen kulmaan, ja se lähtee kulmista reunan
suuntaan, joten pyöreä pää liittyy sivuihin ilman kulmaa. Ulospäin
raahattu piste tekee pyöreän nokan ja sisäänpäin raahattu loven. Terävä
kärki (Jackson-tyylinen) syntyy, kun reunat kohtaavat: jos kärkikulmat
ovat alle 1 mm (`TIP_POINT_WIDTH`) toisistaan, reunat yhtyvät niiden
puolivälissä yhteen pisteeseen (`pointed`), eikä kärkeen saa silloin
kärkipisteitä. Reunat saavat kapeta alle 1 mm:n vain viimeisellä,
kärkeen asti kapenevalla matkalla; muualla kurouma tai risteäminen on
edelleen virhe. Editorissa kärkikulma tarttuu toiseen 3 mm:n päästä,
terävä kärki liikkuu sen jälkeen yhtenä ja Shift-raahaus erottaa kulmat.
FreeCAD-malli lofataan kärjen lähellä vähintään 12 mm leveäksi ja
leikataan sitten reunojen ja kärjen mukaiseksi. Myös reunat ovat pyöreitä käyriä, jotka saavat kaartua kahvojen
ohi, joten esimerkiksi Stratocaster- tai Schecter-tyylisen lavan voi
piirtää. Kunnes kahvaa siirretään, reunat
seuraavat sovitettua ääriviivaa (myös lavatyylin vaihtuessa), kun virittimien
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
| Säätö | Valittava (`truss_rod_adjustment`): kannan puoli (oletus) tai lavan puoli |
| Spoke wheel | `truss_rod_spoke_wheel`: auto (oletus: kannassa on, lavassa ei), yes tai no. Kanta + wheel: hihnan porattava holkin reikä ja pyörä kannan päädyn takana rungon lovessa. Kanta ilman: kanava jyrsitään kannan päätyyn asti ja säätömutteri on valmiiksi kannan päädyssä, joten reikää eikä rungon lovea tarvita (säätö kaula irti). Lapa + wheel: pyörä avoimessa kolossa satulan takana (`truss_rod_nut_length` + 4 mm, 15,5 mm syvä, ilman kantta); lavan juuren on jätettävä 1 mm puuta alle, joten kulmalavassa (16 mm) pyörä ei käy, suorassa (20 mm) käy, muuten rakennus pysähtyy virheeseen. Lapa ilman: avaimen reikä, josta CNC jyrsii vain lavan päässä avoimen alun: 8 mm (`truss_rod_key_hole_diameter`) levyinen, `truss_rod_nut_length` + 2 mm pitkä lovi akselin syvyyteen (11,5 mm), hyllysatulan kanssa kannen alla, urassa olevan satulan kanssa avoin; jatko porataan tarvittaessa käsin |
| Säätöpää lavassa | Kaularauta on kokonaan kaulan puolella (kanava alkaa satulan istukan takaa). Tavallisen raudan 11 mm tasku ja 10,5 mm porras ovat silloin kaulan ohuessa osassa satulan lähellä (oletuskaulassa 11 mm puuta 1. nauhalla), joten kaula tehdään 1. nauhalta niin paksuksi, että taskun ja portaan alle jää 1 mm (`TRUSS_ROD_MIN_FLOOR`) myös niiden reunoilla, missä D-profiili on jo kaartunut ylös: 17 mm → 18,3 mm (`first_fret_thickness_needed`; paksumpi `first_fret_thickness` säilyy) |
| Matala kaularauta | `truss_rod_profile` low_profile: matala kaksitoiminen rauta (kuten StewMacin/Hoscon Hot Rod Low-profile: suora 1/4 × 3/8 in kanava liimapinnasta, 4 mm kuusiokoloavain; myös Next Genin Low Pro 6,25 × 9,25 mm sopii samaan). Yksi suora 6,35 × 9,5 mm kanava (`truss_rod_low_profile_width` / `_depth`) ilman porrasta ja taskua; alle jää oletuskaulassa 1,5 mm puuta, joten kaulaa ei tarvitse paksuntaa. Auto ei laita sille spoke wheeliä: kannassa mutteri on kannan päädyssä, lavassa avaimen lovi |
| Säätöholkki | Säädettävät mitat: pyöreä pää Ø 15 × 6 mm rungon puolella, kaulan puolella 12 mm pitkä Ø 9 mm reikä raudan akselilla; akseli 7,5 mm liimapinnasta (mitattu, `truss_rod_axis_depth`) |
| Kannan säätö | Holkin reikä jyrsitään `Neck_top`-ohjelmassa päältä urana (`truss_rod_sleeve_routed`, oletus): 9 mm leveä ura reiän pohjaan asti (akseli + säde = 12 mm) kannan päädyn läpi; reiän yläreuna on 3 mm liimapinnan alla, joten otelauta peittää uran kannan päähän asti (CNC ei poraa vaakasuoraan). Pois päältä reikä jää malliin pyöreänä ja porataan käsin G-coden ohjeen mukaan; rungon kaulataskun päähän lovi holkin päälle, 1 mm välys, 15,5 mm syvä |
| Lavan säätö | Kanava jatkuu satulan alta; mutteri 32 mm urassa lavan pinnassa, uralle kansi levystä omana NC-ohjelmanaan (`Cover_truss_rod`, lavan pinnalle ruuvattuna, ei upotusta) |
| Kaularaudan kansi | `truss_rod_cover_style`: `bell` (Gibsonin kello: leveä pää satulan puolella uran päällä, sivut kaartuvat koveralla kaarella kapeaan kaulaan ja pyöreään kupuun kohti kärkeä; ruuvi leveän pään kummassakin kulmassa uran vierellä ja yksi kuvussa, 41 × 28,5 mm, oletus), `ibanez` (pyöristetty kolmio, 2 ruuvia, 26 × 26), `prs` (pisara, 2 ruuvia, 30 × 22), `rectangle` (pyöristetty suorakaide uran ympärille, 3 ruuvia) tai `custom` (piirretty lapaeditorissa: `truss_rod_cover_points` ja `truss_rod_cover_screws`); `truss_rod_cover_length` / `_width` muuttavat kokoa. Kannen satulan puoleinen pää on 0,5 mm satulan hyllystä. Kannen on peitettävä ura 1 mm:n marginaalilla, ruuvien (3,2 mm) on jäätävä 1 mm puuhun uran ja kannen reunan ulkopuolelle, ja kannen 1 mm lavan reunoista ja viritinrei'istä; muuten virhe kertoo syyn. Kaiverrus pysyy 2 mm kannesta ja sijoittuu oletuksena kannen taakse ensimmäiseen kohtaan kohti kärkeä, jossa se mahtuu viritinreikien väliin (kuten Gibsonin logo kellon takana). Ruuvien esiporaukset (1,5 mm, 8 mm syvä) aloitetaan lavan pinnasta ohjelmassa `Neck_top_small_holes` (laminoidussa kaulassa käsin kannen läpi). Lapaeditorissa kansi piirretään uran päälle: kulmakahvoista sitä muotoillaan vapaasti (custom), reunaa klikkaamalla lisätään kulma, Alt/oikea klikkaus poistaa, pyöreistä kahvoista muutetaan pituutta ja leveyttä; tyylin valinta palauttaa tyylin oman muodon ja koon |
| Satulan istukka | Kannan säädössä satulahylly on tasainen koko satulan leveydeltä (myös monimensuurin vinolla satulalla). Lavan säädössä raudan tasku kulkee satulan alta, joten G-koodin ohje pyytää liimaamaan taskuun raudan päälle puisen täytepalan (esim. 9 × 5 mm) satulahyllyn tasoon ennen satulan liimausta |
| Valinnaiset aukot | Holkin reikä (`truss_rod_sleeve_bore`) ja lavan ura kansineen (`truss_rod_trough`) ovat oletuksena mukana, mutta ne voi jättää pois |
| Jyrsintä | Porras ja tasku ajetaan terän säteen (3 mm) verran naapurikolon päälle ja tasku säätöpään suuntaan, jotta pyöreä terä ei jätä kulmiin ulkonemia raudan kanttisille paloille; kanavan ankkuripää jyrsitään sellaisenaan |
| Kohdistus | 2 × 6 mm kohdistustappi kaksipuoliseen koneistukseen |


### Hiilikuituvahvistus

`neck_carbon_rods` upottaa kaulan yläpintaan kaksi hiilikuitutankoa,
yhden kaularaudan kummallekin puolelle, liimattuna otelaudan alle
pinnan tasoon: ne jäykistävät kaulaa taivutusta ja vääntöä vastaan.
Tangon poikkileikkaus valitaan (`neck_carbon_rod_size`): 3,2 × 6,35 mm
(1/8 × 1/4 in, oletus), 4 × 4 mm tai StewMacin 3,2 × 9,5 mm (1/8 × 3/8 in);
"custom" ottaa `neck_carbon_rod_width` × `neck_carbon_rod_depth`. Ura on
0,1 mm tankoa leveämpi epoksille. Tangot alkavat
`neck_carbon_rod_start` (20 mm) satulasta ja jatkuvat
`neck_carbon_rod_length` (tyhjä: kantapään tasaisen osan alkuun, pois
kaulan ruuvien tieltä; oletuskitarassa 387 mm, bassossa 537 mm)
`neck_carbon_rod_offset` keskilinjasta (tyhjä: kaularaudan leveimmän
kohdan vieressä 3 mm puuta välissä, 8,4 mm; lavasta säädettävällä
raudalla 9,15 mm). Uran alle on jäätävä vähintään 2 mm puuta koko
matkalta uran ulkoreunaan asti, ja kaularaudan reittiin ja kaulan
kylkeen 2 mm; StewMacin 1/8 × 3/8 in tangot hylätään oletuskaulassa (alle
jäisi 0,2 mm). `Neck_carbon_rods.nc` jyrsii urat `Neck_top`-ohjelman
jälkeen samalla kiinnityksellä 3 mm terällä (pääterä on uraa leveämpi),
ja sen muistiinpanot kertovat tankojen pituuden. FreeCAD-mallissa urat
leikataan kaulaan ja tangot ovat oma objektinsa (`CarbonRods`);
plan-kuva näyttää ne katkoviivalla otelaudan alla.
## Runko

Runko on aina piirretty (`body_shape`, "Your design"): sen ääriviiva
piirretään web-sovelluksessa raahaamalla spline-ohjauspisteitä, eikä
lomakkeessa ole enää rungon tyypin valintaa. Kitaran oletus on Design by
Jone -pohja (`GUITAR_BODY`, omasta `assets/reference/omarunko.dxf`-piirustuksesta
jäljitetty ja 64 pisteeseen uudelleennäytteistetty ääriviiva), basson
Jazz Bass -henkinen pohja. Pythonissa jäljitetty runko
(`DesignByJoneShape`) on yhä käytettävissä, ja sitä käyttävä tallennettu
design latautuu Design by Jone -pohjana; pohjaksi
voi ladata Design by Jone -rungon, Les Paul-, Stratocaster- tai Jackson
RR -henkisen muodon, ESP LTD Alexi Hexed -henkisen muodon (RR:n ääriviiva;
lataus asettaa myös Hexedin ilmeen: yksi tallahumbucker, yksi
volume-potikka ilman valitsinta, Floyd Rose ja grafiikka porrastettuna
kantena, jonka portaat on piirretty alkuperäisen raitojen kohdalle
kahtena sisäkkäisenä nuolena kaulataskun vierestä siipiin (kaulan
vieressä nuolet kohtaavat rungon reunalla, diskanttisakaran puoli
bassosakaran peilikuvana), kummankin perä terävänä V:nä loven kohdalla: sisempi nuoli mikin ja tallan ympärillä
täydessä korkeudessa, nuolten välinen kaista 1,5 mm alempana (loven
kohdalla vain 4 mm leveä) ja loput reunaan ja siipien kärkiin asti 3 mm
alempana; kaulataskun kohdalla pisteillä ei ole väliä; editori kertoo
vahvistuksessa, mitä se asettaa)
(Les Paul, Stratocaster, Jackson RR, Alexi Hexed ja Jazz Bass ovat
mockuppeja, eivät alkuperäisiä ääriviivoja), Mockingbird-, Telecaster-,
SG-, Explorer- tai Flying V -henkisen muodon (jäljitetty suoraan edestä
otetuista tuotekuvista, mittakaava nauhoista ja viimeinen nauha 4 mm
ennen kaulataskun päätä, mockuppeja; Mockingbirdin pitkä sarvi, nokka
ja bassopuolen lohko sekä Explorerin olka, alakulma ja siiven kärki muotoiltu sen jälkeen käsin; Flying V:n kytkin, siiven suuntaan
käännetty kontrollikolo, jakki ja paristokotelo diskanttisiivellä)
tai Jazz Bass -henkisen
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

Sääntö: satulasta 12. nauhaan on aina yhtä pitkä matka kuin 12. nauhasta
tallan satuloihin, millä tahansa tallalla, mensuurilla ja satulalla.
Satula (lukkosatulan etupinta) on satulalinjalla X = 0, 12. nauha
mensuurin puolivälissä ja tallan satulat (säätövaran keskellä)
mensuurilinjalla: Floyd Rosen tapit 11,9 mm ennen sitä, Tune-o-maticin
diskanttitolppa kompensaation verran (`compensation`, 1,6 mm = 1/16 in) ja
bassotolppa vielä `bass_setback` (3,2 mm = 1/8 in) sen takana, jolloin talla
kallistuu kielten kompensaation suuntaan ja jokainen satula aloittaa
lyhyen säätövaransa keskeltä. Bassotolppa on bassopuolella: jos
`headstock_bass_side` on +y, talla peilataan. `tests/presets/test_scale_symmetry.py`
varmistaa tämän.

| Kohta | Speksi |
| --- | --- |
| Paksuus | 44 mm laatta; reunat ja viisteet valinnaisia (alla) |
| Kaulatasku | Kaulan oma kapeneva ääriviiva + 0,15 mm välys/puoli, 79,5 mm pitkä, päättyy kannan päähän, 20 mm syvä; avautuu sarvien väliin |
| Kaulan kulma | `neck_angle` (astetta): kaula kallistuu taaksepäin, lapa soittajaa kohti. Taskun pohja on vino: kannan päässä 20 mm syvä, suussa `body_neck_pocket_length` × tan(kulma) syvempi (2°: 22,8 mm), ja se jyrsitään 0,1 mm portaina (`FLOOR_TERRACE_STEP`) taskun jälkeen; portaat jäävät enintään 0,1 mm vinon pohjan yläpuolelle, ja kaula lepää niiden reunoilla. Kaula kääntyy taskun pohjan kannanpuoleisen pään ympäri, ja talla siirtyy niin, että mensuuri (ja 12. nauha puolivälissä) pitää kielen kallistettua linjaa pitkin nauhojen yläpinnan tasolla (2°, 24": talla 1,04 mm satulaa kohti). Tyhjä: 2° Tune-o-maticin kanssa (`NECK_ANGLE_TUNE_O_MATIC`; tasakantisella rungolla 2–2,5° on tavallinen, Les Paulin kaareva kansi 3–5°), muuten 0°. Enintään 6° |
| Mikkikolot | DXF:n humbucker-kolo korvakkeineen, 41 × 85,9 mm, 22 mm syvä; keskipisteet x = 491,7 ja 587,9 |
| Säätöruuvien syvennykset | Ø 6 mm, 8 mm kolon pohjan alle, ±39,95 mm keskilinjasta |
| Talla | Vaihdettava (`body_bridge`): oletus Kahler 7300 (ruuvattava, levyn kolo 55 × 65 × 25 mm); vaihtoehdot Floyd Rose Original valmistajan jyrsintäpiirustuksen mukaan (tapit Ø10 k/k 73,91, 11,9 mm skaalaviivan edellä; 95,25 mm leveä upotus, joka kapenee 71,12 mm:iin 42,44 mm:n kohdalla (pituus 79,38), jyrsitään kokonaan 6,73 mm syväksi ja syvennetään 11,18 mm:iin etummaisen 15,88 mm tappihyllyn takaa porrastaskuna sen sisällä; pohjassa 20,96 × 82,85 × 29,59 block-kolo, joka avautuu jousikoloon; takana jousikolo 123,19 × 56,64 × 16,13 + 28,19 mm syvä block-tasku ja 2 mm kansiura 8 mm kolon ulkopuolelle, johon tulee kuuden ruuvin levystä leikattava kansi omana `Cover_floyd_rose_spring_cavity.nc`-ohjelmanaan (piirustus on 44,45 mm rungolle; paksummassa rungossa jousikolo ja block-tasku syvenevät erotuksen verran, jotta block-kolo avautuu aina läpi); upotus 3,56 mm leveämpi vipupuolella), Tune-o-matic + stop bar (4 × Ø11,2 reikää) ja hardtail (6 string-through + 5 esiporausta). Floyd Rose -mitat valmistajan piirustuksesta, muut lähtöarvoja — tarkista laitteesta |
| Potikkakolo | DXF:n manteli tallan takana, takaa 36 mm (8 mm puuta kanteen), kansiura 2 mm |
| Kytkinkolo | DXF:n ympyrä Ø 44 yläsakaran juuressa, takaa 36 mm, kansiura Ø 59,5 × 2 mm |
| Akselireiät | Kytkin Ø 12,7; potikat 2 × Ø 10 kohdissa (642, 86) ja (682, 87) |
| Johdinkanavat | `body_wire_channels` (oletus päällä): jokainen mikkiura ja takakolojen erillinen kytkinkolo johdotetaan ohjainkoloon lähimmän jo johdotetun kolon kautta (ohjainkolo, aiemmin johdotettu mikkiura tai kytkinkolo), joten rivissä olevat mikit ketjuuntuvat kuten Stratissa ja Les Paulissa ja Les Paulin vipukytkin liittyy kaulamikin kautta; paristokotelon johto suoraan ohjainkoloon (`Battery wire hole`, jolloin `Body_back_controls`-ohjelman vanha käsiporausmuistiinpano jää pois); tallan maadoitus ohjainkolosta tremolon jousikoloon (jousipidin), muuten lähimpään tallan uraan tai reikään. Ei ohjaimia (`none`), ei johdotusta. Pickguardin alla kanava jyrsitään päältä (10 mm leveä, enintään 16 mm syvä, ei uria syvempi) `Body_top`-ohjelmassa; kanavan uran ulkopuolinen osa on oltava pickguardin alla eikä sen aukoissa (aukko saa ylittää uran 1 mm), 2 mm muista koloista. Muualla suora käsin porattava reikä pitkällä terällä (Ø 6, maadoitus Ø 3): terä tulee kolon avoimesta pinnasta (uran päältä, takakolon takaa) sen kauemman reunan ohi, reikä alkaa kolon seinästä ja päättyy toisen kolon seinään. Korkeus ja kulma haetaan niin, että reikä aukeaa molempiin koloihin seinän kautta, jättää 3 mm puuta pinnan alle (veistetty tai porrastettu kansi ja käsinoja huomioiden) ja takapinnan yläpuolelle (vatsaleikkaus huomioiden), 2 mm muihin koloihin ja reikiin (myös jakkiporaus), pysyy rungossa 2 mm reunasta, on enintään 60° jyrkkä ja terän matka reunalta enintään 300 mm. Sopivista valitaan se, joka on lähimpänä mikkiuran pohjaa (johdot kulkevat siellä), sitten loivin. Reiät mallinnetaan FreeCADiin, piirretään plan-kuvaan punaisella katkoviivalla ja `Body_top`-muistiinpanoissa on porausohje (mistä kolosta mihin, kummalta pinnalta, kulma, alku korkeuksineen, suunta ja pituus). Jos suoraa reikää ei löydy, muistiinpano jättää sen rakentajalle. Runkoeditori ei laske johdotusta (vain build). Neck-through-rungon osissa ovat niihin ulottuvat kanavat; reiät porataan liimattuun runkoon |
| Jakki | Ø 12,5 poraus alkaa siitä, missä muodon jakkilinja (oletus 742, 107,5 suuntaan 202,5°) kohtaa rungon ääriviivan, millä tahansa rungolla, ja jatkuu 3 mm ohjainkolon seinän yli (muuten 55 mm; `body_jack_depth` kiinnittää pituuden). `body_jack`: side (kylkilevy tai putkijakki), cup (Tele-kuppi tai Electrosocket: 7/8" eli 22,2 mm upotus 25 mm syvä reunassa), strat (Strat-tyylinen kansilevy päällä: Ø 25,4 × 32 mm kolo ylhäältä 4 mm reunasta, poraus jatkuu siitä ohjainkoloon) tai plate (Jazz Bass -levyssä, vain `jazz_bass`-asettelun kanssa: ei porausta). Runkoeditori varoittaa, jos poraus ei osu ohjainkoloon |

## Reunat ja viisteet

Kaikki valinnaisia ja oletuksena pois: reunojen pyöristys päältä ja takaa
(`body_top_edge_radius`, `body_back_edge_radius`), pyöristyksen sijaan
reunanauhan ura (`body_*_binding_width` / `_depth`, syvyys oletuksena 6 mm),
soittokäden viiste päälle bassopuolen takakaaren kohdalle
(`body_arm_contour_*`, oletuksena 60 mm leveä ja 240 mm pitkä) ja mahaviiste
taakse bassopuolen yläkaaren kohdalle (`body_belly_cut_*`, 70 × 260 mm).
Viisteet kapenevat reunaa pitkin molempiin päihin. Soittokäden viisteen
alkuviivan voi piirtää runkoeditorissa (`arm_contour_points`): vihreä
viiva pyöreine kahvoineen, päät rungon reunalla; viiste ulottuu reunasta
viivaan asti ja on syvin siellä, missä viiva on kauimpana reunasta.
*Auto arm contour* palauttaa automaattisen. Mahaviisteen alkuviivan voi
piirtää samalla tavalla (`belly_cut_points`, sininen viiva, katsottuna
päältä kuten ääriviiva), kun `body_belly_cut_depth` on päällä; *Auto belly
cut* palauttaa automaattisen. Viisteet ja pyöristykset
ajetaan ball nose -terällä omissa ohjelmissaan (`Body_top_edges.nc`,
`Body_back_edges.nc`), reunanauhan ura pääterällä ääriviivan jälkeen.
FreeCAD-mallissa ne ovat 1 mm porrastuksina.

## Kaareva kansi

Valinnainen (`body_carved_top`, mikä tahansa runkomalli; valinta ja syvyys `body_carve_depth` myös runkoeditorin vieressä): kansi kaarretaan
Les Paul -tyylisesti. Kansi pysyy täydessä paksuudessa tasaisella
keskialueella, jonka raja (mistä lasku lähtee) piirretään suorilla ja
kaarilla: osien ympärysympyröiden kupera verho — kaulatasku ja
kaularaudan säätölovi 3 mm, jokainen mikki 12 mm (`PICKUP_RING_REACH`,
jotta mikin kehys, humbuckerin noin 92 × 45 mm, lepää kokonaan
tasaisella), talla (kolot, levy, tolppa- ja nastareiät) 15 mm
(`body_carve_margin`). Sivut ovat suoria ja kapenevat kaulaa kohti, kulmat
kaaria ja takapää puoliympyrä. Pinta laskee pehmeästi (smoothstep)
`body_carve_depth` (9,5 mm) alemmas ja tasaantuu reunalla
`body_carve_rim` (8 mm) levyiseksi suoraksi kaistaksi; missä tasainen on
lähempänä reunaa kuin reunakaista + 25 mm (`CARVE_MIN_FALL`), reunakaista
kapenee, jotta laskulle jää tilaa. Reunalle jää aina vähintään 1 mm
reunakaistaa (reunanauhan tai -pyöristyksen kanssa sen leveys + 1 mm),
myös kaulataskun suulla, joten reunanauhan ura on aina reunakaistan
tasolla. Tasainen alue pysyy vähintään 12 mm (`PLATEAU_EDGE_FALL`) irti
tuosta kaistasta, joten missä se kulkee reunaa pitkin (Les Paulin
leikkaus kaulataskun vieressä, jossa kannelle jäi muutama mm pudota koko
korkeutensa eli seinämä), laskulle jää tilaa; kaulataskun suulla kansi
laskee taskun seinien vierestä (pohja ei muutu, ja kaula jää reunalla
kaaren yläpuolelle kuten Les Paulissa). Vain mikkien kehykset
(`PICKUP_RING_KEEP`, 7 mm reiän ympäri: humbuckerin kehys ulottuu noin
5 mm reiän yli, tasaisen alueen 12 mm marginaali on väljä) ja tallan osat
(`keep`) pysyvät tasaisella lähempänäkin; 12 mm leveänä Les Paulin
leikkauksen kohdalla kaulamikin kehysalue jätti kannelle 5 mm pudota koko
korkeutensa, seinämän reunanauhan viereen. Lasku lasketaan tarkoilla etäisyysmuunnoksilla ja tasoitetaan
(harmoninen relaksointi): pinta vain laskee tasaiselta reunalle päin,
ilman taitteita tai kupruja. Oletukset Les Paulin mukaan: 5/8"
vaahterakansi ja 1/4" reunanauha jättävät 3/8" kuvun, runko 2 1/4"
keskeltä ja 2" reunalta (`body_thickness` 50,8 sellaiselle).

Takakolot pysyvät 8 mm (`body_rear_cavity_top_wall`) kaarevan pinnan
alla: ne madaltuvat sen verran kuin pinta laskee niiden kohdalla, ja alle
3 mm seinämä hylätään. Kyynärviiste ei käy kaarevan kannen kanssa.
Reunan pyöristys ja reunanauhan ura jyrsitään reunakaistan tasolta, ja
kaiverrus seuraa kaarta. `Body_top_carve.nc` ajetaan heti tappien jälkeen:
tasapäinen terä (`carve_tool_diameter`, 0 = pääterä) rouhii kaaren
kerroksittain, viimeinen kerros pintaa seuraten, ja rivien portaat
hiotaan käsin, kuten käsin portaittain jyrsitty kansi. Kunkin kerroksen
pätkät ajetaan lähin ensin, ja lyhyt siirtymä (enintään neljä riviä)
syötetään leikkauksessa eikä turvakorkeudella, joten terä ei enää hyppää
tasaisen alueen yli joka rivillä. Reunakaistan taso jatkuu rungon reunan
yli vain terän säteen + 3 mm (`CARVE_EDGE_REACH`) 12 mm kaistan sisällä
(tapit pysyvät kaistan ulkopuolella). Les Paul 6 mm pääterällä noin
92 min (aiemmin kuulapääviimeistelyineen 315 min), 10 mm rouhintaterällä
noin 55 min ja 12 mm noin 47 min. `carve_finish` viimeistelee lisäksi
rouhintaterän levyisellä pallojyrsimellä 1 mm välein (sileä mutta hidas). FreeCAD-mallissa kansi
leikataan kuutiollisen B-spline-pinnan alle, jonka ohjauspisteinä ovat
korkeudet 4 mm välein (jyrkässä laskussa Les Paulin leikkauksen kohdalla
nostettu pinta jäi 6 mm välillä jopa 2 mm liian korkealle, 4 mm välillä
0,7 mm ja 3 mm välillä 0,34 mm; kannen leikkaus kestää 6, 9 ja 14 s;
terävöitynä ja naapuripisteiden rajoissa; makroon
kirjoitetaan vain korkeudet ruudukkona): sileä ja
kevyt, eikä se aaltoile jyrkissä kohdissa tasaisen alle. Missä tasainen
on lähellä reunaa (Les Paulin kaulamikki leikkauksen kohdalla), kansi
putoaa koko syvyytensä muutamassa millissä, jyrkemmin kuin kuutiollinen
pinta taipuu, ja malli notkahti mikin kehyksen kulman alle; siksi
ohjauspisteitä nostetaan (`_carve_held_up`), kunnes pinta on jokaisessa
ohjauspisteessä ja niiden neljännesväleissä kaarteen tasolla tai sen
yläpuolella: malli ei koskaan leikkaa kantta syvemmältä, vain jyrkässä
laskussa hieman matalammalta (muutama mm alle 1 %:lla laskusta).
Reunakaista, joka pidetään reunan tasolla koko rungon ympäri
(`edge_rim`, reunanauhan tai -pyöristyksen leveys + 1 mm), leikataan
ensin omalla nopealla tasoleikkauksellaan reunan tasoon, joten nostettu
pinta ei jätä puuta reunanauhan päälle kaulataskun vieressä. Tasaisen alueen
kohdalla pinta on 0,3 mm (`CARVE_PLATEAU_LIFT`) kannen yläpuolella:
smoothstep-lasku alkaa vaakasuorana, joten aivan kannen yläpuolella oleva
pinta kohtasi kannen lähes tangentiaalisesti, ja silloin leikkaus
epäonnistui äänettömästi (runko jäi leikkaamatta tai jopa kasvoi).
Nosto jättää mallissa laskun ensimmäiset 0,3 mm (G-code jyrsii ne). Kansi
leikataan viimeisenä, kolojen ja reunojen jälkeen (ne leikkautuvat
tasaiseen aihioon paljon nopeammin), ja tulos tarkistetaan: jos leikkaus
silti epäonnistuu, makro kokeilee 0,001 ja 0,01 mm toleranssia ja
hyväksyy ensimmäisen kelvollisen tuloksen, joka poisti noin kaarteen
verran puuta (`CARVE_REMOVED`, ±30 %); muuten se pysähtyy virheeseen.
Kannen mallintamista portaina (kuin käsin eri kokoisilla sabluunoilla)
kokeiltiin: se on FreeCADissa moninkertaisesti hitaampi, koska jokaisen
portaan seinä on satoja tahkoja. Plan-kuva ja runkoeditori näyttävät tasaisen alueen rajan
katkoviivana.

## Koristekaiverrus

Valinnainen (`body_engraving`, oletuksena pois): kanteen kaiverretaan
Design by Jonen pintakuvion (`pintakuviodesignbyjone.dxf`) tyylinen
kiehkurakuvio. Kuvion aihio on viisi kaarta (laaja kiehkura, siitä
kiertyvä kierre ja pieni kärki, koukku ja pitkä kaari); aihion kopiot
arvotaan kannelle siemenluvusta (`body_engraving_seed`, sama siemen
antaa aina saman kuvion; runkoeditorin *New pattern* arpoo uuden)
noin `body_engraving_spacing` (50 mm) välein, kukin käännettynä
piirustuksen jompaankumpaan suuntaan. Kaaret rajataan 10 mm rungon
reunan sisäpuolelle ja 4 mm irti koloista, mikeistä, tallasta ja sen
levystä, pleksistä, viisteistä ja rei'istä. Takapuolen koloja ei
väistetä (niiden päälle jää 8 mm puuta), ellei kaiverruksen alle jäisi
alle 3 mm. Arvonnassa ei
tule liian tiheitä rykelmiä (enintään 10 viivaa 30 × 30 mm:n alueella)
eikä yksittäisiä viivoja: yksinäinen viiva tai alle 40 mm:n irrallinen
viivaryhmä jätetään pois. Kaiverrus on
2 mm syvä (`body_engraving_depth`) ja ajetaan omana ohjelmanaan
`Body_top_engraving.nc` V-terällä (`engraving_tool_angle` 60°, ura
2,31 mm leveä, 1 mm kerroksin). FreeCAD-mallissa se näkyy viivoina
kannen pinnalla (ei uria).

Kuvion voi vaihtaa (`body_engraving_pattern`, myös runkoeditorin vieressä);
kaikki arvotaan samasta siemenestä, `body_engraving_spacing` asettaa
mittakaavan, ja kaikki rajataan samalle alueelle (alle 8 mm:n pätkät
jätetään pois):

| Kuvio | Kuvaus |
| --- | --- |
| `scroll` (oletus) | Design by Jonen kiehkurat, yllä |
| `evh_stripes` | Eddie Van Halenin Frankenstrat-tyyliset teippiraidat: suoria 6–16 mm leveitä nauhoja ristiin (kuuteen suuntaan ±12°), yksi kaksinkertaista spacingin neliötä kohden; kummankin reunan viiva kaiverretaan, ja myöhempi raita peittää aiemmat kuin teippi |
| `flame` | Liekkivaahteran tapaiset aaltoviivat rungon poikki, noin spacing/5 (vähintään 6 mm) välein, vierekkäiset lähes samassa vaiheessa, joten ne eivät leikkaa |
| `ripples` | Ryhmiä sisäkkäisiä renkaita (2–6 kpl, 8 mm välein), myöhempi ryhmä peittää aiemmat |
| `crackle` | Satunnainen solukuvio (Voronoi) kuin säröillyt lakka, solu noin spacingin kokoinen |
| `camo` | Woodland-maastokuvio reliefinä, ei viivoina: suljettuja lohkoisia muotoja (viisi harmonista lohkoa) 1–3 ulos työntyvällä sakaralla (0,35–0,8 × koko, kapenevat), leveys 0,3–0,55 × spacing (vähintään 12 mm), venytetty enintään 2,3-kertaiseksi kuvion suuntaan (yksi suunta siementä kohden, muoto ±25°). Jokainen saa yhden neljästä tasosta, `body_engraving_depth` / 4 välein (oletuksena 0,5, 1, 1,5 ja 2 mm), satunnaisesti, tai syvemmän kuin muoto, jonka päälle sen keskipiste osuu. Muotoja tavoitellaan 2,5 spacingin neliötä kohden, kunnes 600 peräkkäistä yritystä ei tuota yhtään. Saman tason muodot pysyvät 3 mm erillään (eivät sulaudu); eri tasojen muodot saavat mennä päällekkäin, jolloin syvempi näkyy (kuten jyrsinnässä, kun kukin tasku jyrsitään omaan syvyyteensä), kunhan jokaisesta jää näkyviin vähintään puolet ääriviivasta; toisistaan erillään olevat pysyvät 3 mm erillään, ettei väliin jää ohutta seinämää. Jos muoto ei mahdu, sitä kokeillaan ensin vähemmillä sakaroilla, sitten 0,75-kertaisena pienempänä ja pyöreämpänä; pienimmätkin ovat vähintään 12 mm leveitä ja lohkoisia. Toisen sisältä aloitettu muoto muotoillaan sen mukaan (0,4–0,6 × koko, enintään yksi sakara; neljännes yrityksistä aloitetaan tarkoituksella ison muodon sisältä), ja kokonaan matalamman sisällä oleva jyrsitään sen pohjasta. Muoto vain tasaisen pinnan päälle: veistetyllä kannella sen tasanteelle, porrastetulla yhden portaan sisälle, taso mitattuna portaan pinnasta. `Body_top_relief.nc` jyrsii muodot tasapäisellä jyrsimellä (`relief_tool_diameter`, 3 mm) `engraving_step_down`-askelin; FreeCAD leikkaa ne taso kerrallaan, runkoeditori varjostaa ne sitä tummemmiksi mitä syvempiä, syvemmät päällimmäisinä |
| `pinstripe` | Yksi raita rungon ympäri 0,5 mm marginaalin sisäpuolella, reunaa myötäillen kuin maalattu pinstripe (Jackson RR, ESP LTD Alexi Hexed); katkeaa kolojen, tallan, pleksin ja muotoilujen kohdalla sekä siellä, missä sakara kapenee alle kaksinkertaisen marginaalin. Siemen ja spacing eivät vaikuta; etäisyys reunasta on `body_engraving_margin` ja leveys syntyy syvyydestä (`body_engraving_depth`, V-terän ura noin 1,15 × syvyys) |
| `drawn` | Toisessa ohjelmassa piirretyt viivat: runkoeditorin *Export SVG* -pohjan *Pattern*-tasolla on nykyinen kuvio, ja *Import SVG* lukee tason viivat `body_engraving_lines`-kenttään (X kantapään päästä, kuten piirretty, ohennettuna 0,05 mm:n tarkkuuteen), jos niitä muutettiin; kaikki viivat poistettuina kaiverrus kytkeytyy pois. Viivat otetaan millin välein ja rajataan kuten muutkin kuviot; suljettu viiva pysyy suljettuna, alle 3 mm:n palat jätetään pois. Vasenkätisessä peilattuna; ilman viivoja build kertoo syyn |

Porrastettu kansi (`body_stepped_top`, myös runkoeditorin vieressä)
laskee kantta kaistoittain reunan suuntaisesti, kuten ESP LTD Alexi
Hexedin grafiikassa. Jokaisella portaalla on raja; sisimmän rajan sisällä
kansi on täydessä korkeudessa ja jokainen reunempana oleva kaista
`body_top_step_height` (1,5 mm) alempana kuin sen sisäpuolinen. Rajat
piirretään (muodon `step_points`: kullekin portaalle suljettu pisteviiva,
suorat viivat pisteiden välillä, uloin ensin, kukin edellisen sisällä
leikkaamatta sitä, paitsi rungon ulkopuolella, kaulataskussa tai alle
3 mm:n päässä reunasta, jossa viivat saavat kohdata) tai ne ovat
ääriviiva sisennettynä kunkin
`body_top_step_insets`-arvon verran (oletus 12 ja 40 mm). Runkoeditori
piirtää rajat violetteina vinoneliökahvoin: kahvaa raahaamalla, viivaa
klikkaamalla (uusi piste) tai Alt-klikkaamalla (pisteen poisto) rajat
tallentuvat piirretyiksi, ja *Auto steps* palauttaa sisennykset.
Rajat kulkevat siipiä ja sakaroita pitkin niin pitkälle kuin ne ovat
leveitä; kapeammat sakarat jäävät kokonaan alempaan kaistaan. Mikkien ja
tallan on oltava sisimmän rajan sisällä (muuten build hylätään; editori
piirtää portaat silti), takakolojen kansiseinämä säilyy laskettujen
kaistojen alla, eikä porrastettu kansi käy yhteen kaarevan kannen,
käsinojan viisteen tai pleksin kanssa. Reunapyöristys ja reunalista
jyrsitään uloimmalle kaistalle ja kaiverrus seuraa tasoja.
`Body_top_steps.nc` ajetaan heti ohjaustappien jälkeen: ensin sisimmän
portaan kaista yhden portaan syvyyteen, sitten seuraava syvemmälle,
kierroksina reunan suuntaisesti; kunkin kaistan viimeinen kierros jyrsii
portaan seinämän tarkasti. FreeCAD-malli leikkaa portaat renkaina.

## Omat suunnitelmat

Lomakkeen jokainen kenttä kertoo merkityksensä, kun hiiren vie sen nimen
päälle (nimi on alleviivattu katkoviivalla): selitys otetaan koodin omasta
dokumentaatiosta (luokkien `Args:`-kuvaukset ja parametrien yläpuolen
kommentit), ja heti näkyville perusasetuksille on kirjoitettu selkokieliset
selitykset (`field_help.FIELD_HELP`).

Web-sovelluksen **Save design** tallentaa kaikki asetukset, myös soittimen,
kitaran nimen, piirretyn rungon ja lavan reunat, JSON-tiedostoksi omalle
koneelle; kun kitaralla on nimi (*Guitar name*, soittimen valinnan alla),
tiedosto nimetään sen mukaan. Rakennuksen jälkeen **Download all NC files
(.zip)** lataa kaikki NC-ohjelmat yhtenä ZIP-tiedostona kitaran nimellä
(`<Guitar name>.zip`): sen sisällä kitaran niminen kansio, siinä kansio
osaa kohden ja ohjelmat numeroituina ajojärjestykseen
(`Neck/02_Neck_top.nc`) sekä `README.txt`, jossa ohjelmat työkaluineen ja
aika-arvioineen.

Rakennuksen tulos näkyy heti valmistuttuaan ensimmäisenä: leveällä
näytöllä oikean sarakkeen ylälaidassa, kapealla (≤ 900 px) suoraan
build-painikkeiden ja soittimen valinnan alla, editorien yläpuolella.
Ensin yhteenveto (aihiot, ohjelmat aika-arvioineen), sitten lataukset,
tasokuva ja työradat; virhe näkyy samassa kohdassa. Jos kohta ei ole
näkyvissä, kun tulos tai virhe tulee, sivu vierittää sen esiin.

Editorien pitkät ohjetekstit on supistettu otsikoiden *How to edit the
design*, *How to edit the headstock* ja *How to edit the inlays* alle, ja
ne aukeavat vasta otsikkoa klikkaamalla.

Jokainen asetus, joka muuttaa editorin kuvaa, on kuvan yläpuolella
editorin omassa ruudussa otsikon *Settings (N)* alla, oletuksena
supistettuna (otsikossa lukee *· changed*, kun jokin niistä on muutettu;
lomakkeen rivi piilossa sillä aikaa):
runkoeditorissa kaulan liitos, mikkien asettelu, kunkin aseman mikki ja
paikka sekä viuhkan seuraaminen, talla ja sen viuhkan seuraaminen,
kontrollit, valitsin, jakki, pleksi, humbuckerin kehykset, kyynärvarren
ja vatsan muotoilut, kaareva ja porrastettu kansi, kaiverrus, akkukotelo
ja kaulapulttien suunta (leveällä, vähintään 1200 px näytöllä kahdessa
sarakkeessa); lapaeditorissa virittimien asettelu ja bassopuoli, lavan
pituus, viritinreiät, satulan tyyli ja lukkosatula, kaiverrusteksti sekä
kaularaudan säätö, kehrä ja kansi; inlay-editorissa merkkien tyyli,
nauhat, koot, syvyys ja reunamarginaali sekä otelaudan reunanauha. Koko
soittimen asetukset, jotka muuttavat kaikkia kuvia (mensuuri,
kielimäärä, kätisyys, satulan leveys), jäävät lomakkeen alkuun, ja
hienosäätömitat *Advanced*-taittoon.
**Load design** lataa tiedoston takaisin lomakkeeseen ja editoreihin. Tiedostovalitsin
aukeaa heti napista (Safari ei avaa sitä vahvistusdialogin jälkeen), ja
kysymys muutettujen arvojen korvaamisesta tulee vasta, kun tiedosto on
valittu. Asetukset,
joita käytössä oleva versio ei tunne, ohitetaan ja luetellaan. Vanhemman
version arvot päivitetään ensin (`webapp.upgrade_design`): ennen
lapaeditoria tallennettu `headstock_outline` "fitted" ilman piirrettyjä
reunoja latautuu "drawn"-muodossa, joka on sama sovitettu ääriviiva, joten
lapaeditori asetuksineen on auki kuten uudessa suunnitelmassa. Kun editorin
ruutu on piilossa (headless-kaula tai sovitettu lapa piirretyin reunoin),
sen ruudun asetukset (`headstock_style`, `nut_style`, kaiverrus) näkyvät
lomakkeessa. Mitään ei tallenneta palvelimelle.
**Undo** ja **Redo** (Resetin vieressä ja jokaisen editorin ruudussa, tai
Ctrl/Cmd+Z ja Ctrl/Cmd+Shift+Z / Ctrl+Y) kumoavat ja palauttavat
suunnitelman muutoksia: editorin raahaus (kun se päättyy), pohja tai
poisto, lomakkeen kentän muutos, Reset, soittimen vaihto ja ladattu
suunnitelma ovat kukin yksi askel, enintään 100 askelta. Historia on koko
sivulle yhteinen; napin vihje kertoo, mitä kenttiä askel muuttaa, ja uusi
muutos tyhjentää palautettavat askeleet. Tekstikentässä näppäimet kumoavat
selaimen tapaan kirjoitusta.
Tallennettu suunnitelma rakennetaan paikallisesti komennolla
`python -m cncguitarwizard build-prototype001 --design oma.json --output
build/oma`: G-koodit, DXF:t sekä FCStd- ja STEP-mallit, joita selain ei
pysty tekemään. Tiedosto luetaan kuten web-sovellus sen lataa
(`webapp.load_design`): vanhan version arvot päivitetään, puuttuva arvo on
soittimen oletus ja tuntematon asetus ohitetaan ja luetellaan.

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
| Kohdistustapit | 2 × Ø6 (`index_pin_diameter` tyhjä: 6 mm, tai pääterän levyiset, kun terä on leveämpi — reiät porataan pääterällä, joten 8 mm terä vaatii 8 mm tapit; terää kapeammiksi annetut tapit hylätään ohjeen kera, ja vanhan tallennuksen 6 mm latautuu tyhjänä) keskilinjalla aihion hukkapuussa: tappi 1 sarvien välissä kaulataskun edessä, tappi 2 perän lovessa — eivät koskaan valmiissa kappaleessa; ≥ terä + 3 mm puuta joka leikkaukseen, ≥ 8 mm aihion reunasta; paikat `build.json`:ssa |
| Tarkistus | jokainen ohjelma ajaa ennen karan käynnistystä tappi 1 → tappi 2 → tappi 1 turvakorkeudella |
| Aihio | vähintään 496 × 324 × 44 mm (ääriviiva + 15 mm joka puolelle) |
| Ääriviiva | puolet paksuudesta + 0,5 mm kummaltakin puolelta; takapuolella 6 kpl 8 × 4 mm pidiketappia |
| Jakin poraus | käsin/porausjigillä reunasta (ei G-koodissa) |
| Kaulan G-koodi | `Neck_index_pins` → `Neck_top` (kaularauta, lavan pinta 8°, viritinreikien merkit) → käännä → `Neck_back_rough` (6 mm tasa) → `Neck_back_finish` (6 mm pallo, 0,75 mm askel) → `Neck_back_outline` (tapit). Koneistusasetus `neck_back_cut` "ball": takaosa yhtenä ohjelmana `Neck_back` pelkällä pallopäällä, ensin rouhinta kerroksittain (enintään 3 mm, 60 % askel) ja samassa ohjelmassa viimeistely 0,75 mm askeleella, ilman terän vaihtoa (laminoidussa kaulassa myös `Headstock_back`) |
| Kaulan aihio | Paksuus lasketaan tarpeesta (kaulan tai lavan syvin kohta liimapinnasta; `blank_thickness` voi pakottaa paksumman). Suora lapa: 20 mm lankku riittää. Kallistettu lapa kahdella tavalla: (1) yksi paksu lankku (8°: 36,6 mm) tai (2) kaulan 20 mm lankku + lavan alle liimattava pala; valinta `neck_blank`. Liimatussa jyrsitään ensin kaula 20 mm lankusta (tapit, kaularautaura, kaulan takapinta palan alkuun asti), sitten lavan alle liimataan lankun paksuinen pala (8°: 125 × 78 × 20 mm, 33 mm satulasta kärjen ohi), ja lapa jyrsitään omilla ohjelmillaan (`Headstock_top`, `Headstock_back_rough`, `Headstock_back_finish`) ennen koko kaulan ääriviivaa. Yläpinta = otelaudan liimapinta; 2 mm nahka pitää kaulan kehyksessä |
| Viritinreiät | vain 0,5 mm keskimerkit lavan pintaan — porataan pylväsporalla 8° kiilalla kohtisuoraan lapaan |
| DXF-vienti | Jokainen build kirjoittaa `Prototype001_plan.dxf`-tiedoston (koko soitin mallin koordinaateissa millimetreinä, X satulasta perää kohti, Y kaulan poikki; jokainen osa omalla tasollaan: runko, kaula, lapa, otelauta, satula, nauhaurat, inlayt, viritinreiät, kolot päältä ja takaa, reiät päältä ja takaa, johdinreiät, veisto, portaat, muotoilut, kaiverrus, levyt, keskilinja) ja `Prototype001_covers.dxf`-tiedoston (levyt rinnakkain leikattaviksi reikineen, aukkoineen ja nimineen, 10 mm välein). AutoCAD R12 (AC1009) ASCII DXF ilman kirjastoja; web-sovellus listaa ne ladattaviksi ja komentorivi tulostaa ne |
| SVG-pohja muuhun ohjelmaan | Runko- ja lapaeditorin *Export SVG* tallentaa ääriviivan SVG-pohjana 1:1 millimetreinä (`webapp.outline_template`, kuten editori näyttää: vasenkätinen peilattuna, 7- ja 8-kielisen runko levennettynä): tasolla *Outline* ääriviiva yhtenä Bézier-polkuna, jonka solmut ovat editorin kahvat (rungon Catmull-Rom ja lavan reunat ja kärki muuntuvat tarkasti), lukitulla tasolla *Reference* kaula, kaulatasku, mikit, kolot, jakki, keskilinja ja tallalinja tai kaula, satula, viritinreiät (katkoviivalla reunan vähimmäisetäisyys) ja kaularaudan kansi sekä kolme punaista kohdistusmerkkiä; rungon pohjassa lisäksi taso *Pattern*, jolla on nykyinen pintakuvio (kaiverrus) piirrettäväksi. Muokkaus Inkscapessa, Illustratorissa, Affinityssä tai CAD-ohjelmassa; *Import SVG* lukee sen takaisin (`webapp.import_outline`): kohdistusmerkit asettavat piirroksen paikalleen ja mittaan millimetrin tarkkuudella, vaikka ohjelma olisi siirtänyt tai skaalannut sen (72/96 dpi), ääriviiva on yhä `cgwOutline`-niminen polku tai suurin suljettu muoto viitetason ulkopuolella (päät enintään 3 mm erillään). Ääriviivasta tehdään editorin kahvat piirretylle viivalle: piirroksen omat solmut ensin ja lisää siellä, missä editorin käyrä poikkeaa yli 0,25 mm (murtoviivan alle 8 mm välein olevat solmut eivät ole kahvoja). Lavan reunat päättyvät samaan etäisyyteen satulasta ja kärki kulkee poikki reunan päästä toiseen; kärjen linja haetaan järjestyksessä: solmupari samalla etäisyydellä molemmilla puolilla (pohjan omat kulmat), kohta jossa sivu kääntyy kulkemaan enemmän poikki kuin pitkin, ja kärjestä taaksepäin millin välein. Kohtaavat kulmat tekevät terävän kärjen, takaisin kääntyvä kärki (koukku) hylätään syyn kera, samoin tiedosto ilman kohdistusmerkkejä tai suljettua ääriviivaa. Muuttamattomana viety ja tuotu ääriviiva palaa täsmälleen samaksi. *Pattern*-tason viivat — sekä ääriviivan viereen muualle piirretyt muodot ja pohjaan liitetyt kuvat (tiedostoon upotettu PNG, jonka tummat alueet jäljitetään ääriviivoiksi ilman kirjastoja: kaikki värityypit ja 1–16-bittiset, yli 480 pikselin kuva luetaan lohkoina, portaat silotetaan; JPEG, linkitetty tai lomitettu kuva jätetään pois syyn kera) — tuodaan piirretyksi pintakuvioksi (`body_engraving_pattern` "drawn"), jos niitä muutettiin (muuttamattomana satunnainen kuvio jää ennalleen); tyhjä taso kytkee kaiverruksen pois, puuttuva taso ei muuta sitä; tuonti on yksi kumottava muutos |
| Inlayn SVG-pohja | Inlay-editorin *Export SVG* tallentaa merkin SVG-pohjana 1:1 millimetreinä ensimmäisen merkin nauhavälissä (viitetasolla otelauta, nauhat, keskilinja ja katkoviivalla alue, jolla kulmat mahtuvat jokaiseen merkkiin; rekisteröintimerkit 15 mm satulan puolella); *Import SVG* lukee kulmat takaisin (käyrä kulmiksi 0,05 mm:n tarkkuudella, Douglas–Peucker, vähintään kolme kulmaa), siirtää katkoviivan ulkopuoliset kulmat sen sisään ja kertoo montako, ja merkistä tulee piirretty (`inlay_style` custom); muuttamattomana takaisin luettuna kulmat ovat täsmälleen samat. Pohjan sivu on vähintään huomautustensa levyinen |
| Inlay-editorin *Start from* | Listaa kaikki merkkityylit paitsi piirretyn; valittu ladataan heti (*Load* lataa uudelleen): tyyli vaihtuu ja piirretty merkki jätetään (kysytään ensin), joten editori näyttää tyylin merkin, jota voi muokata siitä eteenpäin |
| Otelaudan G-koodi | `Fretboard_index_pins` → `Fretboard_radius` (pallo) → `Fretboard_inlays` (1 mm, 30 000 rpm, enintään 0,2 mm kerrallaan; `inlay_spindle_speed` ja `inlay_step_down` säädettävissä koneistusasetuksissa, samat myös satulan uralle ja inlay-paloille) → `Fretboard_slots` (0,6 mm, 30 000 rpm, enintään 0,2 mm kerrallaan, eli 14 kierrosta 2,7 mm:n uraan, sädettä seuraten; kierrosnopeus `fret_slot_spindle_speed` ja askel `fret_slot_step_down` säädettävissä koneistusasetuksissa, jottei ohut terä katkea) → `Fretboard_outline` (tapit). Z-nolla on kaikissa aihion alkuperäinen yläpinta: säteen jyrsinnän jälkeen se jää laudan ympärille, ja Z kosketetaan siihen jokaisen terän vaihdon jälkeen, ei säteen pintaan (se on kruunussa 1 mm alempana, jolloin jokainen leikkaus menisi sen verran liian syvälle). Jokainen nauhaura alkaa 1 mm laudan reunan ulkopuolelta: terä tuodaan pikaliikkeellä 1 mm säteen pinnan yläpuolelle ja syötetään sisään yksi askel kerrallaan |
| Otelaudan aihio | 7 mm; harja 1 mm aihion pinnan alle |
| Otelaudan aihio | Koneistusasetuksissa: `fretboard_blank_length` ja `fretboard_blank_width` ostetun aihion mitat (lauta keskitetään aihioon; tyhjä = laudan ääriviiva + 35 mm joka puolelle, pidennettynä jos tapit tarvitsevat), `fretboard_blank_thickness` paksuus ennen sädettä (oletus 7 mm, vähintään laudan paksuus; jos säteen pinta menee pallojyrsimen Z-askelta syvemmälle, säde rouhitaan ensin kerroksittain) ja `fretboard_carrier_thickness` kantolevy: liian lyhyt aihio liimataan (tai teipataan) pidemmän kantolevyn päälle, ja kohdistustapit porataan kantolevyn läpi aihion päiden ulkopuolelle; tappiohjelman ohjeet kertovat kantolevyn vähimmäiskoon ja kuinka paljon se ulottuu aihion kummankin pään yli. 540 × 70 aihioon oletuslaudan tapit mahtuvat ilman kantolevyä (39 mm hukkaa kummassakin päässä); sivuille jää 6,9 mm, joten ääriviivaohjelma neuvoo kiinnittämään aihion alustaan teipillä |
| Inlay-palat | `Fretboard_inlay_pieces` (1 mm): piikkilanka- (myös piikkilanka 2), blokki- ja piirretyt merkit leikataan levystä (paksuus = inlay-syvyys, 2 mm), pyöreät pisteet eivät. Palat riveissä nauhajärjestyksessä, kaksipuolisella teipillä ilman pidikkeitä, näkyvä puoli ylös. Tasku ja pala seuraavat merkin ääriviivaa pyöristettynä terän säteellä molempiin suuntiin (`inlay_fit_outline`), pala 0,1 mm pienempi joka puolelta, joten se mahtuu taskuunsa |
| Ohjelmien kuvat | Pienen kappaleen (kansi tai mikin kehys) työratakuva on vähintään otsikkonsa levyinen, joten otsikko ei katkea kuvan reunaan |

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
