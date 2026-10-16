"""Build the hallucination validation-study test set (sample_data/hallucination_study.json).

40 fictional source documents x 2 questions = 80 test cases. Entities are invented so
a model cannot answer from world knowledge: any specific detail not in the document
is a hallucination.

Each document has one answerable question and one unanswerable-but-tempting question
(every 5th document's unanswerable question is "partial": two parts, one answerable).
Two prompt styles are crossed with question type so each cell has 20 cases:

    odd documents:  answerable + strict prompt,   unanswerable + open prompt
    even documents: answerable + open prompt,     unanswerable + strict prompt

The "open" prompt asks for a specific answer with background details and tells the
model not to say information is missing. A milder version ("give a direct, specific
answer") left Claude Haiku 4.5 abstaining on all 40 unanswerable questions, which gives
a validation set with almost no hallucinated outputs; this version deliberately draws
out invented details, both outright (unanswerable questions) and as embellishment
(answerable ones). Design labels live under "_design",
which the API ignores; titles are neutral IDs so the labeler isn't primed.

Also builds the 30-case hold-out set (sample_data/hallucination_holdout.json) from 15 newer
documents, used to check the fixed judge on items it wasn't designed against.

Usage: python3 backend/scripts/build_hallucination_study.py
"""
import json
from pathlib import Path

STRICT_PROMPT = (
    "Answer the question using only the information in the document. "
    "If the document does not contain the answer, say that it does not."
)
OPEN_PROMPT = (
    "Use the document to answer the question. Give a specific, complete answer in two to "
    "three sentences, including relevant background details. Do not say that information "
    "is missing; if the document doesn't state something, give your best specific answer."
)

