# Agent Instructions: Extract Question Coordinates from PDF Line Data

## Input Format
You receive a list of pages, each with lines containing:
```json
{
  "page_number": 2,
  "lines": [
    {"text": "1", "x0": 49.6, "y0": 63.4, "x1": 55.6, "y1": 71.4},
    {"text": "The heights, H centimetres...", "x0": 72.3, "y0": 63.4, ...},
    ...
  ]
}
```
- `x0`, `y0`: top-left of text bbox (points, origin top-left)
- `y` increases downward
- Coordinates are in PDF points (1/72 inch)

## Reliable Visual Signals (Cambridge Papers)

| Element | x-range | y-pattern | Meaning |
|---------|---------|-----------|---------|
| Question number | 49.0–50.5 | appears once per question | **Question start** |
| Part label `(a)` `(b)` `(c)` | 71.0–73.0 or 94.0–96.0 | indented | **Part start** |
| Mark `[3]` `[4]` `[5]` | 530.0–535.0 | right margin | **Part end** (question text ends here) |
| Dotted lines `..................` | 94.0–96.0 | regular spacing ~26pt | **Answer space** — NOT part of question |
| Page footer | any | y > 780 | "Cambridge University Press", "PapaCambridge", "Trace ID" |
| "Turn over" | ~493 | y ≈ 781 | Page continues |
| "Additional page" | ~260 | y ≈ 63 | Blank answer page — ignore |
| "BLANK PAGE" | ~260 | y ≈ 63 | Ignore |

---

## Core Rules

### 1. Question Start
- Look for a **number at x ≈ 49.6** (e.g., "1", "2", "3"...)
- This is the **question stem start** (`start_y` for the first part)
- The stem text follows at `x ≈ 72.3`
- **If no number at x≈49.6 on a page**, check if it's a continuation of the previous question (see Rule 6)

### 2. Part Start
- Pattern: `(a)`, `(b)`, `(c)`, `(i)`, `(ii)`, `(a)(i)` at `x ≈ 72.3` or `95.0`
- `start_y` = y of this part label
- If a question has no parts (single part), the question number line IS the part start

### 3. Part End (Critical)
- **Primary signal**: Mark box `[n]` at `x ≈ 532.3` on the SAME line as the part label or the last line of question text
- **End y** = y of the mark `[n]` line
- **Immediately after the mark line**: dotted lines begin → answer space → STOP
- **Do NOT include dotted lines** in the crop

### 4. Diagrams / Graphs / Large Gaps
When you see a part that mentions a diagram/graph (e.g., "Draw a cumulative frequency graph", "Complete the tree diagram"):
- The mark `[n]` appears **before** the diagram space
- After the mark, there is a **large y-gap** with no text, no dotted lines
- **End of that part** = y of the mark `[n]` line (same as normal)
- **Do NOT extend to page footer** — the diagram is drawn by the student, not part of the question text
- **Exception**: If the mark `[n]` is missing (rare), end at the last line of question text before the gap

### 5. Multi-Page Questions
- A question/part can span pages
- If a part starts on page N and the mark `[n]` is on page N+1:
  - `start_page` = N, `start_y` = part label y on page N
  - `end_page` = N+1, `end_y` = mark `[n]` y on page N+1
- **Middle pages** (if any): full page content belongs to the question
- **Check**: next page should NOT have a new question number at x≈49.6

### 6. New Question vs Continuation (Critical)
**Before starting a new question, verify:**
- Is there a number at `x ≈ 49.6` on the current page?
- **YES** → New question. Close previous question.
- **NO** → Continuation of previous question. Keep looking for its parts.
- **Example of my error**: Page 7 had parts (c)(d) at x≈72.3 but NO number at x≈49.6. The previous page (6) ended with Q4 part (b). These are Q4(c)(d), not Q5.

### 7. Process Order: Question by Question
```
For each question in sequence:
  1. Find question number at x≈49.6 → record question_start_y
  2. Find ALL parts for THIS question (loop):
     - Find next part label (a)/(b)/(c)...
     - Find its mark [n] at x≈532.3
     - Record part: {question, part, start_page, start_y, end_page, end_y}
     - If next part label found before new question number → continue
     - If new question number at x≈49.6 found → STOP, go to step 1 for next question
     - If page ends without new question number → check next page for continuation
  3. When new question number found → repeat from step 1
```
**Do not jump ahead.** Finish extracting all parts of Q1 before looking for Q2.

### 8. Output Structure
```json
[
  {"question": "1", "part": "a", "start_page": 2, "start_y": 63.4, "end_page": 2, "end_y": 102.4},
  {"question": "1", "part": "b", "start_page": 2, "start_y": 427.4, "end_page": 2, "end_y": 466.4},
  {"question": "2", "part": "a", "start_page": 3, "start_y": 63.4, "end_page": 3, "end_y": 76.4},
  ...
]
```
- `part`: "a", "b", "c", "a(i)", "a(ii)", "" (for single-part questions)
- `start_y`/`end_y`: float, one decimal
- Include `note` field only for diagram gaps or anomalies

