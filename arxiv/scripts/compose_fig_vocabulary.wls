#!/usr/bin/env wolframscript

(* Publication compositor for the paper's opening figure pair.
   GDSFactory generates every x-y body.  Wolfram applies only typography,
   layout, and a shallow vector relief so sub-micron guides remain legible
   at journal scale without changing their transverse geometry. *)

args = Rest[$ScriptCommandLine];
If[Length[args] < 2,
  Print["usage: wolframscript -file compose_fig_vocabulary.wls DATA.json OUTPUT_DIR"];
  Exit[2];
];

dataPath = ExpandFileName[args[[1]]];
outputDirectory = ExpandFileName[args[[2]]];
If[!DirectoryQ[outputDirectory],
  CreateDirectory[outputDirectory, CreateIntermediateDirectories -> True]
];
data = Import[dataPath, "RawJSON"];

(* White-page publication system: color belongs to geometry, while structure
   is carried by crisp neutral rules and typographic weight. *)
paper = RGBColor[1, 1, 1];
surface = RGBColor[1, 1, 1];
ink = RGBColor[23/255, 25/255, 28/255];
inkSoft = ink;
muted = RGBColor[66/255, 69/255, 73/255];
rule = ink;
ruleStrong = ink;
crimson = RGBColor[163/255, 31/255, 52/255];
crimsonSoft = RGBColor[246/255, 234/255, 237/255];
ochre = RGBColor[139/255, 89/255, 0/255];
ochreSoft = RGBColor[247/255, 238/255, 220/255];
verified = RGBColor[38/255, 124/255, 90/255];
verifiedSoft = RGBColor[234/255, 244/255, 239/255];
diffBlue = RGBColor[49/255, 94/255, 159/255];

displayFont = "Iowan Old Style";
sansFont = "Helvetica Neue";
monoFont = "Menlo";
mathFont = "STIX Two Text";

ClearAll[
  flatPoints, allGroupPolys, rangeOf, specFromRange, specFor, tp, tpoly,
  tpolys, flatPolys, pathStroke, reliefEntries, reliefPolys,
  raisedPolys, reliefGroups, reliefComponent, reliefOrientedComponent,
  reliefCouplingPair, reliefRectangle, portDisks, pointDisks,
  associationPorts, text, displayText, codeText, groupText, panelHeading,
  panelField, arrowLine, horizontalDimension, verticalDimension, callout, pathGraphic,
  subscripted, deltaY, exportFigure
];

flatPoints[polys_List] := Flatten[polys, 1];
allGroupPolys[groups_Association] := Join @@ Values[groups];

rangeOf[polys_List] := Module[{points = flatPoints[polys]},
  {
    {Min[points[[All, 1]]], Max[points[[All, 1]]]},
    {Min[points[[All, 2]]], Max[points[[All, 2]]]}
  }
];

specFromRange[
  source : {{_, _}, {_, _}},
  target : {{_, _}, {_, _}},
  equal_: True
] := Module[
  {sx, sy, scale, sourceCenter, targetCenter},
  sx = (target[[1, 2]] - target[[1, 1]])/
    Max[source[[1, 2]] - source[[1, 1]], 10^-9];
  sy = (target[[2, 2]] - target[[2, 1]])/
    Max[source[[2, 2]] - source[[2, 1]], 10^-9];
  If[TrueQ[equal],
    scale = Min[sx, sy];
    sx = scale;
    sy = scale;
  ];
  sourceCenter = Mean /@ source;
  targetCenter = Mean /@ target;
  <|
    "sx" -> sx, "sy" -> sy,
    "cx" -> sourceCenter[[1]], "cy" -> sourceCenter[[2]],
    "tx" -> targetCenter[[1]], "ty" -> targetCenter[[2]]
  |>
];

specFor[polys_List, target_, equal_: True] :=
  specFromRange[rangeOf[polys], target, equal];

tp[point_List, spec_Association] := {
  spec["tx"] + spec["sx"] (point[[1]] - spec["cx"]),
  spec["ty"] + spec["sy"] (point[[2]] - spec["cy"])
};

