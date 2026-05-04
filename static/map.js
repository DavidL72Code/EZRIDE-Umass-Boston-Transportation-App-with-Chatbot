// ── Directions state ──────────────────────────────────────────────────────────
let _map = null;
let routeLayer = null;
let lastUserLocation = null;
let _dirDestCoords = null;
let _dirDestName = null;
let _lastPanelFn = null;
let _dirFromCoords = null;   // null = use GPS
let _dirFromLabel  = "My Location";
let _dirActiveTab  = "walking";
let _autoTimer     = null;

function getDirOrigin() {
  return _dirFromCoords || lastUserLocation;
}

// ── Map data (coordinates from OpenStreetMap / Overpass API) ─────────────────

const PARKING_LOTS = [
  {
    id: "west-garage",
    name: "West Garage",
    type: "garage",
    coords: [42.31518, -71.04151],
    driveCoords: [42.31494, -71.04131], // OSM parking_entrance node
    description: "Multi-level gated parking garage. Pay-on-foot kiosks accept cash or credit. Reserved spaces available.",
    dailyRates: [
      ["1 hour (minimum)", "$7.00"],
      ["1–1.5 hours", "$8.00"],
      ["2 hours", "$9.00"],
      ["2–2.5 hours", "$10.00"],
      ["3 hours", "$11.00"],
      ["Over 3 hours / max", "$15.00"],
      ["Evening & Weekend", "$10.00"],
    ],
    permitRates: [
      ["Commuter Student — semester", "$550"],
      ["Faculty — semester", "$550"],
      ["Reserved (West Garage only)", "$1,200/semester"],
      ["Summer session", "$70"],
    ],
    payment: "Pay-on-foot · cash or credit",
  },
  {
    id: "lot-d",
    name: "Lot D",
    type: "lot",
    coords: [42.31691, -71.03875],
    description: "Gated surface parking lot on campus. Credit card only.",
    dailyRates: [
      ["Daily rate", "$15.00"],
      ["Evening & Weekend (after 4 pm)", "$10.00"],
    ],
    permitRates: [
      ["Commuter Student — semester", "$550"],
      ["Faculty — semester", "$550"],
      ["Summer session", "$70"],
    ],
    payment: "Credit card only",
  },
  {
    id: "campus-center-garage",
    name: "Campus Center Garage",
    type: "garage",
    coords: [42.31286, -71.03702],
    driveCoords: [42.31310, -71.03698], // entrance road shared with drop-off, south of drop-off zone
    description: "Underground gated garage adjacent to the Campus Center. Pay-on-foot kiosks accept credit only.",
    dailyRates: [
      ["Daily rate", "$15.00"],
      ["Evening & Weekend (after 4 pm)", "$10.00"],
    ],
    permitRates: [
      ["Commuter Student — semester", "$550"],
      ["Faculty — semester", "$550"],
    ],
    payment: "Pay-on-foot · credit only",
  },
  {
    id: "quad-lot",
    name: "Quad Lot",
    type: "lot",
    coords: [42.31450, -71.03824],
    description: "Open surface lot next to the Quad. Pay by plate using the Passport Parking app (Zone 21266) or ParkingApp.com.",
    dailyRates: [
      ["Daily rate", "$15.00"],
      ["Evening & Weekend (after 4 pm)", "$10.00"],
    ],
    payment: "Pay-by-plate · Passport Parking app (Zone 21266)",
  },
  {
    id: "emk-lot",
    name: "Edward M. Kennedy Institute Lot",
    type: "lot",
    coords: [42.31520, -71.03623],
    description: "Surface parking lot adjacent to the Edward M. Kennedy Institute for the United States Senate.",
    dailyRates: [
      ["Daily rate", "$15.00"],
      ["Evening & Weekend (after 4 pm)", "$10.00"],
    ],
    payment: "See signage on site",
  },
  {
    id: "mass-archives-lot",
    name: "Massachusetts Archives Parking",
    type: "lot",
    coords: [42.31447, -71.03466],
    description: "Surface parking lot serving the Massachusetts Archives and adjacent buildings.",
    dailyRates: [
      ["See on-site signage", "—"],
    ],
    payment: "See signage on site",
  },
  {
    id: "jfk-library-lot",
    name: "JFK Library Parking Lot",
    type: "lot",
    coords: [42.31506, -71.03431],
    description: "Surface parking lot serving the JFK Presidential Library & Museum and the adjacent Edward M. Kennedy Institute.",
    dailyRates: [
      ["See on-site signage", "—"],
    ],
    payment: "See signage on site",
  },
  {
    id: "bayside",
    name: "Bayside Lot (Off-Campus)",
    type: "lot",
    coords: [42.32068, -71.04627],
    description: "Off-campus surface lot accessible via Mt. Vernon St. No overnight parking. UMass shuttle connects to main campus.",
    dailyRates: [
      ["Daily rate", "$9.00"],
    ],
    permitRates: [
      ["Commuter Student — semester", "$504"],
      ["Faculty — semester", "$504"],
    ],
    payment: "Pay-by-plate only · Passport Parking app (Zone 21251)",
  },
];

const SHUTTLE_STOPS = [
  {
    id: "stop-jfk",
    name: "JFK/UMass T Station",
    coords: [42.32041, -71.05178],
    type: "mbta",
    routeStopId: 104,
    routes: ["Red Line", "UMass Shuttle"],
    schedule: "Mon–Fri 5:30 AM – 1:30 AM · Sat–Sun 7:30 AM – 1:30 AM",
    notes: "First inbound stop. Board here from the Red Line to reach campus.",
  },
  {
    id: "stop-bayside-in",
    name: "Bayside Inbound",
    coords: [42.31947, -71.04660],
    type: "shuttle",
    routeStopId: 109,
    routes: ["UMass Shuttle"],
    schedule: "Mon–Fri 5:30 AM – 1:30 AM · Sat–Sun 7:30 AM – 1:30 AM",
    notes: "Stop at the Bayside Expo Center area before heading to campus. Serves the Bayside parking lot.",
  },
  {
    id: "stop-mt-vernon-in",
    name: "Mt Vernon St @ South Point Dr (Inbound)",
    coords: [42.31722, -71.04032],
    type: "shuttle",
    routeStopId: 110,
    routes: ["UMass Shuttle"],
    schedule: "Mon–Fri 5:30 AM – 1:30 AM · Sat–Sun 7:30 AM – 1:30 AM",
    notes: "Inbound stop on Mt. Vernon St entering campus near South Point Drive.",
  },
  {
    id: "stop-jfk-library",
    name: "JFK Library / Commonwealth Museum",
    coords: [42.31515, -71.03544],
    type: "shuttle",
    routeStopId: 108,
    routes: ["UMass Shuttle"],
    schedule: "Mon–Fri 5:30 AM – 1:30 AM · Sat–Sun 7:30 AM – 1:30 AM",
    notes: "Stop at the JFK Presidential Library on the eastern edge of campus.",
  },
  {
    id: "stop-campus-center",
    name: "Campus Center",
    coords: [42.31276, -71.03651],
    type: "shuttle",
    routeStopId: 105,
    routes: ["UMass Shuttle"],
    schedule: "Mon–Fri 5:30 AM – 1:30 AM · Sat–Sun 7:30 AM – 1:30 AM",
    notes: "Main campus hub stop. Central point for all campus connections.",
  },
  {
    id: "stop-univ-drive-west",
    name: "University Drive West (Outbound)",
    coords: [42.31474, -71.04113],
    type: "shuttle",
    routeStopId: 112,
    routes: ["UMass Shuttle"],
    schedule: "Mon–Fri 5:30 AM – 1:30 AM · Sat–Sun 7:30 AM – 1:30 AM",
    notes: "Outbound stop on University Drive West heading toward Bayside.",
  },
  {
    id: "stop-mt-vernon-out",
    name: "Mt Vernon St opp South Point Dr (Outbound)",
    coords: [42.31707, -71.04022],
    type: "shuttle",
    routeStopId: 111,
    routes: ["UMass Shuttle"],
    schedule: "Mon–Fri 5:30 AM – 1:30 AM · Sat–Sun 7:30 AM – 1:30 AM",
    notes: "Outbound stop on Mt. Vernon St heading back toward Bayside.",
  },
  {
    id: "stop-bayside-out",
    name: "Bayside Outbound",
    coords: [42.31913, -71.04615],
    type: "shuttle",
    routeStopId: 107,
    routes: ["UMass Shuttle"],
    schedule: "Mon–Fri 5:30 AM – 1:30 AM · Sat–Sun 7:30 AM – 1:30 AM",
    notes: "Final outbound stop before reaching JFK/UMass Station.",
  },
];