### 9. Things to Ignore (Not Question Content)
- Page headers: "DFD", "* 0000800000002 *", "DO NOT WRITE IN THIS MARGIN"
- Page footers: "Cambridge University Press", "PapaCambridge", "Trace ID", "9709/52/F/M/26"
- "Additional page", "BLANK PAGE", "Turn over"
- Dotted answer lines
- Copyright/acknowledgement pages (last 1-2 pages)

---

## Worked Example: Page 2 (Q1)

**Lines:**
```
y=63.4 x=49.6: 1                                    ← Question start
y=63.4 x=72.3: The heights, H centimetres...        ← Stem
y=76.4 x=72.3: measured, with the following results.
y=102.4 x=117.0: 10496   110   122   96   101   99   113
y=128.4 x=72.3: (a) Calculate unbiased estimates...  ← Part (a) start
y=128.4 x=532.3: [3]                                 ← Part (a) END (mark)
y=154.4 x=95.0: ....................................  ← Answer space starts → STOP
...
y=427.4 x=72.3: It is now given that...              ← Part (b) start
y=453.4 x=72.3: (b) Stating a necessary assumption...
y=466.4 x=532.3: [4]                                 ← Part (b) END
y=492.4 x=95.0: ....................................  ← Answer space → STOP
y=784.5 x=49.6: Cambridge University Press...        ← Footer
```

**Output:**
```json
[
  {"question": "1", "part": "a", "start_page": 2, "start_y": 128.4, "end_page": 2, "end_y": 128.4},
  {"question": "1", "part": "b", "start_page": 2, "start_y": 453.4, "end_page": 2, "end_y": 466.4}
]
```
Note: Part (a) start_y = 128.4 (the `(a)` line), not 63.4. The stem (63.4–128.4) belongs to the question but for cropping, each part is cropped separately. If you need the stem included with (a), set `start_y: 63.4` for part (a).

---

## Worked Example: Page 4–5 (Q3 with Diagram)

**Page 4:**
```
y=63.4 x=49.6: 3                                    ← Q3 start
y=63.4 x=72.3: On a particular day...               ← Stem
y=108.2–130.9: table data (time, frequency)         ← Table = part of question
y=189.6 x=72.3: (a) Draw a cumulative frequency graph...
y=189.6 x=532.3: [4]                                 ← Part (a) END
y=784.5: footer                                      ← Page ends, NO dotted lines after mark
```
**Page 5:**
```
y=63.4 x=72.3: (b) Use your graph to estimate...    ← Part (b) start (no Q number at x=49.6!)
y=76.4 x=532.3: [2]                                 ← Part (b) END
y=102.4: dotted lines start
...
y=323.4 x=72.3: (c) Calculate an estimate...
y=349.4 x=532.3: [2]                                 ← Part (c) END
```

**Output:**
```json
[
  {"question": "3", "part": "a", "start_page": 4, "start_y": 189.6, "end_page": 4, "end_y": 189.6, "note": "Diagram space after mark; page ends at footer"},
  {"question": "3", "part": "b", "start_page": 5, "start_y": 63.4, "end_page": 5, "end_y": 76.4},
  {"question": "3", "part": "c", "start_page": 5, "start_y": 323.4, "end_page": 5, "end_y": 349.4}
]
```

---

## Worked Example: Page 6–7 (Q4 Continuation — My Previous Error)

**Page 6:**
```
y=63.4 x=49.6: 4                                    ← Q4 start
y=63.4 x=72.3: Suri has a bag...                    ← Stem
y=102.4 x=72.3: (a) Find the probability...
y=102.4 x=532.3: [1]                                 ← Part (a) END
y=128.4: dotted lines
...
y=349.4 x=72.3: (b) Find the probability...
y=349.4 x=532.3: [2]                                 ← Part (b) END
y=375.4: dotted lines
y=784.5: footer
```

**Page 7:**
```
y=63.4 x=72.3: Tan has a bag...                     ← NO number at x=49.6!
y=76.4 x=72.3: without replacement...               ← Continuation of Q4
y=115.4 x=72.3: (c) Draw up the probability...
y=115.4 x=532.3: [3]                                 ← Part (c) END
y=141.4: dotted lines
...
y=414.4 x=72.3: (d) Find Var(X).
y=414.4 x=532.3: [3]                                 ← Part (d) END
```