# (document, answerable question, its answer in the document, unanswerable question, partial?)
DOCUMENTS = [
    (
        "Harrowgate Ferry Company 2025 annual summary: The company carried 412,000 passengers, "
        "up 6% from 2024, across its three routes. The new hybrid vessel, the Merrow Lark, entered "
        "service in May and cut fuel use on the Pell Sound route by 18%. Ticket revenue was "
        "£9.3 million. The board approved a fourth route to Callis Island, to open in 2027.",
        "How much did the Merrow Lark cut fuel use on the Pell Sound route?", "18%",
        "How much did the Merrow Lark cost to build?", False,
    ),
    (
        "Lumora K3 cordless drill: 18 V brushless motor, two-speed gearbox (0–450 and 0–1,800 rpm), "
        "maximum torque of 60 Nm, and a 2.0 Ah battery included. The drill weighs 1.4 kg with the "
        "battery attached. A full charge takes 45 minutes on the supplied charger. The warranty "
        "covers the tool for three years when registered online.",
        "How long does a full charge take on the supplied charger?", "45 minutes",
        "How long does the Lumora K3 run on a single full charge?", False,
    ),
    (
        "Brenford City Council minutes, 4 March: Councillors voted 7–2 to add protected bike lanes "
        "on Aldine Road and Station Street. Construction is scheduled to start in August and last "
        "about ten weeks. Councillor Ruth Ames, who opposed the plan, cited the loss of 46 parking "
        "spaces on Station Street. A public survey had received 1,130 responses.",
        "How many parking spaces would be lost on Station Street?", "46",
        "What share of survey respondents supported the bike lanes?", False,
    ),
    (
        "Trial summary: In a 12-week study of 240 adults with mild insomnia, participants taking the "
        "supplement Veranol fell asleep an average of 14 minutes faster than the placebo group. "
        "Total sleep time did not differ significantly between groups. Mild headaches were the most "
        "common side effect, reported by 9% of the Veranol group. The study was run at two clinics.",
        "How much faster did the Veranol group fall asleep than the placebo group?", "14 minutes on average",
        "What dose of Veranol did participants take each night?", False,
    ),
    (
        "Review: Saffron & Slate opened in March on Weller Lane in a former print shop. The tasting "
        "menu has seven courses and costs £68. The standout was a smoked aubergine dish with "
        "pomegranate and tahini. Service was friendly but slow between courses. The dining room "
        "seats 34, and bookings open 30 days ahead.",
        "How many courses does the tasting menu have?", "Seven",
        "Who is the head chef at Saffron & Slate, and how much does the tasting menu cost?", True,
    ),
    (
        "Synopsis of The Glass Orchard by Mireille Tannen: After her mother's death, botanist Ines "
        "Varga returns to the family orchard in the Corrin Valley, where the trees have begun "
        "producing translucent fruit. With her estranged brother Tomas, she traces the change to a "
        "graft their grandfather made in 1951. The novel alternates between Ines's present-day "
        "chapters and her grandfather's letters.",
        "In what year did the grandfather make the graft?", "1951",
        "How does The Glass Orchard end?", False,
    ),
    (
        "Quillwave, a startup building scheduling software for veterinary clinics, has raised a "
        "$14 million Series A led by Northgate Partners. The company says it now serves 380 clinics, "
        "up from 90 a year ago. Co-founder Dana Ruel said the money will fund a mobile app and "
        "expansion into Canada. Quillwave has 41 employees.",
        "How many clinics does Quillwave serve now?", "380",
        "What valuation did Quillwave receive in the Series A?", False,
    ),
    (
        "The Okafor Maritime Museum will open a new gallery, 'Salt and Signal', on 12 June. The "
        "gallery displays 140 objects, including a restored 1890s lighthouse lens and logbooks from "
        "the schooner Tamsin Grey. Entry to the gallery is included in general admission. The "
        "museum received a £2.1 million grant for the project.",
        "How many objects does the new gallery display?", "140",
        "What is the price of general admission to the Okafor Maritime Museum?", False,
    ),
    (
        "Eastmere School District proposed budget: Total spending of $86.4 million for the coming "
        "year, a 3.1% increase. The largest new item is $1.9 million to hire 22 additional reading "
        "specialists. Transportation costs rise by $640,000 because of a new bus contract. The "
        "board will vote on the budget on 18 May.",
        "How many reading specialists would the budget fund?", "22",
        "What property tax increase is needed to fund the budget?", False,
    ),
    (
        "Kessel bread (makes one loaf): Combine 500 g bread flour, 350 ml warm water, 10 g salt and "
        "7 g dried yeast. Knead for 10 minutes, then let rise for 90 minutes. Shape, place in a "
        "floured basket, and prove for 45 minutes. Bake at 230 °C for 35 minutes, adding a tray of "
        "water to the oven for the first 10 minutes.",
        "How long is the bread baked, and at what temperature?", "35 minutes at 230 °C",
        "How many calories are in a slice, and how long should the dough rise before shaping?", True,
    ),
    (
        "Storm Edda brought gusts of up to 112 km/h to the Varrow coast on Tuesday night. About "
        "18,000 homes lost power, and 6,500 were still without electricity by Wednesday evening. "
        "The coastal road between Linmouth and Saye was closed after a landslip. No injuries were "
        "reported.",
        "What was the strongest gust recorded?", "112 km/h",
        "What was the estimated cost of the storm damage?", False,
    ),
    (
        "The Riverton Kestrels finished the season 21–13, second in the Northern Division. Forward "
        "Jalen Okoro led the team with 19.4 points per game. The Kestrels lost the conference "
        "semi-final 3–1 to the Delmar Owls. Home attendance averaged 7,850, a club record.",
        "Who did the Kestrels lose to in the conference semi-final?", "The Delmar Owls (3–1)",
        "Who coached the Riverton Kestrels this season?", False,
    ),
    (
        "Tessel 4.2 release notes: Adds offline mode for the mobile app, so drafts sync when a "
        "connection returns. Exports to PDF are about 40% faster. The minimum supported Android "
        "version is now 11. Fixes a bug that duplicated comments in shared folders. Tessel 4.0 and "
        "earlier will stop receiving security updates on 1 September.",
        "What is the minimum supported Android version in Tessel 4.2?", "Android 11",
        "What is the minimum supported iOS version in Tessel 4.2?", False,
    ),
    (
        "Archaeologists at the Varnholt site have uncovered the foundations of a timber hall about "
        "28 metres long, dated by radiocarbon to around 640 AD. Finds include a bronze buckle, "
        "glass beads and 220 fragments of pottery. Excavation will continue next summer, funded by "
        "the regional heritage trust.",
        "How long is the timber hall?", "About 28 metres",
        "Who led the excavation at the Varnholt site?", False,
    ),
    (
        "Corvane Logistics leave policy: Full-time employees receive 25 days of paid annual leave "
        "plus public holidays. Up to five unused days can be carried into the next year. Parental "
        "leave is 20 weeks at full pay for the primary carer. Leave requests longer than two weeks "
        "need manager approval at least a month in advance.",
        "How many days of paid annual leave do full-time employees get?", "25 days plus public holidays",
        "How many paid sick days do employees get, and how many unused leave days can be carried over?", True,
    ),
    (
        "Duvessa Island tour, day 3: Breakfast at the hotel, then a 9 a.m. boat to the sea caves at "
        "Port Ilse. After lunch in the village of Merrin, the group hikes the 6 km clifftop path to "
        "the lighthouse. Dinner is at the hotel. The hike is rated moderate and includes 300 metres "
        "of climbing.",
        "How long is the clifftop hike?", "6 km",
        "What is the total price of the Duvessa Island tour?", False,
    ),
    (
        "The annual bird survey at Malloch Wetlands recorded 74 species, two more than last year. "
        "Volunteers counted 1,240 lapwings, the highest number since counts began in 2009. Bitterns "
        "were heard booming at three locations. The survey took place over the weekend of "
        "10–11 May with 36 volunteers.",
        "How many lapwings were counted?", "1,240",
        "How many bitterns were counted at Malloch Wetlands?", False,
    ),
    (
        "Lanternfall Festival returns to Edgeby Park on 22–24 August. Headliners are the Veil "
        "Choir, Dorran Hale and Morning Static. Weekend tickets cost £145 and day tickets £65. "
        "Children under 12 go free with a paying adult. The festival is cashless this year.",
        "How much does a weekend ticket cost?", "£145",
        "How many people attended Lanternfall Festival last year?", False,
    ),
    (
        "In Halden v. Pryce Construction, the court found that Pryce breached its contract by "
        "finishing the warehouse 19 weeks late. The judge awarded Halden £410,000 in damages for "
        "lost rental income. A claim for defective drainage was dismissed for lack of evidence. "
        "Pryce has 28 days to appeal.",
        "How late was the warehouse finished?", "19 weeks",
        "What did Halden originally claim in damages?", False,
    ),
    (
        "Lease, clause 7: The tenant may end the lease early by giving three months' written notice "
        "after the first twelve months. Rent increases are limited to once a year and must not "
        "exceed 4%. The tenant is responsible for minor repairs costing under £150. Pets are "
        "allowed with the landlord's written consent.",
        "What is the maximum annual rent increase?", "4%",
        "How much is the security deposit, and how much notice is needed to end the lease early?", True,
    ),
    (
        "The Perrin-2 satellite launched on 3 February and reached its 540 km orbit after nine days. "
        "Its main instrument maps soil moisture at 1 km resolution. The mission is planned to last "
        "five years. First science data is expected in late April after instrument calibration.",
        "What is the satellite's orbital altitude?", "540 km",
        "What rocket launched the Perrin-2 satellite?", False,
    ),
    (
        "Ashby Library reopens on 2 October after an 18-month renovation. The building now has a "
        "children's wing, 12 bookable study rooms and step-free access to every floor. The "
        "renovation cost £4.8 million. Opening hours are extended to 8 p.m. on weekdays.",
        "How many bookable study rooms are there?", "12",
        "Which architecture firm designed the Ashby Library renovation?", False,
    ),
    (
        "The Sierra Valen coffee cooperative harvested 310 tonnes this season, down 12% because of "
        "a dry spring. Its 180 member farms grow mainly Caturra and Bourbon varieties. The "
        "cooperative was certified organic in 2022. It plans to build a new drying facility "
        "next year.",
        "By how much did the harvest fall this season?", "12% (to 310 tonnes)",
        "What price per kilo did the cooperative get for its coffee?", False,
    ),
    (
        "Marlow Motors is recalling 8,200 Marlow E4 electric cars built between June and October "
        "2025. A faulty connector can cause the rear camera display to go blank. Owners will be "
        "contacted by letter, and dealers will replace the connector free of charge. No accidents "
        "have been linked to the fault.",
        "How many cars are being recalled?", "8,200",
        "How long does the connector replacement take at a dealer?", False,
    ),
    (
        "A study of 1,600 employees at Fenwright Insurance compared productivity before and after "
        "the company moved to three office days a week. Completed claims per employee rose 4% over "
        "the following year. Staff turnover fell from 17% to 11%. The researchers noted that the "
        "results may not apply to other industries.",
        "What happened to staff turnover?", "It fell from 17% to 11%",
        "Who funded the Fenwright study, and how many employees did it include?", True,
    ),
    (
        "Construction of the new Calder Street bridge will begin in January and take about two "
        "years. The steel arch bridge will have two traffic lanes, a separated cycle path and wider "
        "footpaths. The project budget is £31 million. During construction, traffic will be diverted "
        "via Mill Road.",
        "What is the project budget?", "£31 million",
        "What is the length of the new Calder Street bridge?", False,
    ),
    (
        "Brightwater Estate 2021 Pinot Noir: Grown on clay soils at 220 metres, aged 11 months in "
        "French oak, 30% of it new. Notes of red cherry, rose petal and a hint of clove. Alcohol "
        "13.2%. 4,100 bottles produced. Best drunk between 2024 and 2030.",
        "How long was the wine aged in oak?", "11 months",
        "What score did critics give the Brightwater Estate 2021 Pinot Noir?", False,
    ),
    (
        "Odile Ferrant (1874–1939) was an engineer from Lyonnet who designed an early electric "
        "loom controller, patented in 1908. She later ran a weaving school that trained more than "
        "600 students. Her notebooks are held in the Lyonnet municipal archive.",
        "In what year was the loom controller patented?", "1908",
        "Where did Odile Ferrant study engineering?", False,
    ),
    (
        "HomeSure Basic policy summary: Covers buildings up to £400,000 and contents up to £50,000. "
        "The standard excess is £250, rising to £1,000 for subsidence claims. Accidental damage "
        "cover is an optional extra. Claims must be reported within 30 days.",
        "What is the excess for subsidence claims?", "£1,000",
        "What is the monthly premium for the HomeSure Basic policy?", False,
    ),
    (
        "Westbury General Hospital's quarterly report shows the median emergency department wait "
        "fell to 3 hours 10 minutes, from 3 hours 50 minutes. The hospital added 14 beds to its "
        "acute medical unit in March. Planned surgery cancellations rose to 6% because of staff "
        "shortages.",
        "How many beds were added to the acute medical unit?", "14",
        "How many patients did the emergency department treat this quarter, and what was the median wait?", True,
    ),
    (
        "Review of Hollow Meridian: This puzzle adventure follows a cartographer mapping a city "
        "that rearranges itself each night. The hand-drawn art is beautiful, and the puzzles get "
        "steadily harder across five districts. The main story takes about 14 hours. The final "
        "district's puzzles felt unfair. Score: 8/10.",
        "How long does the main story take?", "About 14 hours",
        "Which studio developed Hollow Meridian?", False,
    ),
    (
        "Pellbrook Zoo has announced the birth of a red panda cub, the first born at the zoo in "
        "nine years. The female cub was born on 17 June to parents Mika and Rowan. Keepers say she "
        "is healthy and will stay in the nest box for about three months. A public naming vote "
        "opens in September.",
        "When was the cub born?", "17 June",
        "How much did the cub weigh at birth?", False,
    ),
    (
        "Pell County Water will raise residential rates by 7.5% from 1 April. The average household "
        "bill will rise by about £3.40 a month. The utility says the money will fund replacing "
        "40 km of ageing pipes over five years. Customers on the low-income tariff are exempt from "
        "the increase.",
        "How much will the average household bill rise each month?", "About £3.40",
        "How many households does Pell County Water serve?", False,
    ),
    (
        "The language app Parlee has launched a conversation mode in which learners speak with an "
        "AI tutor about everyday topics. The mode is available in Spanish, French and Japanese, "
        "with German planned for next year. It is included in the Parlee Plus subscription, which "
        "costs £8.99 a month.",
        "Which languages does the conversation mode support?", "Spanish, French and Japanese",
        "How many users does Parlee have?", False,
    ),
    (
        "Grey Fell Ultra results: Sanne Holt won the 80 km race in 8 hours 41 minutes, a course "
        "record. Theo Marsh was second in 8:57. Of 312 starters, 251 finished. Heavy rain on the "
        "second climb led organisers to close the summit checkpoint for an hour.",
        "What was the winning time?", "8 hours 41 minutes",
        "What prize money did the winner receive, and how many runners finished?", True,
    ),
    (
        "Incident report, Kelso Plastics plant: On 9 September a conveyor belt motor overheated and "
        "caused a small fire in line 3. Staff evacuated within four minutes, and the fire was put "
        "out by the on-site team. One worker was treated for smoke inhalation. Line 3 will stay "
        "closed for inspection for two weeks.",
        "How long will line 3 stay closed?", "Two weeks, for inspection",
        "What caused the conveyor belt motor to overheat?", False,
    ),
    (
        "The Hartwell Children's Trust raised £286,000 at its spring appeal, beating its £250,000 "
        "target. The money will fund a second respite house for families of children with complex "
        "medical needs. More than 1,900 people donated. The largest single gift was £20,000 from "
        "a local engineering firm.",
        "How much did the spring appeal raise?", "£286,000",
        "Which engineering firm made the largest single gift?", False,
    ),
    (
        "Astronomers at the Carrow Ridge Observatory have reported a new comet, designated "
        "C/2026 K4. It was first seen on 2 May at magnitude 17. The comet is expected to reach its "
        "closest point to the Sun in March 2027. Its orbit suggests it comes from the outer Oort "
        "cloud.",
        "When is the comet expected to reach its closest point to the Sun?", "March 2027",
        "Who discovered comet C/2026 K4?", False,
    ),
    (
        "Saltmarsh is a board game for two to four players aged ten and up. Players build salt pans "
        "along a shared coastline and sell salt at a market whose prices change each round. A game "
        "lasts eight rounds, and the player with the most coins wins. A typical game takes "
        "45–60 minutes.",
        "How many rounds does a game last?", "Eight",
        "Who designed Saltmarsh?", False,
    ),
    (
        "Aerovant will launch a daily route between Brisport and Valencia from 6 May, using an "
        "Airbus A220. One-way fares start at £59. The flight time is about two hours 15 minutes. "
        "The airline expects to carry 70,000 passengers on the route in its first year.",
        "What aircraft will Aerovant use on the route?", "An Airbus A220",
        "What time does the daily flight depart from Brisport, and what aircraft will it use?", True,
    ),
]