tpoly[polygon_List, spec_Association] := tp[#, spec] & /@ polygon;
tpolys[polys_List, spec_Association] := tpoly[#, spec] & /@ polys;

flatPolys[
  polys_List,
  spec_Association,
  fill_,
  edge_: None,
  edgeThickness_: 0.35
] := {
  FaceForm[fill],
  EdgeForm[
    If[edge === None, None, Directive[edge, AbsoluteThickness[edgeThickness]]]
  ],
  Polygon /@ tpolys[polys, spec]
};

pathStroke[
  points_List,
  spec_Association,
  color_: verified,
  thickness_: 0.82
] := {
  color,
  AbsoluteThickness[thickness],
  CapForm["Round"],
  JoinForm["Round"],
  Line[tp[#, spec] & /@ points]
};

(* Each entry is {transformed polygon, top color}.  All lower faces are drawn
   before all top faces so adjacent exact GDS polygons remain visually clean. *)
reliefEntries[
  entries_List,
  depth_: {0.30, -0.42},
  topEdgeThickness_: 0.30
] := Module[
  {baseLayer, sideLayer, topLayer, pairs, baseShade, sideShade, edgeShade},
  baseShade[color_] := Blend[{Black, color}, 0.50];
  sideShade[color_] := Blend[{Black, color}, 0.67];
  edgeShade[color_] := Blend[{Black, color}, 0.72];

  baseLayer = (
      {
        FaceForm[baseShade[#[[2]]]],
        EdgeForm[None],
        Polygon[(# + depth) & /@ #[[1]]]
      }
    ) & /@ entries;

  sideLayer = Table[
    pairs = Partition[Append[entries[[i, 1]], First[entries[[i, 1]]]], 2, 1];
    {
      FaceForm[sideShade[entries[[i, 2]]]],
      EdgeForm[None],
      Table[
        Polygon[
          {
            pairs[[j, 1]],
            pairs[[j, 2]],
            pairs[[j, 2]] + depth,
            pairs[[j, 1]] + depth
          }
        ],
        {j, Length[pairs]}
      ]
    },
    {i, Length[entries]}
  ];

  topLayer = (
      {
        FaceForm[#[[2]]],
        EdgeForm[
          Directive[edgeShade[#[[2]]], AbsoluteThickness[topEdgeThickness]]
        ],
        Polygon[#[[1]]]
      }
    ) & /@ entries;

  {baseLayer, sideLayer, topLayer}
];

reliefPolys[
  polys_List,
  spec_Association,
  color_,
  depth_: {0.30, -0.42},
  topEdgeThickness_: 0.30
] := reliefEntries[
  ({#, color} & /@ tpolys[polys, spec]),
  depth,
  topEdgeThickness
];

(* Hollow Boolean results use a clean raised face.  Omitting individual side
   quads avoids exposing the zero-width bridge used by GDS to encode holes. *)
raisedPolys[
  polys_List,
  spec_Association,
  color_,
  depth_: {0.16, -0.22},
  topEdgeThickness_: 0.26
] := Module[{transformed = tpolys[polys, spec]},
  {
    FaceForm[Blend[{Black, color}, 0.52]],
    EdgeForm[None],
    Polygon /@ (((# + depth) & /@ #) & /@ transformed),
    FaceForm[color],
    EdgeForm[None],
    Polygon /@ transformed
  }
];

reliefGroups[
  groups_Association,
  spec_Association,
  colors_Association,
  depth_: {0.30, -0.42},
  topEdgeThickness_: 0.30
] := Module[{entries},
  entries = Join @@ KeyValueMap[
    Function[{name, polygons},
      ({tpoly[#, spec], colors[name]} & /@ polygons)
    ],
    groups
  ];
  reliefEntries[entries, depth, topEdgeThickness]
];

reliefComponent[
  component_Association,
  box_,
  color_,
  showPorts_: False,
  depth_: {0.30, -0.42},
  portRadius_: 0.12
] := Module[{spec = specFor[component["polygons"], box, True]},
  {
    reliefPolys[component["polygons"], spec, color, depth],
    If[
      TrueQ[showPorts],
      portDisks[component["ports"], spec, portRadius],
      {}
    ]
  }
];

reliefOrientedComponent[
  component_Association,
  box_,
  color_,
  connectionPortName_String,
  depth_: {0.30, -0.42},
  portRadius_: 0.12
] := Module[{spec, connectionCenter},
  spec = specFor[component["polygons"], box, True];
  connectionCenter = FirstCase[
    component["ports"],
    port_ /; port["name"] === connectionPortName :> port["center"]
  ];
  {
    reliefPolys[component["polygons"], spec, color, depth],
    portDisks[component["ports"], spec, portRadius, ink],
    pointDisks[{connectionCenter}, spec, 1.10 portRadius, verified]
  }
];

(* Keep both guides in the same viewing orientation as every other primitive.
   A previous gap-preserving treatment projected the upper guide upward and
   the lower guide downward; that made the pair read as two mismatched solids. *)
reliefCouplingPair[
  polys_List,
  spec_Association,
  color_,
  depth : {_, _},
  topEdgeThickness_: 0.30
] := reliefPolys[polys, spec, color, depth, topEdgeThickness];

reliefRectangle[
  bottomLeft_,
  topRight_,
  color_,
  depth_: {0.20, -0.28}
] := reliefEntries[
  {{
    {
      bottomLeft,
      {topRight[[1]], bottomLeft[[2]]},
      topRight,
      {bottomLeft[[1]], topRight[[2]]}
    },
    color
  }},
  depth,
  0.28
];

portDisks[
  ports_List,
  spec_Association,
  radius_: 0.12,
  edgeColor_: ink
] := Table[
  {
    FaceForm[paper],
    EdgeForm[Directive[edgeColor, AbsoluteThickness[0.46]]],
    Disk[tp[port["center"], spec], radius]
  },
  {port, ports}
];

pointDisks[
  points_List,
  spec_Association,
  radius_: 0.095,
  edgeColor_: verified
] := Table[
  {
    FaceForm[paper],
    EdgeForm[Directive[edgeColor, AbsoluteThickness[0.48]]],
    Disk[tp[point, spec], radius]
  },
  {point, points}
];

associationPorts[ports_Association] :=
  KeyValueMap[<|"name" -> #1, "center" -> #2|> &, ports];

text[
  content_,
  position_,
  size_: 4.8,
  alignment_: Center,
  options___Rule
] := Inset[
  Style[
    content,
    FontFamily -> displayFont,
    FontSize -> size,
    FontColor -> ink,
    options
  ],
  position,
  alignment
];

displayText[
  content_,
  position_,
  size_: 7.1,
  alignment_: {Left, Center},
  options___Rule
] := Inset[
  Style[
    content,
    FontFamily -> displayFont,
    FontSize -> size,
    FontColor -> ink,
    options
  ],
  position,
  alignment
];

codeText[
  content_,
  position_,
  size_: 4.15,
  alignment_: Center,
  options___Rule
] := Inset[
  Style[
    content,
    FontFamily -> displayFont,
    FontSize -> size,
    FontColor -> inkSoft,
    options
  ],
  position,
  alignment
];

groupText[content_, position_, alignment_: {Left, Center}] :=
  text[
    content,
    position,
    6.10,
    alignment,
    FontColor -> ink
  ];

panelHeading[tag_String, title_String, x_, y_] := {
  text[tag, {x, y}, 7.40, {Left, Center}],
  displayText[
    title,
    {x + 3.25, y + 0.02},
    7.40,
    {Left, Center}
  ]
};

panelField[bottomLeft_, topRight_] := {
  FaceForm[surface],
  EdgeForm[Directive[ink, AbsoluteThickness[0.52]]],
  Rectangle[bottomLeft, topRight]
};

arrowLine[start_, finish_, color_: ink] := {
  color,
  AbsoluteThickness[0.68],
  Arrowheads[0.012],
  Arrow[{start, finish}]
};

horizontalDimension[x1_, x2_, y_, label_] := {
  ruleStrong,
  AbsoluteThickness[0.50],
  Line[{{x1, y}, {x2, y}}],
  Line[{{x1, y - 0.20}, {x1, y + 0.20}}],
  Line[{{x2, y - 0.20}, {x2, y + 0.20}}],
  text[label, {(x1 + x2)/2, y + 1.35}, 5.30]
};

verticalDimension[x_, y1_, y2_, label_, side_: -1] := {
  ruleStrong,
  AbsoluteThickness[0.50],
  Line[{{x, y1}, {x, y2}}],
  Line[{{x - 0.20, y1}, {x + 0.20, y1}}],
  Line[{{x - 0.20, y2}, {x + 0.20, y2}}],
  text[
    label,
    {x + side 0.48, (y1 + y2)/2},
    5.30,
    If[side < 0, {Right, Center}, {Left, Center}]
  ]
};

callout[anchor_, elbow_, labelPosition_, label_, side_: {Left, Center}] := {
  ruleStrong,
  AbsoluteThickness[0.50],
  Line[{anchor, elbow, labelPosition + {-0.20, 0}}],
  text[label, labelPosition, 5.30, side]
};

pathGraphic[
  path_Association,
  box_,
  color_: verified,
  thickness_: 0.82
] := Module[{source, spec},
  source = {
    {Min[path["points"][[All, 1]]], Max[path["points"][[All, 1]]]},
    {Min[path["points"][[All, 2]]], Max[path["points"][[All, 2]]]}
  };
  spec = specFromRange[source, box, True];
  pathStroke[path["points"], spec, color, thickness]
];

subscripted[base_String, sub_String] :=
  Subscript[
    Style[base, FontFamily -> mathFont, FontSlant -> Italic],
    Style[sub, FontFamily -> mathFont, FontSlant -> Italic]
  ];

deltaY = Row[{
  Style["\[CapitalDelta]", FontFamily -> mathFont],
  Style["y", FontFamily -> mathFont, FontSlant -> Italic]
}];

exportFigure[graphic_, stem_String, imageWidth_Integer] := Module[
  {pdf, svg, png},
  pdf = FileNameJoin[{outputDirectory, stem <> ".pdf"}];
  svg = FileNameJoin[{outputDirectory, stem <> ".svg"}];
  png = FileNameJoin[{outputDirectory, stem <> ".png"}];
  Export[pdf, graphic, "PDF"];
  Export[svg, graphic, "SVG"];
  Export[png, Rasterize[graphic, "Image", RasterSize -> imageWidth], "PNG"];
  Print[pdf];
  Print[svg];
  Print[png];
];


(* ================================================================ Figure 1 *)

f1 = data["figure1"];

fig1Prims = {
  panelField[{1.4, 16.35}, {41.7, 36.75}],
  panelField[{42.1, 16.35}, {73.6, 36.75}],
  panelField[{74.0, 16.35}, {98.7, 36.75}],
  panelField[{1.4, 3.70}, {32.7, 11.85}],
  panelField[{33.2, 3.70}, {64.3, 11.85}],
  panelField[{64.8, 3.70}, {98.7, 11.85}],
  panelHeading["A", "Primitive catalog", 1.5, 38.7],
  panelHeading["B", "Geometric operators", 1.5, 13.25],
  groupText["Regions", {2.5, 35.5}],
  groupText["Port-bearing components", {43.2, 35.5}],
  groupText["Paths", {75.1, 35.5}],
  rule,
  AbsoluteThickness[0.52],
  Line[{{1.5, 14.85}, {98.5, 14.85}}]
};

(* The complete region catalog remains the dominant field. *)
basicX = {6.9, 16.8, 26.7, 36.6};
basicY = {30.8, 22.4};
Do[
  row = Quotient[i - 1, 4] + 1;
  col = Mod[i - 1, 4] + 1;
  AppendTo[
    fig1Prims,
    reliefComponent[
      f1["basic"][[i]],
      {
        {basicX[[col]] - 3.70, basicX[[col]] + 3.70},
        {basicY[[row]] - 2.20, basicY[[row]] + 2.20}
      },
      crimson,
      False,
      {0.28, -0.40}
    ]
  ];
  AppendTo[
    fig1Prims,
    codeText[
      If[
        f1["basic"][[i, "name"]] == "L",
        "l-shape",
        ToLowerCase[f1["basic"][[i, "name"]]]
      ],
      {basicX[[col]], basicY[[row]] - 3.22},
      If[f1["basic"][[i, "name"]] == "regular_polygon", 4.40, 4.90]
    ]
  ],
  {i, Length[f1["basic"]]}
];

(* Six exact port-bearing primitives in a compact two-row ledger. *)
waveX = {47.2, 57.4, 67.6};
waveY = {30.7, 22.3};
Do[
  row = Quotient[i - 1, 3] + 1;
  col = Mod[i - 1, 3] + 1;
  AppendTo[
    fig1Prims,
    reliefComponent[
      f1["waveguides"][[i]],
      {
        {waveX[[col]] - 4.05, waveX[[col]] + 4.05},
        {waveY[[row]] - 2.05, waveY[[row]] + 2.05}
      },
      diffBlue,
      True,
      {0.30, -0.43},
      0.105
    ]
  ];
  AppendTo[
    fig1Prims,
    codeText[
      f1["waveguides"][[i, "name"]],
      {waveX[[col]], waveY[[row]] - 3.25},
      If[f1["waveguides"][[i, "name"]] == "coupler_straight", 4.50, 4.85]
    ]
  ],
  {i, Length[f1["waveguides"]]}
];

(* Centerlines stay intentionally thin: unlike bodies, a Path is 1-D. *)
pathX = {81.2, 92.2};
pathY = {32.0, 25.8, 19.6};
Do[
  row = Quotient[i - 1, 2] + 1;
  col = Mod[i - 1, 2] + 1;
  AppendTo[
    fig1Prims,
    pathGraphic[
      f1["paths"][[i]],
      {
        {pathX[[col]] - 4.0, pathX[[col]] + 4.0},
        {pathY[[row]] - 1.35, pathY[[row]] + 1.35}
      },
      verified,
      0.90
    ]
  ];
  AppendTo[
    fig1Prims,
    codeText[
      ToLowerCase[
        StringReplace[f1["paths"][[i, "name"]], "path." -> ""]
      ],
      {pathX[[col]], pathY[[row]] - 2.18},
      4.90
    ]
  ],
  {i, Length[f1["paths"]]}
];

(* Extrusion operators are compact supporting examples, not hero panels. *)
demoPath = f1["demo_path"];
demoPathSource = {
  {Min[demoPath[[All, 1]]], Max[demoPath[[All, 1]]]},
  {Min[demoPath[[All, 2]]], Max[demoPath[[All, 2]]]}
};

constantPathSpec = specFromRange[
  demoPathSource,
  {{3.5, 9.9}, {6.5, 9.0}},
  True
];
constantBodySpec = specFor[
  f1["constant_body", "polygons"],
  {{17.3, 26.5}, {5.3, 9.8}},
  True
];
AppendTo[
  fig1Prims,
  {
    pathStroke[demoPath, constantPathSpec, verified, 0.90],
    text["+", {11.3, 7.65}, 6.0],
    reliefRectangle[{12.8, 6.75}, {13.25, 8.55}, crimson, {0.16, -0.23}],
    arrowLine[{14.6, 7.65}, {16.3, 7.65}],
    reliefPolys[
      f1["constant_body", "polygons"],
      constantBodySpec,
      diffBlue,
      {0.27, -0.38}
    ],
    portDisks[f1["constant_body", "ports"], constantBodySpec, 0.10],
    text[
      "cross-section",
      {13.0, 5.15},
      4.90,
      Center
    ],
    groupText["extrude", {2.5, 10.6}]
  }
];

variablePathSpec = specFromRange[
  demoPathSource,
  {{34.4, 40.8}, {6.5, 9.0}},
  True
];
variableBodySpec = specFor[
  f1["variable_body", "polygons"],
  {{49.6, 58.8}, {5.0, 10.1}},
  True
];
transitionGlyph = {
  {43.60, 7.15},
  {43.60, 8.15},
  {45.55, 8.95},
  {45.55, 6.35}
};
AppendTo[
  fig1Prims,
  {
    pathStroke[demoPath, variablePathSpec, verified, 0.90],
    text["+", {42.2, 7.65}, 6.0],
    reliefEntries[{{transitionGlyph, crimson}}, {0.16, -0.23}, 0.30],
    arrowLine[{46.9, 7.65}, {48.6, 7.65}],
    reliefPolys[
      f1["variable_body", "polygons"],
      variableBodySpec,
      diffBlue,
      {0.27, -0.38}
    ],
    portDisks[f1["variable_body", "ports"], variableBodySpec, 0.10],
    text[
      "transition",
      {44.6, 5.15},
      4.90,
      Center
    ],
    groupText["extrude_transition", {34.3, 10.6}]
  }
];

(* Exact boolean inputs and all four accepted operator strings. *)
inputPolys = {f1["boolean_inputs", "A"], f1["boolean_inputs", "B"]};
inputSpec = specFor[inputPolys, {{65.8, 72.1}, {5.15, 9.85}}, True];
AppendTo[
  fig1Prims,
  {
    FaceForm[Directive[crimson, Opacity[0.62]]],
    EdgeForm[Directive[crimson, AbsoluteThickness[0.42]]],
    Polygon[tpoly[inputPolys[[1]], inputSpec]],
    FaceForm[Directive[diffBlue, Opacity[0.58]]],
    EdgeForm[Directive[diffBlue, AbsoluteThickness[0.42]]],
    Polygon[tpoly[inputPolys[[2]], inputSpec]],
    codeText["A", {66.2, 10.45}, 4.90, {Left, Center}],
    codeText["B", {71.2, 10.45}, 4.90, {Right, Center}],
    arrowLine[{73.0, 7.5}, {75.5, 7.5}]
  }
];

booleanCenters = {78.1, 84.1, 90.1, 96.1};
booleanPartitionColors = <|
  "A_only" -> crimson,
  "intersection" -> Blend[{crimson, diffBlue}, 0.50],
  "B_only" -> diffBlue
|>;
booleanPartitionKeys = <|
  "or" -> {"A_only", "intersection", "B_only"},
  "and" -> {"intersection"},
  "not" -> {"A_only"},
  "xor" -> {"A_only", "B_only"}
|>;
Do[
  operation = f1["booleans"][[i, "operation"]];
  booleanSpec = specFor[
    f1["booleans"][[i, "polygons"]],
    {
      {booleanCenters[[i]] - 2.15, booleanCenters[[i]] + 2.15},
      {5.4, 9.5}
    },
    True
  ];
  Do[
    AppendTo[
      fig1Prims,
      raisedPolys[
        f1["boolean_partitions", partitionKey],
        booleanSpec,
        booleanPartitionColors[partitionKey],
        {0.15, -0.22},
        0.24
      ]
    ],
    {partitionKey, booleanPartitionKeys[operation]}
  ];
  AppendTo[
    fig1Prims,
    groupText[
      operation,
      {booleanCenters[[i]], 10.6},
      Center
    ]
  ],
  {i, Length[f1["booleans"]]}
];

fig1 = Graphics[
  Flatten[fig1Prims],
  PlotRange -> {{0, 100}, {3.4, 40}},
  PlotRangePadding -> None,
  ImagePadding -> {{3, 3}, {3, 3}},
  Background -> paper,
  AspectRatio -> 36.6/100,
  (* LaTeX expands this canvas to the full two-column width.  A compact
     compositor width makes absolute type and rule weights land at the same
     final publication scale as the Matplotlib-composed verification figure. *)
  ImageSize -> 370
];

exportFigure[fig1, "fig_primitives", 2200];


(* ================================================================ Figure 2 *)

f2 = data["figure2"];
mu = "\[Micro]m";
symW = Style["w", FontFamily -> mathFont, FontSlant -> Italic];
symG = Style["g", FontFamily -> mathFont, FontSlant -> Italic];
symLc = subscripted["L", "c"];
symLb = subscripted["L", "b"];
symLs = subscripted["L", "s"];

groupColors = <|
  "straight" -> diffBlue,
  "bend" -> crimson,
  "coupler" -> verified
|>;

fig2Prims = {
  panelField[{1.4, 14.35}, {26.8, 35.8}],
  panelField[{34.5, 14.35}, {98.7, 35.8}],
  panelField[{1.4, 0.45}, {44.0, 9.65}],
  panelField[{61.5, 0.45}, {98.7, 9.65}],
  panelHeading["A", "From geometric primitives to a PCell", 1.5, 37.8],
  panelHeading["B", "Same PCell source, new geometry", 1.5, 11.15],
  groupText["Exact instances", {2.0, 35.0}],
  groupText["Connected cell", {35.4, 35.0}],
  rule,
  AbsoluteThickness[0.52],
  Line[{{1.5, 12.8}, {98.5, 12.8}}]
};

(* Left: literal multiplicity.  Whitespace and visible endpoint ports keep the
   nine exact instances distinct before they are connected. *)
Do[
  AppendTo[
    fig2Prims,
    reliefComponent[
      f2["primitives"][[1]],
      {{3.3, 14.2}, {32.66 - 0.98 i, 33.34 - 0.98 i}},
      diffBlue,
      True,
      {0.12, -0.10},
      0.095
    ]
  ],
  {i, 0, 3}
];
AppendTo[
  fig2Prims,
  {
    displayText[
      "four straights",
      {14.8, 31.25},
      6.10,
      {Left, Center}
    ],
    text[
      Row[{symLs, " = 8.0 ", mu}],
      {14.8, 29.85},
      5.00,
      {Left, Center}
    ],
    text[
      Row[{symW, " = 0.50 ", mu}],
      {14.8, 28.60},
      5.00,
      {Left, Center}
    ]
  }
];

AppendTo[
  fig2Prims,
  reliefOrientedComponent[
    f2["primitives"][[2]],
    {{3.3, 8.30}, {25.95, 27.35}},
    crimson,
    "o2",
    {0.12, -0.11},
    0.090
  ]
];
AppendTo[
  fig2Prims,
  reliefOrientedComponent[
    f2["primitives"][[2, "negative"]],
    {{3.3, 8.30}, {22.65, 24.05}},
    crimson,
    "o2",
    {0.12, -0.11},
    0.090
  ]
];
AppendTo[
  fig2Prims,
  reliefOrientedComponent[
    f2["primitives"][[2]],
    {{9.10, 14.10}, {25.95, 27.35}},
    crimson,
    "o1",
    {0.12, -0.11},
    0.090
  ]
];
AppendTo[
  fig2Prims,
  reliefOrientedComponent[
    f2["primitives"][[2, "negative"]],
    {{9.10, 14.10}, {22.65, 24.05}},
    crimson,
    "o1",
    {0.12, -0.11},
    0.090
  ]
];
AppendTo[
  fig2Prims,
  {
    displayText[
      "four S-bends",
      {14.8, 25.15},
      6.10,
      {Left, Center}
    ],
    text[
      Row[{symLb, " = 18.0 ", mu}],
      {14.8, 23.70},
      5.00,
      {Left, Center}
    ],
    text[
      Row[{
        deltaY, " = ",
        Style["\[PlusMinus]", FontFamily -> mathFont], "3.0 ", mu
      }],
      {14.8, 22.45},
      5.00,
      {Left, Center}
    ]
  }
];

couplerPrimitive = f2["primitives"][[3]];
couplerPrimitiveSpec = specFor[
  couplerPrimitive["polygons"],
  {{3.3, 14.2}, {18.05, 20.55}},
  True
];
AppendTo[
  fig2Prims,
  {
    reliefCouplingPair[
      couplerPrimitive["polygons"],
      couplerPrimitiveSpec,
      verified,
      {0.23, -0.31},
      0.30
    ],
    portDisks[couplerPrimitive["ports"], couplerPrimitiveSpec, 0.095, ink]
  }
];
AppendTo[
  fig2Prims,
  {
    displayText[
      "coupling section",
      {14.8, 18.45},
      6.10,
      {Left, Center}
    ],
    text[
      Row[{symLc, " = 10.0 ", mu}],
      {14.8, 16.95},
      5.00,
      {Left, Center}
    ],
    text[
      Row[{symG, " = 0.25 ", mu}],
      {14.8, 15.70},
      5.00,
      {Left, Center}
    ],
    arrowLine[{27.4, 25.3}, {34.0, 25.3}],
    codeText[
      Column[{"8 calls", "connect(...)"}, Alignment -> Center, Spacings -> 0.05],
      {30.7, 27.25},
      4.90
    ]
  }
];

(* Right: one large exact component.  Color records construction provenance. *)
semanticGroups = f2["semantic_groups"];
semanticSpec = specFor[
  allGroupPolys[semanticGroups],
  {{35.3, 98.1}, {21.0, 28.8}},
  True
];
AppendTo[
  fig2Prims,
  {
    reliefGroups[
      KeyDrop[semanticGroups, {"coupler"}],
      semanticSpec,
      groupColors,
      {0.42, -0.56},
      0.30
    ],
    reliefCouplingPair[
      semanticGroups["coupler"],
      semanticSpec,
      verified,
      {0.42, -0.56},
      0.30
    ],
    pointDisks[
      f2["semantic_meta", "connections"],
      semanticSpec,
      0.092,
      verified
    ],
    portDisks[
      associationPorts[f2["semantic_meta", "ports"]],
      semanticSpec,
      0.125,
      ink
    ]
  }
];

xAt[value_] := tp[{value, 0.0}, semanticSpec][[1]];
yAt[value_] := tp[{0.0, value}, semanticSpec][[2]];

AppendTo[
  fig2Prims,
  {
    horizontalDimension[xAt[-26.0], xAt[-18.0], 32.7, symLs],
    horizontalDimension[xAt[-18.0], xAt[0.0], 32.7, symLb],
    horizontalDimension[xAt[0.0], xAt[10.0], 32.7, symLc],
    verticalDimension[
      xAt[-18.0] - 1.15,
      yAt[-3.0],
      yAt[0.0],
      deltaY,
      -1
    ],
    callout[
      tp[{-22.0, 4.0}, semanticSpec],
      {xAt[-22.0], 30.2},
      {xAt[-22.0] + 2.2, 30.2},
      symW
    ],
    callout[
      tp[{5.0, 0.375}, semanticSpec],
      {xAt[5.0], 19.2},
      {xAt[5.0] + 2.0, 19.2},
      symG
    ]
  }
];

(* Shared physical scale below: only the two named values change. *)
familyDomain = {{-26.0, 42.0}, {-3.4, 4.4}};
baseSpec = specFromRange[familyDomain, {{7.5, 42.5}, {3.0, 8.6}}, True];
retunedSpec = specFromRange[familyDomain, {{63.0, 98.0}, {3.0, 8.6}}, True];

AppendTo[
  fig2Prims,
  {
    reliefGroups[
      KeyDrop[f2["semantic_groups"], {"coupler"}],
      baseSpec,
      groupColors,
      {0.27, -0.37},
      0.26
    ],
    reliefCouplingPair[
      f2["semantic_groups", "coupler"],
      baseSpec,
      verified,
      {0.27, -0.37},
      0.26
    ],
    portDisks[f2["base", "ports"], baseSpec, 0.105, ink],
    reliefGroups[
      KeyDrop[f2["retuned_semantic_groups"], {"coupler"}],
      retunedSpec,
      groupColors,
      {0.27, -0.37},
      0.26
    ],
    reliefCouplingPair[
      f2["retuned_semantic_groups", "coupler"],
      retunedSpec,
      verified,
      {0.27, -0.37},
      0.26
    ],
    portDisks[f2["retuned", "ports"], retunedSpec, 0.105, ink],
    arrowLine[{45.5, 6.15}, {60.3, 6.15}, ruleStrong],
    text[
      Row[{symG, ": 0.25 \[Rule] 0.75 ", mu}],
      {52.9, 8.45},
      5.10
    ],
    text[
      Row[{symLc, ": 10 \[Rule] 16 ", mu}],
      {52.9, 3.85},
      5.10
    ],
    text[
      Row[{symG, " = 0.25 ", mu, "    ", symLc, " = 10 ", mu}],
      {25.0, 1.45},
      5.00
    ],
    text[
      Row[{symG, " = 0.75 ", mu, "    ", symLc, " = 16 ", mu}],
      {80.5, 1.45},
      5.00
    ]
  }
];

fig2 = Graphics[
  Flatten[fig2Prims],
  PlotRange -> {{0, 100}, {0, 39}},
  PlotRangePadding -> None,
  ImagePadding -> {{3, 3}, {3, 3}},
  Background -> paper,
  AspectRatio -> 39/100,
  ImageSize -> 370
];

exportFigure[fig2, "fig_composition", 2200];
