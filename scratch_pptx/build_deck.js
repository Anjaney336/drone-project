const pptxgen = require("pptxgenjs");

const OUT = "C:\\Users\\hp\\AppData\\Local\\Temp\\claude\\C--Users-hp-Documents-dorne-interceptor\\55af3457-5444-4769-be4b-3fd656997cca\\scratchpad\\AERIS_pitch_deck.pptx";

// Ocean Gradient palette
const DEEP = "065A82";
const TEAL = "1C7293";
const MIDNIGHT = "21295C";
const MINT = "02C39A";
const OFFWHITE = "F7FAFB";
const INK = "142333";
const MUTED = "5C7080";
const WHITE = "FFFFFF";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
const W = 13.333, H = 7.5;

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: MIDNIGHT };
  return s;
}
function lightSlide() {
  const s = pres.addSlide();
  s.background = { color: OFFWHITE };
  return s;
}
function pageNum(s, n, dark) {
  s.addText(String(n).padStart(2, "0"), {
    x: W - 0.9, y: H - 0.55, w: 0.6, h: 0.35,
    fontFace: "Calibri", fontSize: 10, color: dark ? "8FA6C9" : "AEB9C4", align: "right", margin: 0,
  });
}
function circleNum(s, x, y, d, label, fill, textColor) {
  s.addShape("ellipse", { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" } });
  s.addText(label, {
    x, y, w: d, h: d, align: "center", valign: "middle",
    fontFace: "Cambria", bold: true, fontSize: d > 0.7 ? 22 : 16, color: textColor, margin: 0,
  });
}

// ---------- Slide 1: Title ----------
{
  const s = darkSlide();
  // abstract flight-path motif: dotted line + nodes, top right
  const nodes = [[9.7, 1.3], [10.6, 1.9], [11.3, 1.3], [12.2, 2.0]];
  for (let i = 0; i < nodes.length - 1; i++) {
    s.addShape("line", {
      x: nodes[i][0], y: nodes[i][1], w: nodes[i + 1][0] - nodes[i][0], h: nodes[i + 1][1] - nodes[i][1],
      line: { color: TEAL, width: 1.5, dashType: "dash" },
    });
  }
  nodes.forEach(([nx, ny]) => s.addShape("ellipse", { x: nx - 0.06, y: ny - 0.06, w: 0.12, h: 0.12, fill: { color: MINT }, line: { type: "none" } }));

  s.addText("AERIS", {
    x: 0.9, y: 2.55, w: 10, h: 1.3, fontFace: "Cambria", bold: true, fontSize: 64, color: WHITE, margin: 0,
  });
  s.addText("AI-Enabled Drone Mission Intelligence", {
    x: 0.95, y: 3.75, w: 9.5, h: 0.6, fontFace: "Calibri", fontSize: 22, color: "CADCFC", margin: 0,
  });
  s.addShape("ellipse", { x: 0.95, y: 4.7, w: 0.1, h: 0.1, fill: { color: MINT }, line: { type: "none" } });
  s.addText("Turning drone missions into decisions you can trust", {
    x: 1.2, y: 4.55, w: 8, h: 0.4, fontFace: "Calibri", italic: true, fontSize: 14, color: "8FA6C9", margin: 0,
  });
  pageNum(s, 1, true);
}

// ---------- Slide 2: Problem statement ----------
{
  const s = lightSlide();
  s.addText("The Problem", { x: 0.9, y: 0.6, w: 8, h: 0.7, fontFace: "Cambria", bold: true, fontSize: 34, color: INK, margin: 0 });
  s.addText("Drones fly. Nobody has time to look at everything they bring back.", {
    x: 0.9, y: 1.35, w: 9.5, h: 0.5, fontFace: "Calibri", fontSize: 15, color: MUTED, margin: 0,
  });

  const items = [
    ["Bridges, roads, dams, farms", "Governments and companies fly drones over them to check for problems."],
    ["Hundreds of photos, one flight", "A single flight creates a huge pile of photos and flight data."],
    ["Nobody checks it all", "There isn't enough time to look at every photo by hand."],
    ["Can you even trust it?", "Even if AI spots something, was the drone's GPS working? Did the connection keep dropping?"],
  ];
  const colW = 2.75, gap = 0.35, startX = 0.9, y0 = 2.3;
  items.forEach((it, i) => {
    const x = startX + i * (colW + gap);
    s.addShape("roundRect", { x, y: y0, w: colW, h: 3.4, rectRadius: 0.12, fill: { color: WHITE }, line: { color: "E1E8ED", width: 1 }, shadow: { type: "outer", color: "142333", opacity: 0.12, blur: 8, offset: 3, angle: 90 } });
    circleNum(s, x + 0.3, y0 + 0.3, 0.55, String(i + 1), i === 3 ? DEEP : TEAL, WHITE);
    s.addText(it[0], { x: x + 0.25, y: y0 + 1.05, w: colW - 0.5, h: 0.75, fontFace: "Cambria", bold: true, fontSize: 14.5, color: INK, margin: 0 });
    s.addText(it[1], { x: x + 0.25, y: y0 + 1.75, w: colW - 0.5, h: 1.5, fontFace: "Calibri", fontSize: 11.5, color: MUTED, margin: 0, lineSpacingMultiple: 1.15 });
  });
  pageNum(s, 2, false);
}

// ---------- Slide 3: Why this matters ----------
{
  const s = darkSlide();
  s.addText("Why This Matters", { x: 0.9, y: 0.6, w: 9, h: 0.7, fontFace: "Cambria", bold: true, fontSize: 34, color: WHITE, margin: 0 });

  // two comparison cards
  const cardY = 2.1, cardW = 5.3, cardH = 3.9;
  // Left: shaky flight
  s.addShape("roundRect", { x: 0.9, y: cardY, w: cardW, h: cardH, rectRadius: 0.12, fill: { color: "2C3768" }, line: { type: "none" } });
  s.addText("SHAKY FLIGHT", { x: 1.2, y: cardY + 0.3, w: cardW - 0.6, h: 0.4, fontFace: "Calibri", bold: true, fontSize: 12, color: "F9A8A8", charSpacing: 2, margin: 0 });
  s.addText("\u201CPossible crack\u201D", { x: 1.2, y: cardY + 0.85, w: cardW - 0.6, h: 0.6, fontFace: "Cambria", bold: true, fontSize: 22, color: WHITE, margin: 0 });
  s.addText([
    { text: "GPS signal kept dropping", options: { breakLine: true, bullet: { code: "2022" } } },
    { text: "Connection lost twice mid-flight", options: { breakLine: true, bullet: { code: "2022" } } },
    { text: "Battery was low near the end", options: { breakLine: true, bullet: { code: "2022" } } },
  ], { x: 1.2, y: cardY + 1.6, w: cardW - 0.6, h: 1.6, fontFace: "Calibri", fontSize: 13, color: "C7D2E8", paraSpaceAfter: 8, margin: 0 });
  s.addText("Should you trust this finding? Hard to say.", { x: 1.2, y: cardY + cardH - 0.7, w: cardW - 0.6, h: 0.5, fontFace: "Calibri", italic: true, fontSize: 12, color: "F9A8A8", margin: 0 });

  // Right: clean flight
  s.addShape("roundRect", { x: 0.9 + cardW + 0.35, y: cardY, w: cardW, h: cardH, rectRadius: 0.12, fill: { color: "1C4A5C" }, line: { type: "none" } });
  const rx = 0.9 + cardW + 0.35;
  s.addText("CLEAN FLIGHT", { x: rx + 0.3, y: cardY + 0.3, w: cardW - 0.6, h: 0.4, fontFace: "Calibri", bold: true, fontSize: 12, color: MINT, charSpacing: 2, margin: 0 });
  s.addText("\u201CPossible crack\u201D", { x: rx + 0.3, y: cardY + 0.85, w: cardW - 0.6, h: 0.6, fontFace: "Cambria", bold: true, fontSize: 22, color: WHITE, margin: 0 });
  s.addText([
    { text: "GPS signal stayed strong", options: { breakLine: true, bullet: { code: "2022" } } },
    { text: "Connection never dropped", options: { breakLine: true, bullet: { code: "2022" } } },
    { text: "Battery healthy throughout", options: { breakLine: true, bullet: { code: "2022" } } },
  ], { x: rx + 0.3, y: cardY + 1.6, w: cardW - 0.6, h: 1.6, fontFace: "Calibri", fontSize: 13, color: "CFE8E0", paraSpaceAfter: 8, margin: 0 });
  s.addText("This finding is worth acting on.", { x: rx + 0.3, y: cardY + cardH - 0.7, w: cardW - 0.6, h: 0.5, fontFace: "Calibri", italic: true, fontSize: 12, color: MINT, margin: 0 });

  s.addText("Same words, same photo pattern \u2014 completely different level of trust. Today that difference gets lost.", {
    x: 0.9, y: cardY + cardH + 0.25, w: 11.5, h: 0.5, fontFace: "Calibri", fontSize: 13.5, color: "CADCFC", margin: 0,
  });
  pageNum(s, 3, true);
}

// ---------- Slide 4: The solution ----------
{
  const s = lightSlide();
  s.addText("The Solution", { x: 0.9, y: 0.7, w: 8, h: 0.7, fontFace: "Cambria", bold: true, fontSize: 34, color: INK, margin: 0 });
  s.addShape("roundRect", { x: 0.9, y: 1.7, w: 11.5, h: 2.0, rectRadius: 0.12, fill: { color: DEEP }, line: { type: "none" } });
  s.addText("Upload your drone photos and flight data. Get a real AI-checked finding, plus a trust score for the flight itself \u2014 so a human can decide what to do next with the full picture.", {
    x: 1.4, y: 1.95, w: 10.5, h: 1.5, fontFace: "Cambria", fontSize: 20, color: WHITE, valign: "middle", margin: 0, lineSpacingMultiple: 1.25,
  });

  const pillars = [
    ["What AI saw", "A trained model checks your photos for possible problems and shows exactly where."],
    ["Can we trust it", "A plain HIGH / MEDIUM / LOW score for the flight itself, with reasons in plain English."],
    ["What to do next", "A human always makes the final call \u2014 AI only flags, never confirms."],
  ];
  const pw = 3.6, gap = 0.35, x0 = 0.9, y0 = 4.15;
  pillars.forEach((p, i) => {
    const x = x0 + i * (pw + gap);
    circleNum(s, x, y0, 0.6, String(i + 1), MINT, MIDNIGHT);
    s.addText(p[0], { x: x + 0.8, y: y0 - 0.05, w: pw - 0.8, h: 0.5, fontFace: "Cambria", bold: true, fontSize: 16, color: INK, valign: "middle", margin: 0 });
    s.addText(p[1], { x: x, y: y0 + 0.75, w: pw, h: 1.5, fontFace: "Calibri", fontSize: 12, color: MUTED, margin: 0, lineSpacingMultiple: 1.2 });
  });
  pageNum(s, 4, false);
}

// ---------- Slide 5: How it works ----------
{
  const s = darkSlide();
  s.addText("How It Works", { x: 0.9, y: 0.55, w: 8, h: 0.7, fontFace: "Cambria", bold: true, fontSize: 34, color: WHITE, margin: 0 });
  s.addText("Four steps, start to finish", { x: 0.95, y: 1.25, w: 8, h: 0.4, fontFace: "Calibri", fontSize: 14, color: "8FA6C9", margin: 0 });

  const steps = [
    ["Upload", "Create a mission. Add your photos, and flight data if you have it."],
    ["AI checks", "A trained model looks at each photo for possible problems."],
    ["Trust score", "AERIS scores how reliable the flight was \u2014 HIGH, MEDIUM, or LOW, with reasons."],
    ["Human decides", "A reviewer confirms, rejects, or asks for a re-check. AI never has the final say."],
  ];
  const cw = 2.75, gap = 0.3, x0 = 0.9, y0 = 2.1;
  steps.forEach((st, i) => {
    const x = x0 + i * (cw + gap);
    s.addShape("roundRect", { x, y: y0, w: cw, h: 3.9, rectRadius: 0.12, fill: { color: "24316B" }, line: { type: "none" } });
    circleNum(s, x + 0.3, y0 + 0.35, 0.6, String(i + 1), MINT, MIDNIGHT);
    s.addText(st[0], { x: x + 0.3, y: y0 + 1.2, w: cw - 0.6, h: 0.5, fontFace: "Cambria", bold: true, fontSize: 17, color: WHITE, margin: 0 });
    s.addText(st[1], { x: x + 0.3, y: y0 + 1.8, w: cw - 0.6, h: 1.9, fontFace: "Calibri", fontSize: 11.5, color: "C7D2E8", margin: 0, lineSpacingMultiple: 1.2 });
    if (i < steps.length - 1) {
      s.addText("\u2192", { x: x + cw - 0.05, y: y0 + 1.5, w: 0.4, h: 0.5, fontFace: "Calibri", fontSize: 20, color: MINT, align: "center", margin: 0 });
    }
  });
  pageNum(s, 5, true);
}

// ---------- Slide 6: What makes AERIS different ----------
{
  const s = lightSlide();
  s.addText("What Makes AERIS Different", { x: 0.9, y: 0.7, w: 10, h: 0.7, fontFace: "Cambria", bold: true, fontSize: 32, color: INK, margin: 0 });

  const leftW = 5.4;
  s.addShape("roundRect", { x: 0.9, y: 1.85, w: leftW, h: 4.3, rectRadius: 0.12, fill: { color: "EDF1F4" }, line: { color: "DCE3E9", width: 1 } });
  s.addText("MOST TOOLS", { x: 1.25, y: 2.1, w: leftW - 0.7, h: 0.4, fontFace: "Calibri", bold: true, fontSize: 11, color: MUTED, charSpacing: 2, margin: 0 });
  s.addText("\u201CHere\u2019s a possible crack in this photo.\u201D", { x: 1.25, y: 2.6, w: leftW - 0.7, h: 1.1, fontFace: "Cambria", italic: true, fontSize: 19, color: INK, margin: 0, lineSpacingMultiple: 1.2 });
  s.addText("Full stop. You still don\u2019t know if the flight behind that photo was any good.", { x: 1.25, y: 3.9, w: leftW - 0.7, h: 1.8, fontFace: "Calibri", fontSize: 13, color: MUTED, margin: 0, lineSpacingMultiple: 1.3 });

  const rx = 0.9 + leftW + 0.4, rw = 11.5 - leftW - 0.4;
  s.addShape("roundRect", { x: rx, y: 1.85, w: rw, h: 4.3, rectRadius: 0.12, fill: { color: DEEP }, line: { type: "none" } });
  s.addText("AERIS", { x: rx + 0.35, y: 2.1, w: rw - 0.7, h: 0.4, fontFace: "Calibri", bold: true, fontSize: 11, color: MINT, charSpacing: 2, margin: 0 });
  s.addText("\u201CHere\u2019s a possible crack \u2014 and here\u2019s how much you should trust this flight\u2019s data.\u201D", { x: rx + 0.35, y: 2.6, w: rw - 0.7, h: 1.5, fontFace: "Cambria", bold: true, fontSize: 19, color: WHITE, margin: 0, lineSpacingMultiple: 1.2 });
  s.addText("One combined answer: what AI saw, and whether you can believe it.", { x: rx + 0.35, y: 4.35, w: rw - 0.7, h: 1.6, fontFace: "Calibri", fontSize: 13, color: "CADCFC", margin: 0, lineSpacingMultiple: 1.3 });

  pageNum(s, 6, false);
}

// ---------- Slide 7: What's real today ----------
{
  const s = lightSlide();
  s.addText("What\u2019s Real Today", { x: 0.9, y: 0.6, w: 9, h: 0.7, fontFace: "Cambria", bold: true, fontSize: 34, color: INK, margin: 0 });
  s.addText("Working, tested, end to end \u2014 not a mockup", { x: 0.95, y: 1.3, w: 9, h: 0.4, fontFace: "Calibri", fontSize: 14, color: MUTED, margin: 0 });

  const rows = [
    ["Bridge, road & dam inspection", "Fully working. Upload real photos, get a real AI check \u2014 tested in a real browser, not just behind the scenes."],
    ["Two trained AI models", "One finds possible defects, one traces out cracks. Both trained and measured on real test photos."],
    ["Works without internet", "Save your data with no signal. It syncs automatically the moment you\u2019re back online."],
    ["A human always reviews", "Every AI finding is a flag, never a confirmed fact, until a person signs off."],
  ];
  const y0 = 2.1, rh = 1.15;
  rows.forEach((r, i) => {
    const y = y0 + i * rh;
    s.addShape("roundRect", { x: 0.9, y, w: 11.5, h: rh - 0.18, rectRadius: 0.1, fill: { color: WHITE }, line: { color: "E1E8ED", width: 1 } });
    s.addShape("ellipse", { x: 1.15, y: y + (rh - 0.18) / 2 - 0.14, w: 0.28, h: 0.28, fill: { color: MINT }, line: { type: "none" } });
    s.addText("\u2713", { x: 1.15, y: y + (rh - 0.18) / 2 - 0.14, w: 0.28, h: 0.28, align: "center", valign: "middle", fontFace: "Calibri", bold: true, fontSize: 13, color: WHITE, margin: 0 });
    s.addText(r[0], { x: 1.65, y: y + 0.1, w: 3.7, h: rh - 0.35, fontFace: "Cambria", bold: true, fontSize: 14, color: INK, valign: "middle", margin: 0 });
    s.addText(r[1], { x: 5.5, y: y + 0.1, w: 6.7, h: rh - 0.35, fontFace: "Calibri", fontSize: 12, color: MUTED, valign: "middle", margin: 0, lineSpacingMultiple: 1.15 });
  });
  pageNum(s, 7, false);
}

// ---------- Slide 8: What's in progress ----------
{
  const s = darkSlide();
  s.addText("What\u2019s In Progress", { x: 0.9, y: 0.7, w: 9, h: 0.7, fontFace: "Cambria", bold: true, fontSize: 34, color: WHITE, margin: 0 });
  s.addText("Named honestly \u2014 not hidden, not oversold", { x: 0.95, y: 1.4, w: 9, h: 0.4, fontFace: "Calibri", fontSize: 14, color: "8FA6C9", margin: 0 });

  const cardY = 2.3, cardW = 5.3, cardH = 3.8;
  [
    ["Agriculture / crop health", "A real soybean crop dataset is downloading and being checked right now. Not switched on until a real trained model exists.", "62%"],
    ["Video analysis", "Photos work today. Checking video frame-by-frame is planned, but not built yet.", "Planned"],
  ].forEach((c, i) => {
    const x = 0.9 + i * (cardW + 0.35);
    s.addShape("roundRect", { x, y: cardY, w: cardW, h: cardH, rectRadius: 0.12, fill: { color: "2C3768" }, line: { type: "none" } });
    s.addText(c[2], { x: x + 0.35, y: cardY + 0.35, w: cardW - 0.7, h: 0.9, fontFace: "Cambria", bold: true, fontSize: 40, color: MINT, margin: 0 });
    s.addText(c[0], { x: x + 0.35, y: cardY + 1.35, w: cardW - 0.7, h: 0.6, fontFace: "Cambria", bold: true, fontSize: 18, color: WHITE, margin: 0 });
    s.addText(c[1], { x: x + 0.35, y: cardY + 2.0, w: cardW - 0.7, h: 1.6, fontFace: "Calibri", fontSize: 13, color: "C7D2E8", margin: 0, lineSpacingMultiple: 1.3 });
  });
  pageNum(s, 8, true);
}

// ---------- Slide 9: Why the honesty matters ----------
{
  const s = lightSlide();
  s.addText("Why The Honesty Matters", { x: 0.9, y: 0.8, w: 10.5, h: 0.7, fontFace: "Cambria", bold: true, fontSize: 32, color: INK, margin: 0 });
  s.addShape("roundRect", { x: 0.9, y: 1.9, w: 11.5, h: 2.3, rectRadius: 0.12, fill: { color: "EDF1F4" }, line: { color: "DCE3E9", width: 1 } });
  s.addText("Every number and claim in AERIS is backed by something real and reproducible. Nothing is faked to look more finished than it is.", {
    x: 1.4, y: 2.15, w: 10.5, h: 1.9, fontFace: "Cambria", fontSize: 22, italic: true, color: INK, valign: "middle", margin: 0, lineSpacingMultiple: 1.3,
  });
  s.addText("This is a design rule, not a limitation \u2014 it\u2019s what new members and outsiders should trust about this project from day one.", {
    x: 0.9, y: 4.5, w: 10.5, h: 0.6, fontFace: "Calibri", fontSize: 14, color: MUTED, margin: 0,
  });
  pageNum(s, 9, false);
}

// ---------- Slide 10: Closing ----------
{
  const s = darkSlide();
  const nodes = [[1.0, 5.6], [2.0, 5.0], [3.0, 5.6], [4.1, 4.9]];
  for (let i = 0; i < nodes.length - 1; i++) {
    s.addShape("line", { x: nodes[i][0], y: nodes[i][1], w: nodes[i + 1][0] - nodes[i][0], h: nodes[i + 1][1] - nodes[i][1], line: { color: TEAL, width: 1.5, dashType: "dash" } });
  }
  nodes.forEach(([nx, ny]) => s.addShape("ellipse", { x: nx - 0.06, y: ny - 0.06, w: 0.12, h: 0.12, fill: { color: MINT }, line: { type: "none" } }));

  s.addText("AERIS", { x: 0.9, y: 2.6, w: 10, h: 1.1, fontFace: "Cambria", bold: true, fontSize: 54, color: WHITE, margin: 0 });
  s.addText("Turning drone missions into decisions you can trust.", {
    x: 0.95, y: 3.7, w: 10, h: 0.6, fontFace: "Calibri", fontSize: 20, color: "CADCFC", margin: 0,
  });
  pageNum(s, 10, true);
}

pres.writeFile({ fileName: OUT }).then(() => console.log("WROTE " + OUT));