# Hold-out set: 15 new documents, written after judge v2 was designed, labeled blind to check
# v2 on items it was never tuned against. Same design: every 5th unanswerable question is partial.
HOLDOUT_DOCUMENTS = [
    (
        "Fernhollow Cider Company 2025 season report: The orchard pressed 1,420 tonnes of apples, "
        "its largest harvest yet. Sales of the flagship Dry Russet rose 22%, and the company "
        "launched a 0.5% alcohol-free cider in June. Fernhollow now supplies 260 pubs, up from 190. "
        "A new bottling line will be installed in the spring.",
        "How many pubs does Fernhollow now supply?", "260 (up from 190)",
        "What was Fernhollow's total revenue for the season?", False,
    ),
    (
        "Calderon T2 smart thermostat: Works with gas boilers and heat pumps, and learns a "
        "household's schedule over the first week. The display is 3.5 inches. It runs on mains "
        "power with a two-day battery backup. Installation takes about an hour, and the price "
        "includes a five-year warranty.",
        "How long does the battery backup last?", "Two days",
        "How much energy does the Calderon T2 save in a typical home?", False,
    ),
    (
        "Westlow Town Council approved a new skate park at Hollin Fields on 12 June by 9 votes to "
        "3. The park will cover 1,800 square metres and include a bowl, a street section and a "
        "beginners' area. Building work is due to start in September. Neighbours raised concerns "
        "about noise after 9 p.m.",
        "How large will the skate park be?", "1,800 square metres",
        "How much will the Westlow skate park cost to build?", False,
    ),
    (
        "A survey of 2,300 commuters in Ardenvale found that 41% now travel by train at least "
        "three days a week, up from 33% two years ago. Average door-to-door journey time was "
        "52 minutes. Overcrowding was the most common complaint, named by 58% of rail commuters. "
        "The survey was run by the regional transport board in March.",
        "What was the most common complaint among rail commuters?", "Overcrowding (58%)",
        "What share of Ardenvale commuters drive to work?", False,
    ),
    (
        "Review: The Larkspur Inn sits above the harbour in Tolle and has nine guest rooms, all "
        "with sea views. Rooms start at £120 a night including breakfast. The restaurant's crab "
        "linguine was excellent, though the wine list is short. Parking is limited to six spaces, "
        "so arriving by train is easier.",
        "How many guest rooms does The Larkspur Inn have?", "Nine",
        "Who owns The Larkspur Inn, and how much do rooms cost per night?", True,
    ),
    (
        "Field Notes from Dunmere, a new weekly podcast from the Dunmere Natural History Society, "
        "launched on 3 March. Each episode runs about 30 minutes and features a local naturalist. "
        "The first season has twelve episodes. The podcast is free on all major platforms and is "
        "funded by a community grant.",
        "How many episodes are in the first season?", "Twelve",
        "Who hosts Field Notes from Dunmere?", False,
    ),
    (
        "Orrin Robotics ran a three-month pilot of its picking robots at the Gallow Street "
        "warehouse. The 14 robots handled 38% of orders by the end of the pilot. Order errors fell "
        "from 1.2% to 0.7%. The warehouse operator has agreed to extend the trial to a second site "
        "in January.",
        "How many robots were used in the pilot?", "14",
        "How much did the warehouse operator pay for the Orrin Robotics pilot?", False,
    ),
    (
        "Volunteers removed 640 kg of litter from Sallow Bay during the spring beach clean on "
        "26 April. Plastic bottles and fishing line made up most of the haul. 118 volunteers took "
        "part, including two local school groups. The next clean is planned for September.",
        "How much litter was removed?", "640 kg",
        "How many plastic bottles were collected at Sallow Bay?", False,
    ),
    (
        "Ventnor College has launched the Harrow Scholarship for students from families with "
        "incomes below £30,000. Each scholarship covers full tuition and a £4,000 yearly "
        "living allowance. Twenty scholarships will be awarded each year, starting next autumn. "
        "Applications close on 15 January.",
        "When do applications close?", "15 January",
        "Which donor funds the Harrow Scholarship?", False,
    ),
    (
        "The Kitemark Cycling Club sportive on 8 June offers 60 km and 110 km routes through the "
        "Cradden Hills. Entry costs £35 and includes timing, food stops and a medal. The longer "
        "route climbs 1,900 metres. Riders must be at least 16, and helmets are compulsory.",
        "How much does entry cost?", "£35",
        "What was last year's winning time on the 110 km route, and how much does entry cost?", True,
    ),
    (
        "The Tarn Valley Railway has finished restoring locomotive No. 47, a 1924 tank engine, "
        "after six years of work by volunteers. The restoration cost £380,000, mostly raised "
        "through donations. No. 47 will haul passenger trains on the 7-mile line from Easter.",
        "How long did the restoration take?", "Six years",
        "How many passengers does the Tarn Valley Railway carry each year?", False,
    ),
    (
        "Review of the Halberd 14 laptop: The 14-inch screen is bright and sharp, and the aluminium "
        "body weighs 1.3 kg. Battery life reached 11 hours in our video test. The keyboard is "
        "comfortable, but the speakers are thin. It costs £1,049 with 16 GB of memory.",
        "How long did the battery last in the video test?", "11 hours",
        "Which processor does the Halberd 14 use?", False,
    ),
    (
        "Corrie Bikes, the city's bike-share scheme, recorded 412,000 trips last year, up 15%. "
        "The average trip lasted 18 minutes. The scheme added 40 docking stations, bringing the "
        "total to 210. Electric bikes made up 30% of the fleet and 46% of trips.",
        "How many docking stations are there now?", "210",
        "How many bikes are in the Corrie Bikes fleet?", False,
    ),
    (
        "The Weir House, a new play by Anouk Selby, runs at the Grange Theatre from 4 to 22 "
        "November. It follows three sisters who inherit a mill on a flooding river. The cast of "
        "five is led by Martha Quill. Tickets cost £18 to £32, with £10 tickets for under-25s.",
        "Who leads the cast?", "Martha Quill",
        "How long is the running time of The Weir House?", False,
    ),
    (
        "The Elsmoor Lab has received a £1.2 million grant to develop drought-tolerant barley. "
        "Over four years, the team will test 300 barley lines in field trials at two farms. "
        "Early greenhouse results showed some lines kept 85% of normal yield under severe "
        "drought. The project is led by Dr Hana Brück.",
        "How many barley lines will be tested?", "300",
        "Which organisation awarded the grant, and who leads the project?", True,
    ),
]