const BUILDINGS = [
  { id: "campus-center",   name: "Campus Center",                      coords: [42.31289, -71.03702], desc: "Main student hub with dining, student services, and the bookstore." },
  { id: "quinn-admin",     name: "Quinn Administration Building",       coords: [42.31426, -71.03989], desc: "University administration and administrative offices." },
  { id: "wheatley",        name: "Wheatley Hall",                       coords: [42.31204, -71.03822], desc: "College of Education & Human Development; College of Management." },
  { id: "mccormack",       name: "McCormack Hall",                      coords: [42.31267, -71.03930], desc: "College for Public and Community Service; McCormack Graduate School." },
  { id: "isc",             name: "Integrated Sciences Complex",         coords: [42.31390, -71.04087], desc: "State-of-the-art science research and teaching facility." },
  { id: "university-hall", name: "University Hall",                     coords: [42.31339, -71.03525], desc: "College of Liberal Arts; School for the Environment." },
  { id: "clark-athletic",  name: "Clark Athletic Center",               coords: [42.31507, -71.03947], desc: "Athletics, gym, pool, fitness center, and recreation facilities." },
  { id: "healey-library",  name: "Healey Library",                      coords: [42.31348, -71.03974], desc: "Main campus library with extensive research resources." },
  { id: "emk-institute",   name: "Edward M. Kennedy Institute",         coords: [42.31525, -71.03590], desc: "Institute for the United States Senate dedicated to civic education and engagement." },
  { id: "jfk-library",     name: "JFK Presidential Library & Museum",   coords: [42.31618, -71.03401], desc: "Presidential library and museum dedicated to President John F. Kennedy." },
  { id: "mass-archives",   name: "Massachusetts Archives",               coords: [42.31397, -71.03481], desc: "Commonwealth of Massachusetts Archives — official repository for state government records." },
  { id: "west-residence",  name: "West Residence Hall",                 coords: [42.31636, -71.03964], desc: "On-campus student residential hall." },
  { id: "east-residence",  name: "East Residence Hall",                 coords: [42.31622, -71.03873], desc: "On-campus student residential hall." },
  { id: "service-supply",  name: "Service & Supply Building",           coords: [42.31454, -71.04022], desc: "Facilities and operations services building." },
  { id: "bio-greenhouse",  name: "Biology Department Greenhouse",       coords: [42.31277, -71.04035], desc: "Research greenhouse for the Biology Department." },
];

const DROPOFF_POINTS = [
  {
    id: "dropoff-main",
    name: "UMass Boston Drop-Off / Rideshare",
    coords: [42.31347, -71.03698],
    notes: "Designated drop-off zone for Uber, Lyft, and general passenger drop-off.",
  },
];

// Transfer specs reused by Orange and Green line stations
const _OrangeToDTC = { stopId: "place-dwnxg", name: "Downtown Crossing", coords: [42.3553, -71.0598], line: "Red", lineColor: "#da291c", dir: 0 };
const _GreenToPark = { stopId: "place-pktrm", name: "Park Street",        coords: [42.3563, -71.0628], line: "Red", lineColor: "#da291c", dir: 0 };

// MBTA_STATIONS covers Red, Orange, and Green lines.
// dir: direction_id on that line to reach JFK (Red) or the transfer station (Orange/Green).
//   Red Line — 0=outbound toward Braintree, 1=inbound toward Alewife, null=already at JFK
//   Orange   — 0=toward Forest Hills (passes Downtown Crossing going south), 1=toward Oak Grove
//   Green    — 0=outbound toward branches (passes Park Street going west), 1=inbound toward Lechmere
const MBTA_STATIONS = [
  // ── Red Line ──────────────────────────────────────────────────────────────
  { name: "Alewife",           coords: [42.3952, -71.1428], stopId: "place-alfcl", line: "Red", lineColor: "#da291c", route: "Red", dir: 0 },
  { name: "Davis",             coords: [42.3967, -71.1225], stopId: "place-davis", line: "Red", lineColor: "#da291c", route: "Red", dir: 0 },
  { name: "Porter",            coords: [42.3884, -71.1190], stopId: "place-portr", line: "Red", lineColor: "#da291c", route: "Red", dir: 0 },
  { name: "Harvard",           coords: [42.3736, -71.1190], stopId: "place-harsq", line: "Red", lineColor: "#da291c", route: "Red", dir: 0 },
  { name: "Central",           coords: [42.3654, -71.1036], stopId: "place-cntsq", line: "Red", lineColor: "#da291c", route: "Red", dir: 0 },
  { name: "Kendall/MIT",       coords: [42.3625, -71.0861], stopId: "place-knncl", line: "Red", lineColor: "#da291c", route: "Red", dir: 0 },
  { name: "Charles/MGH",       coords: [42.3610, -71.0706], stopId: "place-chmnl", line: "Red", lineColor: "#da291c", route: "Red", dir: 0 },
  { name: "Park Street",       coords: [42.3563, -71.0628], stopId: "place-pktrm", line: "Red", lineColor: "#da291c", route: "Red", dir: 0 },
  { name: "Downtown Crossing", coords: [42.3553, -71.0598], stopId: "place-dwnxg", line: "Red", lineColor: "#da291c", route: "Red", dir: 0 },
  { name: "South Station",     coords: [42.3524, -71.0552], stopId: "place-sstat", line: "Red", lineColor: "#da291c", route: "Red", dir: 0 },
  { name: "Broadway",          coords: [42.3426, -71.0572], stopId: "place-brdwy", line: "Red", lineColor: "#da291c", route: "Red", dir: 0 },
  { name: "Andrew",            coords: [42.3302, -71.0576], stopId: "place-andrw", line: "Red", lineColor: "#da291c", route: "Red", dir: 0 },
  { name: "JFK/UMass",         coords: [42.3204, -71.0518], stopId: "place-jfk",   line: "Red", lineColor: "#da291c", route: "Red", dir: null },
  { name: "Savin Hill",        coords: [42.3107, -71.0534], stopId: "place-shmnl", line: "Red", lineColor: "#da291c", route: "Red", dir: 1 },
  { name: "Fields Corner",     coords: [42.3004, -71.0619], stopId: "place-fldcr", line: "Red", lineColor: "#da291c", route: "Red", dir: 1 },
  { name: "Shawmut",           coords: [42.2933, -71.0657], stopId: "place-smmnl", line: "Red", lineColor: "#da291c", route: "Red", dir: 1 },
  { name: "Ashmont",           coords: [42.2843, -71.0644], stopId: "place-asmnl", line: "Red", lineColor: "#da291c", route: "Red", dir: 1 },
  { name: "North Quincy",      coords: [42.2757, -71.0050], stopId: "place-nqncy", line: "Red", lineColor: "#da291c", route: "Red", dir: 1 },
  { name: "Wollaston",         coords: [42.2666, -71.0203], stopId: "place-wlsta", line: "Red", lineColor: "#da291c", route: "Red", dir: 1 },
  { name: "Quincy Center",     coords: [42.2519, -71.0051], stopId: "place-qnctr", line: "Red", lineColor: "#da291c", route: "Red", dir: 1 },
  { name: "Quincy Adams",      coords: [42.2332, -71.0073], stopId: "place-qamnl", line: "Red", lineColor: "#da291c", route: "Red", dir: 1 },
  { name: "Braintree",         coords: [42.2079, -71.0015], stopId: "place-brntn", line: "Red", lineColor: "#da291c", route: "Red", dir: 1 },

  // ── Orange Line — transfer at Downtown Crossing to Red ────────────────────
  // dir=0 → toward Forest Hills (passes DTC southbound); dir=1 → toward Oak Grove (passes DTC northbound)
  { name: "Oak Grove",          coords: [42.4362, -71.0709], stopId: "place-ogmnl", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 0, transfer: _OrangeToDTC },
  { name: "Malden Center",      coords: [42.4267, -71.0662], stopId: "place-mlmnl", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 0, transfer: _OrangeToDTC },
  { name: "Wellington",         coords: [42.4020, -71.0773], stopId: "place-welln", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 0, transfer: _OrangeToDTC },
  { name: "Sullivan Square",    coords: [42.3838, -71.0764], stopId: "place-sull",  line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 0, transfer: _OrangeToDTC },
  { name: "Community College",  coords: [42.3739, -71.0706], stopId: "place-ccmnl", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 0, transfer: _OrangeToDTC },
  { name: "North Station",      coords: [42.3655, -71.0606], stopId: "place-north", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 0, transfer: _OrangeToDTC },
  { name: "Haymarket",          coords: [42.3634, -71.0574], stopId: "place-haecl", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 0, transfer: _OrangeToDTC },
  { name: "State",              coords: [42.3590, -71.0578], stopId: "place-state", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 0, transfer: _OrangeToDTC },
  { name: "Chinatown",          coords: [42.3523, -71.0624], stopId: "place-chncl", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 1, transfer: _OrangeToDTC },
  { name: "Tufts Medical",      coords: [42.3493, -71.0642], stopId: "place-tumnl", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 1, transfer: _OrangeToDTC },
  { name: "Back Bay",           coords: [42.3470, -71.0753], stopId: "place-bbsta", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 1, transfer: _OrangeToDTC },
  { name: "Mass Ave",           coords: [42.3411, -71.0837], stopId: "place-masta", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 1, transfer: _OrangeToDTC },
  { name: "Ruggles",            coords: [42.3362, -71.0993], stopId: "place-rugg",  line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 1, transfer: _OrangeToDTC },
  { name: "Roxbury Crossing",   coords: [42.3311, -71.1001], stopId: "place-rcmnl", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 1, transfer: _OrangeToDTC },
  { name: "Jackson Square",     coords: [42.3228, -71.1010], stopId: "place-jaksn", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 1, transfer: _OrangeToDTC },
  { name: "Stony Brook",        coords: [42.3170, -71.1052], stopId: "place-sbmnl", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 1, transfer: _OrangeToDTC },
  { name: "Green Street",       coords: [42.3110, -71.1089], stopId: "place-grmnl", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 1, transfer: _OrangeToDTC },
  { name: "Forest Hills",       coords: [42.3014, -71.1139], stopId: "place-forhl", line: "Orange", lineColor: "#ed8b00", route: "Orange", dir: 1, transfer: _OrangeToDTC },

  // ── Green Line — transfer at Park Street to Red ───────────────────────────
  // dir=1 → inbound toward Lechmere (passes Park Street going east); dir=0 → outbound toward branches
  { name: "Lechmere",           coords: [42.3701, -71.0741], stopId: "place-lech",  line: "Green", lineColor: "#00843d", route: "Green-B,Green-C,Green-D,Green-E", dir: 0, transfer: _GreenToPark },
  { name: "Science Park",       coords: [42.3669, -71.0676], stopId: "place-spmnl", line: "Green", lineColor: "#00843d", route: "Green-B,Green-C,Green-D,Green-E", dir: 0, transfer: _GreenToPark },
  { name: "Government Center",  coords: [42.3592, -71.0592], stopId: "place-gover", line: "Green", lineColor: "#00843d", route: "Green-B,Green-C,Green-D,Green-E", dir: 0, transfer: _GreenToPark },
  { name: "Boylston",           coords: [42.3549, -71.0645], stopId: "place-boyls", line: "Green", lineColor: "#00843d", route: "Green-B,Green-C,Green-D,Green-E", dir: 1, transfer: _GreenToPark },
  { name: "Arlington",          coords: [42.3510, -71.0707], stopId: "place-armnl", line: "Green", lineColor: "#00843d", route: "Green-B,Green-C,Green-D,Green-E", dir: 1, transfer: _GreenToPark },
  { name: "Copley",             coords: [42.3498, -71.0771], stopId: "place-coecl", line: "Green", lineColor: "#00843d", route: "Green-B,Green-C,Green-D,Green-E", dir: 1, transfer: _GreenToPark },
  { name: "Hynes Conv. Center", coords: [42.3473, -71.0817], stopId: "place-hymnl", line: "Green", lineColor: "#00843d", route: "Green-B,Green-C,Green-D,Green-E", dir: 1, transfer: _GreenToPark },
  { name: "Kenmore",            coords: [42.3484, -71.0966], stopId: "place-kencl", line: "Green", lineColor: "#00843d", route: "Green-B,Green-C,Green-D,Green-E", dir: 1, transfer: _GreenToPark },
  // B branch
  { name: "BU East",            coords: [42.3499, -71.1048], stopId: "place-buest", line: "Green", lineColor: "#00843d", route: "Green-B", dir: 1, transfer: _GreenToPark },
  { name: "BU Central",         coords: [42.3499, -71.1137], stopId: "place-bucen", line: "Green", lineColor: "#00843d", route: "Green-B", dir: 1, transfer: _GreenToPark },
  { name: "BU West",            coords: [42.3499, -71.1215], stopId: "place-buwst", line: "Green", lineColor: "#00843d", route: "Green-B", dir: 1, transfer: _GreenToPark },
  { name: "Boston College",     coords: [42.3395, -71.1669], stopId: "place-lake",  line: "Green", lineColor: "#00843d", route: "Green-B", dir: 1, transfer: _GreenToPark },
  // C branch
  { name: "Coolidge Corner",    coords: [42.3422, -71.1212], stopId: "place-cool",  line: "Green", lineColor: "#00843d", route: "Green-C", dir: 1, transfer: _GreenToPark },
  { name: "Cleveland Circle",   coords: [42.3367, -71.1501], stopId: "place-clmnl", line: "Green", lineColor: "#00843d", route: "Green-C", dir: 1, transfer: _GreenToPark },
  // D branch
  { name: "Brookline Village",  coords: [42.3309, -71.1166], stopId: "place-bvmnl", line: "Green", lineColor: "#00843d", route: "Green-D", dir: 1, transfer: _GreenToPark },
  { name: "Riverside",          coords: [42.3366, -71.2562], stopId: "place-river", line: "Green", lineColor: "#00843d", route: "Green-D", dir: 1, transfer: _GreenToPark },
  // E branch
  { name: "Northeastern",       coords: [42.3377, -71.0904], stopId: "place-nuniv", line: "Green", lineColor: "#00843d", route: "Green-E", dir: 1, transfer: _GreenToPark },
  { name: "Museum of Fine Arts", coords: [42.3355, -71.0994], stopId: "place-mfa",  line: "Green", lineColor: "#00843d", route: "Green-E", dir: 1, transfer: _GreenToPark },
  { name: "Longwood Medical",   coords: [42.3347, -71.1047], stopId: "place-lngmd", line: "Green", lineColor: "#00843d", route: "Green-E", dir: 1, transfer: _GreenToPark },
  { name: "Heath Street",       coords: [42.3174, -71.1098], stopId: "place-hsmnl", line: "Green", lineColor: "#00843d", route: "Green-E", dir: 1, transfer: _GreenToPark },
];

