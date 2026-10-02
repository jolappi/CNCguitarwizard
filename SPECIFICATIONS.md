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
| Multiscale | Valinnainen `bass_scale_length`: `scale_length` on silloin diskanttimensuuri ja `bass_scale_length` bassomensuuri (pidempi, enintään 1,15-kertainen); `perpendicular_fret` (oletus 7, 0 = satula) on kohtisuorassa. Jokainen nauha on suora ja osuu jokaisella kielellä tarkalleen oikeaan kohtaan; keskilinja saa mensuurien keskiarvon. Talla voi olla mikä tahansa: se pysyy suorana keskilinjan mensuurin kohdalla ja tallapalat säädetään kunkin kielen mensuuriin (säätövaran on riitettävä puoleen mensuurierosta kumpaankin suuntaan). Poikkeus on Tune-o-matic, jonka säätövara on liian pieni: sen tolpat (kohta, jolla kielet lepäävät) käännetään aina nauhojen mukaan, stop tail pysyy paikallaan. Hardtailin läpivientireiät voi kääntää samoin (`body_bridge_follows_fan`). Mikkien kääntö on valinta (`body_pickups_follow_fan`): auto kääntää ne paitsi Tune-o-maticin kanssa, yes aina, no ei koskaan |
| Lukkosatula | `locking_nut`: auto (oletus) ottaa Floyd Rose Original R2 -lukkosatulan (41,3 mm), kun tallana on Floyd Rose, muuten tavallinen satula; none, r2 tai r3 (42,85 mm, vaatii yhtä leveän `nut_width`:n; web-lomake leventää satulan leveyden 43 mm:iin R3:a valittaessa) valitsevat suoraan. Satula ruuvataan päältä kahdella ruuvilla (13,59 mm välein, 7,5 mm satulalinjan takana, 2,5 mm × 8 mm esiporaus käsin satulan läpi). Sen etureuna on satulalinjalla ja hylly jatkuu 16 mm taaksepäin, joten lavan pinta, siirtymä ja lavan puolen truss rod -tasku alkavat sen verran taempaa. Satulan yläpinta on 0,38 mm nauhojen yläpintaa ylempänä (`fret_height` 1,2 mm): R2:n hylly on 1,73 mm liimapinnan yläpuolella, joten otelauta jatkuu satulan alle ja jyrsitään siinä hyllyn korkeuteen; R3:n hylly jäisi alle 1 mm:n, joten se istuu kaulan omalla hyllyllä 0,48 mm shimmin päällä |
| Satula urassa (Fender/Telecaster) | `nut_style` "slot": otelauta jatkuu satulalinjan ohi, ja siihen jyrsitään `nut_thickness` (3,5 mm) levyinen ura `nut_slot_depth` (3 mm) harjan alapuolelle; satula liimataan uraan, etupinta satulalinjalla. Uran takana otelauta jatkuu täyskorkeana `nut_slot_lip` (3 mm) ja loivenee sitten liimapintaan `nut_slot_taper` (3 mm) matkalla, eli otelauta päättyy 9,5 mm satulalinjan taakse. Ura jyrsitään inlay-ohjelmassa 1 mm terällä, loivennus ääriviivaohjelmassa 0,5 mm portain tasaterällä (hiotaan tasaiseksi). Uran alle on jäätävä vähintään 1 mm otelautaa. Lukkosatula korvaa satulan tyylistä riippumatta. Lavan puolelta säädettävä kaularauta avataan silloin Fender-tyylisesti ilman kantta (ks. Spoke wheel) |
| Telecaster-kaula | Lapaeditorin *Start from* → Telecaster neck (`NECK_TEMPLATES`): satula urassa, suora 0° lapa, 6 virittimen rivi (`6_inline`), Telecaster-lavan muoto piirrettynä (204 mm oletusrivin ympärillä, muokattavissa) ja kaularaudan säätö kantapäässä (vintage); `truss_rod_adjustment` headstock antaa modernin säädön satulan takaa |
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
mahtuvat. Kahler 7300, Floyd Rose ja Tune-o-matic on mitoitettu kuudelle
kielelle, joten ne eivät ole valittavissa 7- ja 8-kielisille.
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
myös pyöreä kytkinkolo. Ohjainkolon voi kääntää (`control_angle_degrees`) kolon keskipisteen ympäri kansineen ja potikoineen (Tele-levy ruuveineen ja teräkytkimen aukkoineen); akun kotelolla ja jakilla on omat kulmansa, pyöreitä koloja ei käännetä. Runkoeditorissa kääntö tehdään Shift-raahauksella, ja uusi piirtopiste lisätään klikkaamalla ääriviivaa. Ohjainkoloa ja sen kantta voi venyttää tai lyhentää pituusakselinsa suunnassa (`control_stretch`, mm keskeltä molempiin päihin puoliksi); päät säilyttävät pyöristyksensä, leveys ei muutu, ja Gibson- ja rivikolon reunimmaiset potikat sekä Tele-levyn ruuvit, kytkinaukko ja takimmainen potikka siirtyvät päiden mukana. Liian lyhyeksi kutistettu kolo hylätään. Samoin kolon ja kannen voi leventää tai kaventaa poikittain (`control_stretch_across`); Gibson-kolon potikkarivit siirtyvät kauemmas toisistaan, ja rivikolon sekä Tele-levyn päät pysyvät puoliympyröinä. Kolon on oltava vähintään 16 mm leveä (minipotikan runko). Editorissa kannen päissä ja sivuilla on neliökahvat: kahvaa raahatessa vastakkainen pää tai sivu pysyy paikallaan. Mikkivalitsimeksi valitaan (`body_switch`)
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
tule, ja pleksi jatkuu tallan ohi kontrollien puolella.

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
sitä voi raahata kaulan suunnassa.

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
raahattu piste tekee terävän tai pyöreän pään ja sisäänpäin raahattu
loven. Myös reunat ovat pyöreitä käyriä, jotka saavat kaartua kahvojen
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
| Kannan säätö | Holkin reikä porataan käsin (CNC ei aja vaakasuoraa porausta; mukana mallissa ja G-coden ohjeissa); rungon kaulataskun päähän lovi holkin päälle, 1 mm välys, 15,5 mm syvä |
| Lavan säätö | Kanava jatkuu satulan alta; mutteri 32 mm urassa lavan pinnassa, uralle Gibson-tyylinen kansi (3 ruuvia) levystä omana NC-ohjelmanaan |
| Satulan istukka | Kannan säädössä satulahylly on tasainen koko satulan leveydeltä (myös monimensuurin vinolla satulalla). Lavan säädössä raudan tasku kulkee satulan alta, joten G-koodin ohje pyytää liimaamaan taskuun raudan päälle puisen täytepalan (esim. 9 × 5 mm) satulahyllyn tasoon ennen satulan liimausta |
| Valinnaiset aukot | Holkin reikä (`truss_rod_sleeve_bore`) ja lavan ura kansineen (`truss_rod_trough`) ovat oletuksena mukana, mutta ne voi jättää pois |
| Jyrsintä | Porras ja tasku ajetaan terän säteen (3 mm) verran naapurikolon päälle ja tasku säätöpään suuntaan, jotta pyöreä terä ei jätä kulmiin ulkonemia raudan kanttisille paloille; kanavan ankkuripää jyrsitään sellaisenaan |
| Kohdistus | 2 × 6 mm kohdistustappi kaksipuoliseen koneistukseen |

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
| Jakki | Ø 12,5 poraus alkaa siitä, missä muodon jakkilinja (oletus 742, 107,5 suuntaan 202,5°) kohtaa rungon ääriviivan, millä tahansa rungolla, ja jatkuu 3 mm ohjainkolon seinän yli (muuten 55 mm; `body_jack_depth` kiinnittää pituuden). `body_jack`: side (kylkilevy tai putkijakki), cup (Tele-kuppi tai Electrosocket: 7/8" eli 22,2 mm upotus 25 mm syvä reunassa) tai strat (Strat-tyylinen kansilevy päällä: Ø 25,4 × 32 mm kolo ylhäältä 4 mm reunasta, poraus jatkuu siitä ohjainkoloon). Runkoeditori varoittaa, jos poraus ei osu ohjainkoloon |

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
| Kaulan aihio | Paksuus lasketaan tarpeesta (kaulan tai lavan syvin kohta liimapinnasta; `blank_thickness` voi pakottaa paksumman). Suora lapa: 20 mm lankku riittää. Kallistettu lapa kahdella tavalla: (1) yksi paksu lankku (8°: 36,6 mm) tai (2) kaulan 20 mm lankku + lavan alle liimattava pala; valinta `neck_blank`. Liimatussa jyrsitään ensin kaula 20 mm lankusta (tapit, kaularautaura, kaulan takapinta palan alkuun asti), sitten lavan alle liimataan lankun paksuinen pala (8°: 125 × 78 × 20 mm, 33 mm satulasta kärjen ohi), ja lapa jyrsitään omilla ohjelmillaan (`Headstock_top`, `Headstock_back_rough`, `Headstock_back_finish`) ennen koko kaulan ääriviivaa. Yläpinta = otelaudan liimapinta; 2 mm nahka pitää kaulan kehyksessä |
| Viritinreiät | vain 0,5 mm keskimerkit lavan pintaan — porataan pylväsporalla 8° kiilalla kohtisuoraan lapaan |
| Otelaudan G-koodi | `Fretboard_index_pins` → `Fretboard_radius` (pallo) → `Fretboard_inlays` (1 mm) → `Fretboard_slots` (0,6 mm, 3 × 0,9 mm sädettä seuraten) → `Fretboard_outline` (tapit) |
| Otelaudan aihio | 7 mm; harja 1 mm aihion pinnan alle |
| Inlay-palat | `Fretboard_inlay_pieces` (1 mm): piikkilanka- ja blokki-merkit leikataan levystä (paksuus = inlay-syvyys, 2 mm), pyöreät pisteet eivät. Palat riveissä nauhajärjestyksessä, kaksipuolisella teipillä ilman pidikkeitä, näkyvä puoli ylös. Tasku ja pala seuraavat merkin ääriviivaa pyöristettynä terän säteellä molempiin suuntiin (`inlay_fit_outline`), pala 0,1 mm pienempi joka puolelta, joten se mahtuu taskuunsa |

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