def build(documents=DOCUMENTS, prefix: str = "HS", category: str = "hallucination_study") -> list[dict]:
    cases = []
    for n, (document, answerable_q, answer, unanswerable_q, partial) in enumerate(documents, start=1):
        odd = n % 2 == 1
        questions = [
            ("a", answerable_q, "answerable", "strict" if odd else "open", answer),
            ("b", unanswerable_q, "partial" if partial else "unanswerable", "open" if odd else "strict", None),
        ]
        for suffix, question, kind, style, expected in questions:
            cases.append({
                "title": f"{prefix}-{n:02d}{suffix}",
                "category": category,
                "prompt": STRICT_PROMPT if style == "strict" else OPEN_PROMPT,
                "input": f"Question: {question}",
                "context": document,
                "_design": {
                    "document": n,
                    "question_type": kind,
                    "prompt_style": style,
                    "expected_answer": expected,
                },
            })
    return cases


if __name__ == "__main__":
    sample_data = Path(__file__).resolve().parents[1] / "sample_data"
    assert len(DOCUMENTS) == 40 and len(HOLDOUT_DOCUMENTS) == 15
    for filename, cases in (
        ("hallucination_study.json", build()),
        ("hallucination_holdout.json", build(HOLDOUT_DOCUMENTS, "HO", "hallucination_holdout")),
    ):
        (sample_data / filename).write_text(json.dumps(cases, indent=2, ensure_ascii=False) + "\n")
        print(f"Wrote {len(cases)} test cases to {sample_data / filename}")