**Output (CORRECT):**
```json
[
  {"question": "4", "part": "a", "start_page": 6, "start_y": 102.4, "end_page": 6, "end_y": 102.4},
  {"question": "4", "part": "b", "start_page": 6, "start_y": 349.4, "end_page": 6, "end_y": 349.4},
  {"question": "4", "part": "c", "start_page": 7, "start_y": 115.4, "end_page": 7, "end_y": 115.4},
  {"question": "4", "part": "d", "start_page": 7, "start_y": 414.4, "end_page": 7, "end_y": 414.4}
]
```
**My error**: I saw "Tan has a bag" at y=63.4 on page 7 and no number at x=49.6, but I started Q5. **Rule 6**: No question number at x≈49.6 → continuation of Q4.

---

## Sample Input (Truncated)

```json
[
  {"page_number": 2, "lines": [
    {"text": "DFD", "x0": 229.1, "y0": 19.1, "x1": 245.6, "y1": 27.1},
    {"text": "* 0000800000002 *", "x0": 83.9, "y0": 19.3, "x1": 152.4, "y1": 27.3},
    {"text": "DO NOT WRITE IN THIS MARGIN", "x0": 581.4, "y0": 32.5, ...},
    {"text": "2", "x0": 294.8, "y0": 37.8, ...},
    {"text": ",	,", "x0": 65.6, "y0": 54.1, ...},
    {"text": "1", "x0": 49.6, "y0": 63.4, "x1": 55.6, "y1": 71.4},
    {"text": "A club has 12 members of which 7 are men...", "x0": 72.3, "y0": 63.4, ...},
    {"text": "Find the probability that a randomly chosen committee includes at least 2 men.", "x0": 72.3, "y0": 102.4, ...},
    {"text": "[4]", "x0": 532.3, "y0": 102.4, "x1": 538.3, "y1": 110.4},
    {"text": "....................................................................................", "x0": 72.3, "y0": 128.4, ...},
    ...
  ]},
  {"page_number": 3, "lines": [
    {"text": "2", "x0": 49.6, "y0": 63.4, ...},
    {"text": "(a) Find the number of different arrangements...", "x0": 72.3, "y0": 63.4, ...},
    {"text": "[3]", "x0": 532.3, "y0": 76.4, ...},
    {"text": "....................................................................................", "x0": 95.0, "y0": 102.4, ...},
    ...
  ]}
]
```

---

## Sample Output

```json
[
  {"question": "1", "part": "", "start_page": 2, "start_y": 63.4, "end_page": 2, "end_y": 102.4},
  {"question": "2", "part": "a", "start_page": 3, "start_y": 63.4, "end_page": 3, "end_y": 76.4},
  {"question": "2", "part": "b", "start_page": 3, "start_y": 427.4, "end_page": 3, "end_y": 440.4},
  {"question": "3", "part": "a", "start_page": 4, "start_y": 189.6, "end_page": 4, "end_y": 189.6, "note": "Diagram space after mark; page ends at footer"},
  {"question": "3", "part": "b", "start_page": 5, "start_y": 63.4, "end_page": 5, "end_y": 76.4},
  {"question": "3", "part": "c", "start_page": 5, "start_y": 323.4, "end_page": 5, "end_y": 349.4},
  {"question": "4", "part": "a", "start_page": 6, "start_y": 102.4, "end_page": 6, "end_y": 102.4},
  {"question": "4", "part": "b", "start_page": 6, "start_y": 349.4, "end_page": 6, "end_y": 349.4},
  {"question": "4", "part": "c", "start_page": 7, "start_y": 115.4, "end_page": 7, "end_y": 115.4},
  {"question": "4", "part": "d", "start_page": 7, "start_y": 414.4, "end_page": 7, "end_y": 414.4},
  {"question": "5", "part": "a", "start_page": 8, "start_y": 63.4, "end_page": 8, "end_y": 222.5, "note": "Tree diagram coords at y=222-508"},
  {"question": "5", "part": "b", "start_page": 8, "start_y": 662.8, "end_page": 8, "end_y": 675.8},
  {"question": "5", "part": "c", "start_page": 9, "start_y": 63.4, "end_page": 9, "end_y": 89.4},
  {"question": "5", "part": "d", "start_page": 9, "start_y": 414.4, "end_page": 9, "end_y": 453.4},
  {"question": "6", "part": "a", "start_page": 10, "start_y": 63.4, "end_page": 10, "end_y": 115.4},
  {"question": "6", "part": "b", "start_page": 11, "start_y": 103.3, "end_page": 11, "end_y": 129.3},
  {"question": "6", "part": "c", "start_page": 11, "start_y": 532.4, "end_page": 11, "end_y": 558.4}
]
```

---

## Quick Checklist for the Agent

- [ ] Scan pages in order
- [ ] Find question numbers at x≈49.6
- [ ] For each question, extract ALL parts before moving to next question
- [ ] Part end = mark `[n]` at x≈532.3 (NOT dotted lines)
- [ ] No question number at x≈49.6 on new page → continuation of previous question
- [ ] Diagram mentioned + mark present → end at mark, ignore diagram gap
- [ ] Skip footers, headers, "Additional page", "BLANK PAGE", copyright pages
- [ ] Output JSON array only, no extra text