// ── Icon factories ────────────────────────────────────────────────────────────

function makeIcon(label, colorClass) {
  return L.divIcon({
    className: "",
    html: `<div class="map-pin ${colorClass}">${label}</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -20],
  });
}

const icons = {
  garage:   makeIcon("P", "pin-garage"),
  lot:      makeIcon("P", "pin-lot"),
  shuttle:  makeIcon("S", "pin-shuttle"),
  mbta:     makeIcon("T", "pin-mbta"),
  building: makeIcon("B", "pin-building"),
  dropoff:  makeIcon("D", "pin-dropoff"),
};

// ── Detail panel ──────────────────────────────────────────────────────────────

function rateTable(rows) {
  if (!rows || rows.length === 0) return "";
  const trs = rows.map(([k, v]) => `<tr><td>${k}</td><td class="rate-val">${v}</td></tr>`).join("");
  return `<table class="rate-table">${trs}</table>`;
}

function showParking(lot) {
  _dirDestCoords = lot.driveCoords || lot.coords;
  _dirDestName = lot.name;
  _lastPanelFn = () => showParking(lot);
  const imgHtml = `<div class="lot-img-placeholder"><span>P</span>${lot.name}</div>`;
  let html = `
    <div class="panel-badge badge-parking">${lot.type === "garage" ? "Garage" : "Surface Lot"}</div>
    <h2>${lot.name}</h2>
    ${imgHtml}
    <p class="panel-desc">${lot.description}</p>
    <h3>Daily Rates</h3>
    ${rateTable(lot.dailyRates)}`;
  if (lot.permitRates) {
    html += `<h3>Permit Rates</h3>${rateTable(lot.permitRates)}`;
  }
  html += `<div class="payment-info">${lot.payment}</div>`;
  html += `<button class="directions-btn" onclick="startDirections()">Get Directions</button>`;
  openPanel(html);
}

function parseTransLocDate(raw) {
  const m = String(raw).match(/\d+/);
  return m ? new Date(parseInt(m[0])) : null;
}

function formatArrival(seconds) {
  if (seconds <= 60) return '<span class="arrival-now">Arriving</span>';
  const mins = Math.round(seconds / 60);
  return `<span class="arrival-min">${mins} min</span>`;
}

async function fetchMbtaPredictions(route, direction, headsignFilter) {
  try {
    let url = `${window.API_BASE || ""}/api/mbta/predictions?stop=place-jfk&route=${route}`;
    if (direction !== undefined && direction !== null) url += `&direction=${direction}`;
    const res = await fetch(url);
    const data = await res.json();
    if (!data.data || data.data.length === 0) return [];

    const tripMap = {};
    for (const item of (data.included || [])) {
      if (item.type === "trip") tripMap[item.id] = item.attributes.headsign || "";
    }

    const now = Date.now();
    let preds = data.data
      .map(pred => {
        const t = pred.attributes.departure_time || pred.attributes.arrival_time;
        if (!t) return null;
        const dt = new Date(t);
        const secs = Math.round((dt - now) / 1000);
        const tripId = pred.relationships?.trip?.data?.id;
        return { secs, headsign: tripMap[tripId] || "", dt, dir: pred.attributes.direction_id };
      })
      .filter(p => p && p.secs > -60)
      .sort((a, b) => a.secs - b.secs);

    if (headsignFilter) {
      preds = preds.filter(p =>
        p.headsign.toLowerCase().includes(headsignFilter.toLowerCase()));
    }
    return preds.slice(0, 4);
  } catch {
    return null;
  }
}

function renderMbtaArrivals(preds) {
  if (!preds) return '<span class="arrival-none">Unable to load</span>';
  if (preds.length === 0) return '<span class="arrival-none">No departures scheduled</span>';
  return preds.map(p => {
    const timeStr = p.dt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    return `<div class="arrival-row">
      ${formatArrival(p.secs)}
      ${p.headsign ? `<span class="arrival-headsign">${p.headsign}</span>` : ""}
      <span class="arrival-time">${timeStr}</span>
    </div>`;
  }).join("");
}

async function fetchArrivals(routeStopId) {
  try {
    const res = await fetch(`${window.API_BASE || ""}/api/transit/arrivals?stop_id=${routeStopId}`);
    const data = await res.json();
    if (!Array.isArray(data) || data.length === 0) return [];
    const arrivals = [];
    for (const stop of data) {
      if (!stop.Times) continue;
      for (const t of stop.Times) {
        const secs = t.Seconds != null ? t.Seconds : null;
        const est = t.EstimateTime ? parseTransLocDate(t.EstimateTime) : null;
        if (secs !== null) arrivals.push({ seconds: secs, time: est });
      }
    }
    arrivals.sort((a, b) => a.seconds - b.seconds);
    return arrivals.slice(0, 4);
  } catch {
    return null;
  }
}

function showStop(stop) {
  _dirDestCoords = stop.coords;
  _dirDestName = stop.name;
  _lastPanelFn = () => showStop(stop);
  const isMbta = stop.type === "mbta";
  const badge = isMbta ? "badge-mbta" : "badge-shuttle";
  const label = isMbta ? "MBTA Station" : "Shuttle Stop";
  const routes = stop.routes.map(r => `<span class="route-chip">${r}</span>`).join(" ");

  let html = `
    <div class="panel-badge ${badge}">${label}</div>
    <h2>${stop.name}</h2>
    <div class="route-chips">${routes}</div>`;

  if (isMbta) {
    html += `
    <h3>Red Line — Inbound to Alewife</h3>
    <div id="mbtaInbound" class="arrivals-list"><span class="arrival-loading">Loading…</span></div>
    <h3>Red Line — Outbound to Braintree</h3>
    <div id="mbtaBraintree" class="arrivals-list"><span class="arrival-loading">Loading…</span></div>
    <h3>Red Line — Outbound to Ashmont</h3>
    <div id="mbtaAshmont" class="arrivals-list"><span class="arrival-loading">Loading…</span></div>
    <h3>UMass Shuttle</h3>
    <div id="arrivalsList" class="arrivals-list"><span class="arrival-loading">Loading…</span></div>`;
  } else {
    html += `
    <h3>Next Arrivals</h3>
    <div id="arrivalsList" class="arrivals-list"><span class="arrival-loading">Loading…</span></div>`;
  }

  if (isMbta) {
    html += `
    <h3>Commuter Rail (Purple)</h3>
    <p class="panel-desc">Take the Red Line <strong>1 stop inbound</strong> to South Station for the Greenbush, Kingston, and Middleborough/Lakeville lines. See <a href="/transit" style="color:var(--navy)">Buses &amp; Train</a> for live departures.</p>`;
  }

  html += `
    <h3>Operating Hours</h3>
    <p class="panel-desc">${stop.schedule}</p>
    <h3>Notes</h3>
    <p class="panel-desc">${stop.notes}</p>
    <button class="directions-btn" onclick="startDirections()">Get Directions</button>`;

  openPanel(html);

  if (isMbta) {
    fetchMbtaPredictions("Red", 1).then(preds => {
      const el = document.getElementById("mbtaInbound");
      if (el) el.innerHTML = renderMbtaArrivals(preds);
    });
    fetchMbtaPredictions("Red", 0, "Braintree").then(preds => {
      const el = document.getElementById("mbtaBraintree");
      if (el) el.innerHTML = renderMbtaArrivals(preds);
    });
    fetchMbtaPredictions("Red", 0, "Ashmont").then(preds => {
      const el = document.getElementById("mbtaAshmont");
      if (el) el.innerHTML = renderMbtaArrivals(preds);
    });
  }

  if (stop.routeStopId) {
    fetchArrivals(stop.routeStopId).then(arrivals => {
      const el = document.getElementById("arrivalsList");
      if (!el) return;
      if (!arrivals || arrivals.length === 0) {
        el.innerHTML = '<span class="arrival-none">No arrivals scheduled</span>';
        return;
      }
      el.innerHTML = arrivals.map(a => {
        const timeStr = a.time
          ? a.time.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
          : "";
        return `<div class="arrival-row">${formatArrival(a.seconds)}${timeStr ? `<span class="arrival-time">${timeStr}</span>` : ""}</div>`;
      }).join("");
    });
  }
}

function showBuilding(bldg) {
  _dirDestCoords = bldg.coords;
  _dirDestName = bldg.name;
  _lastPanelFn = () => showBuilding(bldg);
  openPanel(`
    <div class="panel-badge badge-building">Building</div>
    <h2>${bldg.name}</h2>
    <p class="panel-desc">${bldg.desc}</p>
    <button class="directions-btn" onclick="startDirections()">Get Directions</button>`);
}

function openPanel(html) {
  document.getElementById("panelBody").innerHTML = html;
  document.getElementById("detailPanel").classList.add("open");
}

function closePanel() {
  document.getElementById("detailPanel").classList.remove("open");
  clearRoute();
}

// ── Directions helpers ────────────────────────────────────────────────────────

function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const φ1 = lat1 * Math.PI / 180, φ2 = lat2 * Math.PI / 180;
  const Δφ = (lat2 - lat1) * Math.PI / 180;
  const Δλ = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(Δφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Shuttle loop order (inbound → campus → outbound)
const SHUTTLE_ROUTE_ORDER = [
  "stop-jfk",
  "stop-bayside-in",
  "stop-mt-vernon-in",
  "stop-jfk-library",
  "stop-campus-center",
  "stop-univ-drive-west",
  "stop-mt-vernon-out",
  "stop-bayside-out",
];

async function shuttleRouteGeometry(fromId, toId) {
  const n = SHUTTLE_ROUTE_ORDER.length;
  const fromIdx = SHUTTLE_ROUTE_ORDER.indexOf(fromId);
  const toIdx   = SHUTTLE_ROUTE_ORDER.indexOf(toId);
  if (fromIdx === -1 || toIdx === -1) return null;
  const byId = Object.fromEntries(SHUTTLE_STOPS.map(s => [s.id, s]));

  // Collect stops in loop order from fromId to toId
  const stops = [];
  let i = fromIdx;
  while (true) {
    stops.push(byId[SHUTTLE_ROUTE_ORDER[i]]);
    if (i === toIdx) break;
    i = (i + 1) % n;
    if (i === fromIdx) break;
  }
  if (stops.length < 2) return null;

  // OSRM driving route between each consecutive stop pair (all in parallel)
  const legs = await Promise.all(
    stops.slice(0, -1).map((s, idx) => osrmRoute("car", s.coords, stops[idx + 1].coords))
  );

  // Concatenate all geometry coordinates
  const allCoords = [];
  for (const leg of legs) allCoords.push(...leg.geometry);
  return allCoords;
}

function nearestParkingLot(lat, lng) {
  let best = null, bestDist = Infinity;
  for (const lot of PARKING_LOTS) {
    const d = haversine(lat, lng, lot.coords[0], lot.coords[1]);
    if (d < bestDist) { bestDist = d; best = lot; }
  }
  return { lot: best, dist: bestDist };
}

function nearestShuttleStop(lat, lng) {
  let best = null, bestDist = Infinity;
  for (const s of SHUTTLE_STOPS) {
    const d = haversine(lat, lng, s.coords[0], s.coords[1]);
    if (d < bestDist) { bestDist = d; best = s; }
  }
  return { stop: best, dist: bestDist };
}

function nearestMbtaStation(lat, lng) {
  let best = null, bestDist = Infinity;
  for (const s of MBTA_STATIONS) {
    const d = haversine(lat, lng, s.coords[0], s.coords[1]);
    if (d < bestDist) { bestDist = d; best = s; }
  }
  return { station: best, dist: bestDist };
}

function isNearCampus(coords) {
  return haversine(coords[0], coords[1], 42.3135, -71.0384) < 1000;
}

async function fetchMbtaAt(stopId, route, direction) {
  try {
    let url = `${window.API_BASE || ""}/api/mbta/predictions?stop=${stopId}&route=${route}`;
    if (direction !== undefined && direction !== null) url += `&direction=${direction}`;
    const res = await fetch(url);
    const data = await res.json();
    if (!data.data || data.data.length === 0) return [];
    const tripMap = {};
    for (const item of (data.included || [])) {
      if (item.type === "trip") tripMap[item.id] = item.attributes.headsign || "";
    }
    const now = Date.now();
    return data.data
      .map(pred => {
        const t = pred.attributes.departure_time || pred.attributes.arrival_time;
        if (!t) return null;
        const dt = new Date(t);
        const secs = Math.round((dt - now) / 1000);
        const tripId = pred.relationships?.trip?.data?.id;
        return { secs, headsign: tripMap[tripId] || "", dt };
      })
      .filter(p => p && p.secs > -60)
      .sort((a, b) => a.secs - b.secs)
      .slice(0, 3);
  } catch {
    return null;
  }
}

async function withRetry(fn, retries = 2, delayMs = 800) {
  for (let i = 0; i <= retries; i++) {
    try { return await fn(); }
    catch (e) {
      if (i === retries) throw e;
      await new Promise(r => setTimeout(r, delayMs));
    }
  }
}

async function osrmRoute(profile, from, to) {
  const url = `https://router.project-osrm.org/route/v1/${profile}/${from[1]},${from[0]};${to[1]},${to[0]}?overview=full&geometries=geojson&steps=true`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`OSRM ${res.status}`);
  const data = await res.json();
  if (data.code !== "Ok" || !data.routes?.length) throw new Error("No route found");
  const r = data.routes[0];
  return { distance: r.distance, duration: r.duration, geometry: r.geometry.coordinates, steps: r.legs[0].steps };
}

function fmtDist(m) {
  return m < 900 ? `${Math.round(m / 10) * 10} m` : `${(m / 1000).toFixed(1)} km`;
}

function fmtTime(s) {
  const mins = Math.round(s / 60);
  if (mins < 1) return "< 1 min";
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60), rem = mins % 60;
  return rem ? `${h} hr ${rem} min` : `${h} hr`;
}

// Valhalla polyline6 decoder → [[lng, lat], ...]
function decodePolyline6(str) {
  const coords = [];
  let index = 0, lat = 0, lng = 0;
  while (index < str.length) {
    let b, shift = 0, result = 0;
    do { b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
    lat += result & 1 ? ~(result >> 1) : result >> 1;
    shift = 0; result = 0;
    do { b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
    lng += result & 1 ? ~(result >> 1) : result >> 1;
    coords.push([lng / 1e6, lat / 1e6]);
  }
  return coords;
}

async function valhallaWalkRoute(from, to) {
  const res = await fetch("/api/walk-route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      locations: [
        { lat: from[0], lon: from[1] },
        { lat: to[0],   lon: to[1]   },
      ],
      costing: "pedestrian",
      costing_options: {
        pedestrian: {
          shortest: true,
          walkway_factor: 0.1,
          use_tracks: 1.0,
          service_penalty: 0,
          alley_factor: 1.0,
          driveway_factor: 1.0,
        },
      },
      directions_options: { units: "kilometers" },
    }),
  });
  if (!res.ok) throw new Error(`walk-route ${res.status}`);
  const data = await res.json();
  if (!data.trip) throw new Error("No route found");
  const leg = data.trip.legs[0];
  const summary = data.trip.summary;
  return {
    distance: summary.length * 1000,
    duration: summary.time,
    geometry: decodePolyline6(leg.shape),
    steps: leg.maneuvers.map(m => ({
      distance: (m.length || 0) * 1000,
      _instruction: m.instruction,
      maneuver: { type: m.type, modifier: "" },
      name: m.street_names?.[0] || "",
    })),
  };
}

function stepArrow(type, modifier) {
  // Valhalla numeric types
  if (type === 1 || type === 2 || type === 3) return "▶";  // start
  if (type === 4 || type === 5 || type === 6) return "■";  // destination
  if (type === 10 || type === 11) return "↱";              // right / sharp right
  if (type === 14 || type === 15) return "↰";              // left / sharp left
  if (type === 9 || type === 16) return "→";               // slight right / slight left
  // OSRM string types
  if (type === "depart") return "▶";
  if (type === "arrive") return "■";
  if (!modifier) return "→";
  if (modifier.includes("left")) return "↰";
  if (modifier.includes("right")) return "↱";
  return "→";
}

function buildStepsHtml(steps) {
  return steps
    .filter(s => s.distance > 0 || s.maneuver.type === "arrive" || s.maneuver.type === 4)
    .map(s => {
      const arrow = stepArrow(s.maneuver.type, s.maneuver.modifier);
      const street = s._instruction
        || s.name
        || (s.maneuver.type === "arrive" || s.maneuver.type === 4 ? "Arrive at destination" : "Continue");
      const distHtml = s.distance > 0 ? `<span class="step-dist">${fmtDist(s.distance)}</span>` : "";
      return `<div class="dir-step"><span class="step-arrow">${arrow}</span><span class="step-street">${street}</span>${distHtml}</div>`;
    }).join("");
}

function _shortenLabel(displayName) {
  return displayName.split(", ").slice(0, 2).join(", ");
}

function renderDirFromBar() {
  const fromGps = _dirFromCoords === null;
  return `
    <div class="dir-orig-dest" id="dirFromBar">
      <div class="dir-od-row">
        <span class="dir-od-dot dir-od-dot-from"></span>
        <button class="dir-od-pill" onclick="showDirFromInput()" title="Change starting point">
          ${fromGps ? "📍 " : ""}${_dirFromLabel}
        </button>
      </div>
      <div class="dir-od-divider">
        <button class="dir-swap-btn" onclick="swapDirOriginDest()" title="Swap">⇅</button>
      </div>
      <div class="dir-od-row">
        <span class="dir-od-dot dir-od-dot-to"></span>
        <span class="dir-od-dest">${_dirDestName}</span>
      </div>
    </div>`;
}

function showDirFromInput() {
  const bar = document.getElementById("dirFromBar");
  if (!bar) return;
  bar.innerHTML = `
    <div class="dir-od-row">
      <span class="dir-od-dot dir-od-dot-from"></span>
      <div class="dir-autocomplete-wrap">
        <input class="dir-from-text" id="dirFromInput" type="text" placeholder="Search address or place…"
          autocomplete="off" value="${(_dirFromCoords ? _dirFromLabel : "").replace(/"/g, "&quot;")}">
        <div class="dir-dropdown" id="dirDropdown"></div>
      </div>
    </div>
    <div class="dir-from-btns">
      <button class="dir-from-gps-btn" onclick="resetDirFromGPS()">📍 Use my location</button>
    </div>`;
  const inp = document.getElementById("dirFromInput");
  if (!inp) return;
  inp.focus();
  inp.select();
  inp.addEventListener("input", () => {
    clearTimeout(_autoTimer);
    const q = inp.value.trim();
    if (q.length < 2) { _hideDropdown(); return; }
    _autoTimer = setTimeout(() => _fetchAutocomplete(q), 300);
  });
  inp.addEventListener("keydown", e => {
    if (e.key === "Escape") { _hideDropdown(); const b = document.getElementById("dirFromBar"); if (b) b.outerHTML = renderDirFromBar(); }
  });
}

async function _fetchAutocomplete(q) {
  const dd = document.getElementById("dirDropdown");
  if (!dd) return;
  dd.innerHTML = `<div class="dir-dd-item dir-dd-loading">Searching…</div>`;
  dd.style.display = "block";
  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&limit=6&addressdetails=1&viewbox=-71.4,42.2,-70.8,42.5&bounded=0`;
    const res = await fetch(url, { headers: { "Accept-Language": "en" } });
    const data = await res.json();
    if (!data.length) { dd.innerHTML = `<div class="dir-dd-item dir-dd-empty">No results</div>`; return; }
    dd.innerHTML = data.map(r => {
      const parts = r.display_name.split(", ");
      const main = parts.slice(0, 2).join(", ");
      const sub  = parts.slice(2, 5).join(", ");
      const safe = r.display_name.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
      return `<div class="dir-dd-item" onclick="selectDirFrom(${r.lat},${r.lon},'${safe}')">
        <div class="dir-dd-main">${main}</div>
        ${sub ? `<div class="dir-dd-sub">${sub}</div>` : ""}
      </div>`;
    }).join("");
  } catch {
    dd.innerHTML = `<div class="dir-dd-item dir-dd-empty">Search failed</div>`;
  }
}

function selectDirFrom(lat, lon, label) {
  _dirFromCoords = [parseFloat(lat), parseFloat(lon)];
  _dirFromLabel  = _shortenLabel(label);
  renderDirPanel(_dirActiveTab);
}

function _hideDropdown() {
  const dd = document.getElementById("dirDropdown");
  if (dd) dd.style.display = "none";
}

function resetDirFromGPS() {
  _dirFromCoords = null;
  _dirFromLabel  = "My Location";
  renderDirPanel(_dirActiveTab);
}

function swapDirOriginDest() {
  const prevFromCoords = _dirFromCoords ? [..._dirFromCoords] : (lastUserLocation ? [...lastUserLocation] : null);
  const prevFromLabel  = _dirFromLabel;
  if (!prevFromCoords || !_dirDestCoords) return;
  _dirFromCoords = [..._dirDestCoords];
  _dirFromLabel  = _dirDestName;
  _dirDestCoords = prevFromCoords;
  _dirDestName   = prevFromLabel;
  renderDirPanel(_dirActiveTab);
}

function clearRoute() {
  if (routeLayer && _map) { _map.removeLayer(routeLayer); routeLayer = null; }
}

function drawMultiRoute(segments) {
  clearRoute();
  if (!_map) return;
  routeLayer = L.layerGroup().addTo(_map);
  const allLatLngs = [];
  for (const seg of segments) {
    const latlngs = seg.coords.map(([lng, lat]) => [lat, lng]);
    allLatLngs.push(...latlngs);
    const opts = { color: seg.color || "#1d4ed8", weight: seg.weight || 5, opacity: 0.85 };
    if (seg.dashed) opts.dashArray = "8, 6";
    L.polyline(latlngs, opts).addTo(routeLayer);
  }
  const bounds = L.latLngBounds(allLatLngs);
  if (bounds.isValid()) _map.fitBounds(bounds, { padding: [60, 60] });
}

function startDirections() {
  renderDirPanel("walking");
}

function renderDirPanel(activeTab) {
  _dirActiveTab = activeTab;
  const destCoords = _dirDestCoords;
  const destName = _dirDestName;
  const tabDefs = [
    { id: "walking", label: "Walk" },
    { id: "driving", label: "Drive" },
    { id: "transit", label: "Transit" },
  ];
  const tabsHtml = tabDefs.map(t =>
    `<button class="dir-tab${t.id === activeTab ? " active" : ""}" onclick="renderDirPanel('${t.id}')">${t.label}</button>`
  ).join("");

  openPanel(`
    <button class="dir-back-btn" onclick="_backToDestPanel()">← Back</button>
    ${renderDirFromBar()}
    <div class="dir-tabs">${tabsHtml}</div>
    <div id="dirContent" class="dir-content"><div class="dir-loading">Loading…</div></div>`);

  loadDirContent(activeTab, destCoords, destName);
}

async function loadDirContent(tab, destCoords) {
  const el = document.getElementById("dirContent");
  if (!el) return;

  const origin = getDirOrigin();
  if (!origin) {
    el.innerHTML = `<div class="dir-error">Enable your location (blue dot button on the map) or enter a "From" address above to get directions.</div>`;
    return;
  }

  if (tab === "walking") {
    try {
      const route = await withRetry(() => valhallaWalkRoute(origin, destCoords));
      drawMultiRoute([{ coords: route.geometry, color: "#1d4ed8", weight: 5 }]);
      el.innerHTML = `
        <div class="dir-summary">
          <span class="dir-time">${fmtTime(route.duration)}</span>
          <span class="dir-dist">${fmtDist(route.distance)}</span>
        </div>
        <div class="dir-steps">${buildStepsHtml(route.steps)}</div>`;
    } catch (e) {
      el.innerHTML = `<div class="dir-error">Could not load route. <button class="dir-retry-btn" onclick="renderDirPanel('walking')">Try again</button></div>`;
    }
  } else if (tab === "driving") {
    try {
      if (!isNearCampus(destCoords)) {
        // Reverse: driving from campus to off-campus destination
        const driveRoute = await withRetry(() => osrmRoute("car", origin, destCoords));
        drawMultiRoute([{ coords: driveRoute.geometry, color: "#16a34a", weight: 5 }]);
        el.innerHTML = `
          <div class="dir-summary">
            <span class="dir-time">${fmtTime(driveRoute.duration)}</span>
            <span class="dir-dist">${fmtDist(driveRoute.distance)}</span>
          </div>
          <div class="dir-steps">${buildStepsHtml(driveRoute.steps)}</div>`;
      } else {
        const { lot } = nearestParkingLot(destCoords[0], destCoords[1]);
        const lotEntry = lot.driveCoords || lot.coords;
        const [driveRoute, walkRoute] = await Promise.all([
          withRetry(() => osrmRoute("car", origin, lotEntry)),
          withRetry(() => valhallaWalkRoute(lotEntry, destCoords)),
        ]);
        drawMultiRoute([
          { coords: driveRoute.geometry, color: "#16a34a", weight: 5 },
          { coords: walkRoute.geometry, color: "#1d4ed8", weight: 4 },
        ]);
        el.innerHTML = `
          <div class="dir-summary">
            <span class="dir-time">${fmtTime(driveRoute.duration + walkRoute.duration)}</span>
            <span class="dir-dist">${fmtDist(driveRoute.distance + walkRoute.distance)}</span>
          </div>
          <div class="dir-segment-label dir-seg-drive">
            <span>Drive to ${lot.name}</span>
            <span class="dir-seg-meta">${fmtTime(driveRoute.duration)} · ${fmtDist(driveRoute.distance)}</span>
          </div>
          <div class="dir-steps">${buildStepsHtml(driveRoute.steps)}</div>
          <div class="dir-segment-label dir-seg-walk">
            <span>Walk to destination</span>
            <span class="dir-seg-meta">${fmtTime(walkRoute.duration)} · ${fmtDist(walkRoute.distance)}</span>
          </div>
          <div class="dir-steps">${buildStepsHtml(walkRoute.steps)}</div>`;
      }
    } catch (e) {
      el.innerHTML = `<div class="dir-error">Could not load route. <button class="dir-retry-btn" onclick="renderDirPanel('driving')">Try again</button></div>`;
    }
  } else {
    await loadTransitDir(destCoords, el);
  }
}

function _predsHtml(preds) {
  if (!preds || !preds.length) return '<span class="arrival-none">No schedule</span>';
  return preds.slice(0, 2).map(p =>
    `${formatArrival(p.secs)}${p.headsign ? ` <span class="arrival-headsign">${p.headsign}</span>` : ""}`
  ).join(" &nbsp;·&nbsp; ");
}

async function loadTransitDir(destCoords, el) {
  const JFK_COORDS = [42.3204, -71.0518];
  const JFK_TRANSLOC_ID = 104;
  const origin = getDirOrigin();

  try {
    const { station: boardStation } = nearestMbtaStation(origin[0], origin[1]);
    // Use shuttle when: nearest MBTA station is JFK, OR origin is within 1 km of campus centre.
    // Eastern campus buildings (University Hall, JFK Library, etc.) are geometrically closer to
    // Savin Hill station than to JFK — without this second condition they'd be routed via Red Line.
    const onCampus = boardStation.stopId === "place-jfk" || isNearCampus(origin);
    const destOnCampus = isNearCampus(destCoords);

    // ── Shuttle-only (origin on or near campus, dest on campus) ─────────────
    if (onCampus && destOnCampus) {
      const { stop: boardStop }  = nearestShuttleStop(origin[0],      origin[1]);
      const { stop: alightStop } = nearestShuttleStop(destCoords[0],  destCoords[1]);

      // If same stop, just walk
      if (boardStop.id === alightStop.id) {
        try {
          const walkRoute = await withRetry(() => valhallaWalkRoute(origin, destCoords));
          drawMultiRoute([{ coords: walkRoute.geometry, color: "#1d4ed8", weight: 5 }]);
          el.innerHTML = `
            <div class="dir-summary">
              <span class="dir-time">${fmtTime(walkRoute.duration)}</span>
              <span class="dir-dist">${fmtDist(walkRoute.distance)}</span>
            </div>
            <div class="dir-steps">${buildStepsHtml(walkRoute.steps)}</div>`;
        } catch {
          el.innerHTML = `<div class="dir-error">Could not load route. <button class="dir-retry-btn" onclick="renderDirPanel('transit')">Try again</button></div>`;
        }
        return;
      }

      const [walkToBoard, walkToDest] = await Promise.all([
        withRetry(() => valhallaWalkRoute(origin, boardStop.coords)),
        withRetry(() => valhallaWalkRoute(alightStop.coords, destCoords)),
      ]);
      const [shuttleArrivals, shuttleCoords] = await Promise.all([
        fetchArrivals(boardStop.routeStopId).catch(() => null),
        withRetry(() => shuttleRouteGeometry(boardStop.id, alightStop.id), 1).catch(() => null),
      ]);
      const nextShuttle = shuttleArrivals?.length
        ? formatArrival(shuttleArrivals[0].seconds)
        : '<span class="arrival-none">No arrivals scheduled</span>';
      const shuttleSeg = shuttleCoords
        || [[boardStop.coords[1], boardStop.coords[0]], [alightStop.coords[1], alightStop.coords[0]]];
      drawMultiRoute([
        { coords: walkToBoard.geometry, color: "#1d4ed8", weight: 4 },
        { coords: shuttleSeg, color: "#15803d", weight: 4, dashed: true },
        { coords: walkToDest.geometry, color: "#1d4ed8", weight: 4 },
      ]);
      el.innerHTML = `
        <div class="dir-segment-label dir-seg-walk">
          <span>Walk to ${boardStop.name}</span>
          <span class="dir-seg-meta">${fmtTime(walkToBoard.duration)} · ${fmtDist(walkToBoard.distance)}</span>
        </div>
        <div class="dir-steps">${buildStepsHtml(walkToBoard.steps)}</div>
        <div class="dir-segment-label dir-seg-shuttle">
          <span>UMass Shuttle → ${alightStop.name}</span>
          <span class="dir-seg-meta">Next: ${nextShuttle}</span>
        </div>
        <div class="dir-segment-label dir-seg-walk">
          <span>Walk to destination</span>
          <span class="dir-seg-meta">${fmtTime(walkToDest.duration)} · ${fmtDist(walkToDest.distance)}</span>
        </div>
        <div class="dir-steps">${buildStepsHtml(walkToDest.steps)}</div>`;
      return;
    }

    // ── Reverse: origin on campus, dest off-campus ───────────────────────────
    if (onCampus && !destOnCampus) {
      const { stop: boardShuttleStop } = nearestShuttleStop(origin[0], origin[1]);
      const { station: destStation } = nearestMbtaStation(destCoords[0], destCoords[1]);
      const [walkToShuttle, walkFromStation] = await Promise.all([
        withRetry(() => valhallaWalkRoute(origin, boardShuttleStop.coords)),
        withRetry(() => valhallaWalkRoute(destStation.coords, destCoords)),
      ]);
      const [shuttleArrivals, redPreds] = await Promise.all([
        fetchArrivals(boardShuttleStop.routeStopId).catch(() => null),
        (() => {
          // direction of Red Line from JFK to destStation's Red Line stop
          let redStop = destStation.transfer ? destStation.transfer : destStation;
          const dir = redStop.dir === 0 ? 1 : redStop.dir === 1 ? 0 : null;
          return dir === null ? Promise.resolve(null)
            : fetchMbtaAt("place-jfk", "Red", dir).catch(() => null);
        })(),
      ]);
      const nextShuttle = shuttleArrivals?.length
        ? formatArrival(shuttleArrivals[0].seconds)
        : '<span class="arrival-none">No arrivals scheduled</span>';

      const hasTransfer = !!destStation.transfer;
      const xfer = destStation.transfer || { coords: destStation.coords, name: destStation.name };
      // Determine Red Line direction from JFK toward the transfer/destination
      const redDirFromJfk = hasTransfer ? 1
        : destStation.dir === 0 ? 1 : destStation.dir === 1 ? 0 : null;
      const redSegEnd = hasTransfer ? xfer.coords : destStation.coords;

      const segments = [
        { coords: walkToShuttle.geometry, color: "#1d4ed8", weight: 4 },
        { coords: [[JFK_COORDS[1], JFK_COORDS[0]], [boardShuttleStop.coords[1], boardShuttleStop.coords[0]]], color: "#15803d", weight: 4, dashed: true },
      ];
      if (redDirFromJfk !== null) {
        segments.push({ coords: [[JFK_COORDS[1], JFK_COORDS[0]], [redSegEnd[1], redSegEnd[0]]], color: "#da291c", weight: 5, dashed: true });
      }
      if (hasTransfer) {
        segments.push({ coords: [[xfer.coords[1], xfer.coords[0]], [destStation.coords[1], destStation.coords[0]]], color: destStation.lineColor, weight: 4, dashed: true });
      }
      segments.push({ coords: walkFromStation.geometry, color: "#1d4ed8", weight: 4 });
      drawMultiRoute(segments);

      const lineLabel = hasTransfer
        ? `Red Line → ${xfer.name}, transfer to ${destStation.line} Line → ${destStation.name}`
        : `Red Line → ${destStation.name}`;

      el.innerHTML = `
        <div class="dir-segment-label dir-seg-walk">
          <span>Walk to ${boardShuttleStop.name}</span>
          <span class="dir-seg-meta">${fmtTime(walkToShuttle.duration)} · ${fmtDist(walkToShuttle.distance)}</span>
        </div>
        <div class="dir-segment-label dir-seg-shuttle">
          <span>UMass Shuttle → JFK/UMass Station</span>
          <span class="dir-seg-meta">Next: ${nextShuttle}</span>
        </div>
        <div class="dir-segment-label dir-seg-redline">
          <span>${lineLabel}</span>
          <span class="dir-seg-meta">${_predsHtml(redPreds)}</span>
        </div>
        <div class="dir-segment-label dir-seg-walk">
          <span>Walk to destination</span>
          <span class="dir-seg-meta">${fmtTime(walkFromStation.duration)} · ${fmtDist(walkFromStation.distance)}</span>
        </div>
        <div class="dir-steps">${buildStepsHtml(walkFromStation.steps)}</div>`;
      return;
    }

    // ── Off-campus origin → transit to campus ────────────────────────────────
    // Before routing via a subway line, check if an inbound shuttle boarding stop is within 1 km.
    // The shuttle is free and direct — prefer it over paying for the subway when reachable on foot.
    const SHUTTLE_BOARD_IDS = new Set(["stop-jfk", "stop-bayside-in", "stop-mt-vernon-in"]);
    let nearBoardStop = null, nearBoardDist = Infinity;
    for (const s of SHUTTLE_STOPS) {
      if (!SHUTTLE_BOARD_IDS.has(s.id)) continue;
      const d = haversine(origin[0], origin[1], s.coords[0], s.coords[1]);
      if (d < nearBoardDist) { nearBoardDist = d; nearBoardStop = s; }
    }

    const { stop: alightStop } = nearestShuttleStop(destCoords[0], destCoords[1]);

    if (nearBoardStop && nearBoardDist < 1300 && destOnCampus) {
      // Walk to shuttle boarding stop → shuttle → walk to destination (no subway fare needed)
      const [walkToBoard, walkToDest] = await Promise.all([
        withRetry(() => valhallaWalkRoute(origin, nearBoardStop.coords)),
        withRetry(() => valhallaWalkRoute(alightStop.coords, destCoords)),
      ]);
      const [shuttleArrivals, shuttleCoords] = await Promise.all([
        fetchArrivals(nearBoardStop.routeStopId).catch(() => null),
        withRetry(() => shuttleRouteGeometry(nearBoardStop.id, alightStop.id), 1).catch(() => null),
      ]);
      const nextShuttle = shuttleArrivals?.length
        ? formatArrival(shuttleArrivals[0].seconds)
        : '<span class="arrival-none">No arrivals scheduled</span>';
      const shuttleSeg = shuttleCoords
        || [[nearBoardStop.coords[1], nearBoardStop.coords[0]], [alightStop.coords[1], alightStop.coords[0]]];
      drawMultiRoute([
        { coords: walkToBoard.geometry, color: "#1d4ed8", weight: 4 },
        { coords: shuttleSeg, color: "#15803d", weight: 4, dashed: true },
        { coords: walkToDest.geometry, color: "#1d4ed8", weight: 4 },
      ]);
      el.innerHTML = `
        <div class="dir-segment-label dir-seg-walk">
          <span>Walk to ${nearBoardStop.name}</span>
          <span class="dir-seg-meta">${fmtTime(walkToBoard.duration)} · ${fmtDist(walkToBoard.distance)}</span>
        </div>
        <div class="dir-steps">${buildStepsHtml(walkToBoard.steps)}</div>
        <div class="dir-segment-label dir-seg-shuttle">
          <span>UMass Shuttle → ${alightStop.name}</span>
          <span class="dir-seg-meta">Next: ${nextShuttle}</span>
        </div>
        <div class="dir-segment-label dir-seg-walk">
          <span>Walk to destination</span>
          <span class="dir-seg-meta">${fmtTime(walkToDest.duration)} · ${fmtDist(walkToDest.distance)}</span>
        </div>
        <div class="dir-steps">${buildStepsHtml(walkToDest.steps)}</div>`;
      return;
    }

    const [walkToStation, walkToDest] = await Promise.all([
      withRetry(() => valhallaWalkRoute(origin, boardStation.coords)),
      withRetry(() => valhallaWalkRoute(alightStop.coords, destCoords)),
    ]);

    const hasTransfer = !!boardStation.transfer;
    const xfer = boardStation.transfer;

    const [boardPreds, xferPreds, shuttleArrivals, shuttleCoords] = await Promise.all([
      fetchMbtaAt(boardStation.stopId, boardStation.route, boardStation.dir).catch(() => null),
      hasTransfer ? fetchMbtaAt(xfer.stopId, "Red", xfer.dir).catch(() => null) : Promise.resolve(null),
      fetchArrivals(JFK_TRANSLOC_ID).catch(() => null),
      withRetry(() => shuttleRouteGeometry("stop-jfk", alightStop.id), 1).catch(() => null),
    ]);

    const nextShuttle = shuttleArrivals?.length
      ? formatArrival(shuttleArrivals[0].seconds)
      : '<span class="arrival-none">No arrivals scheduled</span>';
    const shuttleSeg = shuttleCoords || [[JFK_COORDS[1], JFK_COORDS[0]], [alightStop.coords[1], alightStop.coords[0]]];

    let segments, html;

    if (!hasTransfer) {
      // Red Line direct
      const redSeg = [[boardStation.coords[1], boardStation.coords[0]], [JFK_COORDS[1], JFK_COORDS[0]]];
      segments = [
        { coords: walkToStation.geometry, color: "#1d4ed8", weight: 4 },
        { coords: redSeg, color: "#da291c", weight: 5, dashed: true },
        { coords: shuttleSeg, color: "#15803d", weight: 4, dashed: true },
        { coords: walkToDest.geometry, color: "#1d4ed8", weight: 4 },
      ];
      html = `
        <div class="dir-segment-label dir-seg-walk">
          <span>Walk to ${boardStation.name}</span>
          <span class="dir-seg-meta">${fmtTime(walkToStation.duration)} · ${fmtDist(walkToStation.distance)}</span>
        </div>
        <div class="dir-steps">${buildStepsHtml(walkToStation.steps)}</div>
        <div class="dir-segment-label dir-seg-redline">
          <span>Red Line → JFK/UMass Station</span>
          <span class="dir-seg-meta">${_predsHtml(boardPreds)}</span>
        </div>`;
    } else {
      // Orange or Green Line → transfer to Red Line at xfer
      const boardSeg = [[boardStation.coords[1], boardStation.coords[0]], [xfer.coords[1], xfer.coords[0]]];
      const redSeg   = [[xfer.coords[1], xfer.coords[0]], [JFK_COORDS[1], JFK_COORDS[0]]];
      const lineLabel = `${boardStation.line} Line → ${xfer.name}`;
      const redLabel  = `Red Line → JFK/UMass Station`;
      segments = [
        { coords: walkToStation.geometry, color: "#1d4ed8", weight: 4 },
        { coords: boardSeg, color: boardStation.lineColor, weight: 5, dashed: true },
        { coords: redSeg,   color: "#da291c", weight: 5, dashed: true },
        { coords: shuttleSeg, color: "#15803d", weight: 4, dashed: true },
        { coords: walkToDest.geometry, color: "#1d4ed8", weight: 4 },
      ];
      html = `
        <div class="dir-segment-label dir-seg-walk">
          <span>Walk to ${boardStation.name}</span>
          <span class="dir-seg-meta">${fmtTime(walkToStation.duration)} · ${fmtDist(walkToStation.distance)}</span>
        </div>
        <div class="dir-steps">${buildStepsHtml(walkToStation.steps)}</div>
        <div class="dir-segment-label" style="background:#fff3cd;color:#7d5a00;">
          <span>${lineLabel}</span>
          <span class="dir-seg-meta">${_predsHtml(boardPreds)}</span>
        </div>
        <div class="dir-segment-label dir-seg-transfer">
          <span>Transfer → Red Line at ${xfer.name}</span>
          <span class="dir-seg-meta">${_predsHtml(xferPreds)}</span>
        </div>
        <div class="dir-segment-label dir-seg-redline">
          <span>${redLabel}</span>
        </div>`;
    }

    drawMultiRoute(segments);
    el.innerHTML = html + `
      <div class="dir-segment-label dir-seg-shuttle">
        <span>UMass Shuttle → ${alightStop.name}</span>
        <span class="dir-seg-meta">Next at JFK: ${nextShuttle}</span>
      </div>
      <div class="dir-segment-label dir-seg-walk">
        <span>Walk to destination</span>
        <span class="dir-seg-meta">${fmtTime(walkToDest.duration)} · ${fmtDist(walkToDest.distance)}</span>
      </div>
      <div class="dir-steps">${buildStepsHtml(walkToDest.steps)}</div>`;

  } catch (e) {
    el.innerHTML = `<div class="dir-error">Could not load transit directions. <button class="dir-retry-btn" onclick="renderDirPanel('transit')">Try again</button></div>`;
  }
}

function _backToDestPanel() {
  clearRoute();
  if (_lastPanelFn) _lastPanelFn();
}

// ── Map init ──────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  const map = L.map("map", { zoomControl: true }).setView([42.3140, -71.0400], 15);
  _map = map;

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  PARKING_LOTS.forEach(lot => {
    L.marker(lot.coords, { icon: icons[lot.type] })
      .addTo(map)
      .on("click", () => showParking(lot));
  });

  SHUTTLE_STOPS.forEach(stop => {
    L.marker(stop.coords, { icon: icons[stop.type] })
      .addTo(map)
      .on("click", () => showStop(stop));
  });

  BUILDINGS.forEach(bldg => {
    L.marker(bldg.coords, { icon: icons.building })
      .addTo(map)
      .on("click", () => showBuilding(bldg));
  });

  DROPOFF_POINTS.forEach(dp => {
    L.marker(dp.coords, { icon: icons.dropoff })
      .addTo(map)
      .on("click", () => {
        _dirDestCoords = dp.coords;
        _dirDestName = dp.name;
        _lastPanelFn = () => {
          _dirDestCoords = dp.coords;
          _dirDestName = dp.name;
          openPanel(`
            <div class="panel-badge badge-dropoff">Drop-Off / Rideshare</div>
            <h2>${dp.name}</h2>
            <p class="panel-desc">${dp.notes}</p>
            <div class="payment-info">Uber &nbsp;·&nbsp; Lyft &nbsp;·&nbsp; Passenger drop-off</div>
            <button class="directions-btn" onclick="startDirections()">Get Directions</button>`);
        };
        _lastPanelFn();
      });
  });

  // Live coordinate display
  const coordDisplay = document.getElementById("coordDisplay");
  map.on("mousemove", (e) => {
    coordDisplay.textContent = `${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}`;
  });
  map.on("click", (e) => {
    coordDisplay.textContent = `[click] ${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}`;
    coordDisplay.style.background = "rgba(0,48,135,0.9)";
    coordDisplay.style.color = "#fff";
    setTimeout(() => {
      coordDisplay.style.background = "";
      coordDisplay.style.color = "";
    }, 3000);
  });

  document.getElementById("closePanel").addEventListener("click", closePanel);

  // ── Live location ─────────────────────────────────────────────
  const locateBtn = document.getElementById("locateBtn");
  let locationMarker = null;
  let locationCircle = null;
  let watchId = null;

  const locationIcon = L.divIcon({
    className: "",
    html: `<div class="user-dot"><div class="user-dot-ring"></div></div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });

  function stopLocation() {
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      watchId = null;
    }
    if (locationMarker) { map.removeLayer(locationMarker); locationMarker = null; }
    if (locationCircle) { map.removeLayer(locationCircle); locationCircle = null; }
    locateBtn.classList.remove("active");
    locateBtn.title = "Show my location";
  }

  locateBtn.addEventListener("click", () => {
    if (watchId !== null) { stopLocation(); return; }

    if (!navigator.geolocation) {
      coordDisplay.textContent = "Geolocation not supported by this browser";
      setTimeout(() => { coordDisplay.textContent = "Move mouse over map"; }, 3000);
      return;
    }

    locateBtn.classList.add("waiting");

    watchId = navigator.geolocation.watchPosition(
      (pos) => {
        locateBtn.classList.remove("waiting");
        locateBtn.classList.add("active");
        locateBtn.title = "Location active — click to stop";

        const latlng = [pos.coords.latitude, pos.coords.longitude];
        lastUserLocation = latlng;
        const accuracy = pos.coords.accuracy;

        if (!locationMarker) {
          locationMarker = L.marker(latlng, { icon: locationIcon, zIndexOffset: 1000 }).addTo(map);
          locationCircle = L.circle(latlng, {
            radius: accuracy,
            color: "#2563eb",
            fillColor: "#2563eb",
            fillOpacity: 0.08,
            weight: 1,
          }).addTo(map);
          map.setView(latlng, Math.max(map.getZoom(), 16));
        } else {
          locationMarker.setLatLng(latlng);
          locationCircle.setLatLng(latlng).setRadius(accuracy);
        }
      },
      (err) => {
        locateBtn.classList.remove("waiting");
        stopLocation();
        const msgs = {
          1: "Location access denied",
          2: "Location unavailable",
          3: "Location request timed out",
        };
        coordDisplay.textContent = msgs[err.code] || "Location error";
        setTimeout(() => { coordDisplay.textContent = "Move mouse over map"; }, 4000);
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 12000 }
    );
  });

  // Hamburger menu
  const hamburgerBtn = document.getElementById("hamburgerBtn");
  const sideMenu = document.getElementById("sideMenu");
  const closeMenu = document.getElementById("closeMenu");

  hamburgerBtn.addEventListener("click", () => sideMenu.classList.toggle("open"));
  closeMenu.addEventListener("click", () => sideMenu.classList.remove("open"));
});
