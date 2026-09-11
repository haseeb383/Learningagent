# Agent Instructions: Extract Question Coordinates from Cambridge Past Paper Line Data

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

---

## Paper Type Detection

**Before parsing, determine paper type from the first 3 content pages:**

| Signal | Structured (9709) | MCQ (9702) |
|--------|-------------------|------------|
| Mark boxes `[3]`, `[4]` at x≈532.3 | **YES** | NO |
| Choices A/B/C/D at x≈70.9 | NO | **YES** |
| Part labels `(a)`, `(b)` at x≈72.3 | **YES** | NO |
| Question numbers at x≈49.6 | **YES** | **YES** |

**If mark boxes at x≈532.3 exist → Structured parser. Else → MCQ parser.**

---

## COMMON SIGNALS (Both Paper Types)

| Element | x-range | Meaning |
|---------|---------|---------|
| Question number | 48.0–51.0 | **Question start** |
| Page footer | any, y > 780 | "Cambridge University Press", "PapaCambridge", "Trace ID" |
| "Turn over" | ~493, y ≈ 781 | Page continues |
| "Additional page" | ~260, y ≈ 63 | Blank answer page — ignore |
| "BLANK PAGE" | ~260, y ≈ 63 | Ignore |
| Copyright/acknowledgement | y > 680 on last pages | Ignore |

**Skip pages containing:** "Additional page", "BLANK PAGE", "Permission to reproduce", "Acknowledgements Booklet", "Cambridge International Education"

---

## STRUCTURED PAPER PARSER (9709/52, 9709/62, etc.)

### Visual Signals

| Element | x-range | y-pattern | Meaning |
|---------|---------|-----------|---------|
| Part label `(a)` `(b)` `(c)` | 71.0–73.0 | indented | **Part start** |
| Sub-part `(i)` `(ii)` | 94.0–96.0 | more indented | **Sub-part start** |
| Mark `[3]` `[4]` `[5]` | 530.0–535.0 | right margin | **Part end** |
| Dotted lines `..................` | 94.0–96.0 | regular ~26pt | **Answer space** — NOT part of question |
| Question stem | 71.0–75.0 | after question number | Question intro text |

### Core Rules

#### 1. Question Start
- Number at `x ≈ 49.6` (e.g., "1", "2", "3"...)
- `question_start_y` = y of this number
- Stem text follows at `x ≈ 72.3` (this is PART OF THE QUESTION)

#### 2. Part Start — CRITICAL: STEM INCLUSION RULE
- Pattern: `(a)`, `(b)`, `(c)`, `(i)`, `(ii)`, `(a)(i)` at `x ≈ 72.3` or `95.0`
- **FIRST PART of a question**: `start_y` = `question_start_y` (includes stem)
- **Subsequent parts**: `start_y` = y of the part label
- **Reason**: The stem (text between question number and first part) contains essential context (definitions, data, diagrams) that belongs to the first part's crop.

#### 2a. How to Implement
```
When you find a question number at x≈49.6:
  1. Record question_start_y = that line's y0
  2. Scan forward for the FIRST part label (a)/(b)/(c)...
  3. For that FIRST part: start_y = question_start_y
  4. For each subsequent part: start_y = part label's y0
```

#### 3. Part End (Critical)
- **Primary signal**: Mark box `[n]` at `x ≈ 532.3` on same line as part label or last line of question text
- **End y** = y of the mark `[n]` line
- **Immediately after mark**: dotted lines begin → answer space → **STOP**
- **Do NOT include dotted lines** in the crop

#### 4. Diagrams / Graphs / Large Gaps — CRITICAL: INCLUDE GRAPH SPACE
When a part mentions a diagram/graph (e.g., "Draw a cumulative frequency graph", "Complete the tree diagram", "Draw the graph of..."):
- The mark `[n]` appears **before** the diagram/graph space
- **Two cases — handle differently:**

**Case A: Explicit diagram in question paper (tree diagram, circuit, geometry figure)**
- Diagram elements have coordinates (labels, lines, axes at specific x/y)
- **End y = bottom of diagram elements** (max y of diagram-related lines)
- Example: Tree diagram at y=222–508 → end_y = 508

**Case B: "Draw a graph" — blank graph paper/axes provided for student**
- After mark `[n]`, large blank space to page footer (no text, no dotted lines, no diagram elements)
- **End y = page footer y (or next question start on same page)**
- **INCLUDE the blank graph space** — it's part of the question paper
- Example: Mark at y=189.6, footer at y=784.5 → end_y = 784.5

**How to distinguish:**
- Scan lines after mark `[n]` up to page end/next question
- If lines contain diagram keywords ("diagram", "graph", "axes", "grid", "curve") OR coordinate clusters at varied x → Case A
- If only footer/copyright lines → Case B (blank graph space)

**Rule: When in doubt for "Draw..." questions, extend to page footer.**

#### 5. Multi-Page Questions
- A question/part can span pages
- If a part starts on page N and the mark `[n]` is on page N+1:
  - `start_page` = N, `start_y` = part label y on page N
  - `end_page` = N+1, `end_y` = mark `[n]` y on page N+1
- **Middle pages**: full page content belongs to the question
- **Check**: next page should NOT have a new question number at x≈49.6

#### 6. New Question vs Continuation (Critical)
**Before starting a new question, verify:**
- Is there a number at `x ≈ 49.6` on the current page?
- **YES** → New question. Close previous question.
- **NO** → Continuation of previous question. Keep looking for its parts.
- **Example**: Page 7 has parts (c)(d) at x≈72.3 but NO number at x≈49.6. Previous page (6) ended with Q4 part (b). These are Q4(c)(d), not Q5.

#### 6a. SEQUENTIAL ORDER ENFORCEMENT — MANDATORY
- Questions MUST appear in numerical order: 1, 2, 3, 4...
- **If you reach a question number N but have not output question N-1 → ERROR**
- **Do NOT skip questions.** If Q1 is missing from the data, stop and report:
  ```
  ERROR: Missing question 1. Found question 2 at page 3, y=63.4 but no question 1 detected.
  Possible causes: Page 2 is data/formulae (skip), or question 1 starts on page 1 (cover page).
  ```
- **Verification**: After parsing, check `questions = sorted(set(q["question"] for q in results))`. Must be `[1, 2, 3, ...]` with no gaps.

#### 7. Process Order: Question by Question
```
For each question in sequence:
  1. Find question number at x≈49.6 → record question_start_y
  2. Scan forward to find FIRST part label (a)/(b)/(c)...
  3. For FIRST part: start_y = question_start_y (INCLUDES STEM)
  4. For each subsequent part: start_y = part label's y0
  5. Find mark [n] at x≈532.3 for each part → end_y
  6. Record part: {question, part, start_page, start_y, end_page, end_y}
  7. If next part label found before new question number → continue
  8. If new question number at x≈49.6 found → STOP, go to step 1 for next question
  9. If page ends without new question number → check next page for continuation
```
**Do not jump ahead.** Finish extracting all parts of Q1 before looking for Q2.

**VERIFICATION**: Before outputting, check that every question's first part has start_y = question number's y0. If not, fix it.

#### 8. Single-Part Questions
- No `(a)` label — the question number line IS the start
- `start_y` = question number's y0 (includes stem)
- Stem text at x≈72.3
- Mark `[n]` at x≈532.3 ends the question
- Output `part: ""`

#### 9. Output Structure
```json
[
  {"question": "1", "part": "a", "start_page": 2, "start_y": 128.4, "end_page": 2, "end_y": 128.4},
  {"question": "1", "part": "b", "start_page": 2, "start_y": 453.4, "end_page": 2, "end_y": 466.4},
  {"question": "2", "part": "a", "start_page": 3, "start_y": 63.4, "end_page": 3, "end_y": 76.4},
  ...
]
```
- `part`: "a", "b", "c", "a(i)", "a(ii)", "" (for single-part)
- `start_y`/`end_y`: float, one decimal
- Include `note` field only for diagram gaps or anomalies

---

## MCQ PAPER PARSER (9702/12, 9702/22, etc.)

### Visual Signals

| Element | x-range | Meaning |
|---------|---------|---------|
| Question number | 48.0–51.0 | **Question start** |
| Question text | 70.0–72.0 | Stem |
| Choice label A/B/C/D | 70.0–72.0 | Choice start |
| Choice text | 90.0–100.0, 168.0–175.0, 267.0–275.0, 365.0–395.0 | Choice content |
| Diagrams | scattered | Part of question — include in crop |

### MCQ Rules

#### 1. Question Start
- Number at `x ≈ 49.6` (e.g., "1", "2", ... "40")
- `start_y` = y of this number
- Question text follows at `x ≈ 70.9`

#### 2. Question End
- **Last choice is D** — question ends at the **D choice line**
- D label at `x ≈ 70.9`, D text at `x ≈ 389.8` (or 92.2 for single-column)
- `end_y` = y of the D choice line (use the rightmost D text y if split)
- Next question starts at next number at `x ≈ 49.6`

#### 3. Multiple Questions Per Page
- Typical: 4–6 questions per page
- Each question: number → stem → A → B → C → D
- No blank lines between questions

#### 4. Diagrams in MCQs
- Diagrams appear between stem and choices, or alongside choices
- Coordinates are scattered (labels at various x/y)
- **Include diagram in crop**: `end_y` = D choice y (diagram is before choices)
- If diagram extends below D choice (rare), extend to diagram bottom

#### 5. Page 2 = Data/Formulae (9702)
- Page 2 contains constants, formulae — **SKIP entirely**
- Detect: "Data", "Formulae", "uniformly accelerated motion", "hydrostatic pressure" in first 10 lines

#### 6. Output Structure
```json
[
  {"question": "1", "part": "", "start_page": 3, "start_y": 71.4, "end_page": 3, "end_y": 99.4},
  {"question": "2", "part": "", "start_page": 3, "start_y": 137.4, "end_page": 3, "end_y": 226.0},
  ...
]
```
- All MCQ questions have `part: ""`
- 40 questions for 9702 Paper 1

---

## WORKED EXAMPLES

### Structured: Q1 (9709/62, Page 2)
```
y=63.4 x=49.6: 1                                    ← Question start (question_start_y = 63.4)
y=63.4 x=72.3: The heights, H centimetres...        ← Stem (ESSENTIAL — included in part a)
y=128.4 x=72.3: (a) Calculate unbiased estimates...  ← Part (a) label
y=128.4 x=532.3: [3]                                 ← Part (a) END
y=154.4 x=95.0: ....................................  ← Answer space → STOP
y=427.4 x=72.3: It is now given that...              ← Part (b) start
y=453.4 x=72.3: (b) Stating a necessary assumption...
y=466.4 x=532.3: [4]                                 ← Part (b) END
y=492.4 x=95.0: ....................................  ← STOP
```
**Output — NOTE: part (a) starts at 63.4 (question number), NOT 128.4:**
```json
[
  {"question": "1", "part": "a", "start_page": 2, "start_y": 63.4, "end_page": 2, "end_y": 128.4},
  {"question": "1", "part": "b", "start_page": 2, "start_y": 453.4, "end_page": 2, "end_y": 466.4}
]
```

### Structured: Q3 with Diagram (9709/52, Pages 4–5) — Case B: "Draw a graph"
```
Page 4:
y=63.4 x=49.6: 3                                    ← Q3 start (question_start_y = 63.4)
y=63.4 x=72.3: On a particular day...               ← Stem + table (ESSENTIAL)
y=189.6 x=72.3: (a) Draw a cumulative frequency graph...
y=189.6 x=532.3: [4]                                 ← Part (a) mark
y=784.5: footer                                      ← Page ends, NO dotted lines, NO diagram elements

Page 5:
y=63.4 x=72.3: (b) Use your graph to estimate...    ← Part (b) start (NO Q number!)
y=76.4 x=532.3: [2]                                 ← Part (b) END
y=323.4 x=72.3: (c) Calculate an estimate...
y=349.4 x=532.3: [2]                                 ← Part (c) END
```
**Analysis**: Part (a) says "Draw a cumulative frequency graph". After mark [4], only footer lines exist → **Case B (blank graph space)**. Extend to page footer.
**Output — part (a) ends at footer (784.5), includes blank graph space:**
```json
[
  {"question": "3", "part": "a", "start_page": 4, "start_y": 63.4, "end_page": 4, "end_y": 784.5, "note": "Includes stem + table; 'Draw graph' → blank graph space to footer"},
  {"question": "3", "part": "b", "start_page": 5, "start_y": 63.4, "end_page": 5, "end_y": 76.4},
  {"question": "3", "part": "c", "start_page": 5, "start_y": 323.4, "end_page": 5, "end_y": 349.4}
]
```

### Structured: Q6 with Tree Diagram (9709/52, Pages 8–9) — Case A: Explicit diagram
```
Page 8:
y=63.4 x=49.6: 6                                    ← Q6 start (question_start_y = 63.4)
y=63.4 x=72.3: Drivers who wish to obtain...        ← Stem
y=193.4 x=72.3: (a) Complete the tree diagram...
y=193.4 x=532.3: [2]                                 ← Part (a) mark
y=222.5–508: diagram elements (labels "Skills", "Theory", "Pass", "Fail", probabilities at various x/y)
y=662.8 x=72.3: (b) Show that the probability...
y=675.8 x=532.3: [1]                                 ← Part (b) END

Page 9:
y=63.4 x=72.3: (c) Find the probability...          ← Part (c) start (NO Q number!)
y=89.4 x=532.3: [2]                                 ← Part (c) END
y=414.4 x=72.3: (d) Find the probability...
y=453.4 x=532.3: [3]                                 ← Part (d) END
```
**Analysis**: Part (a) says "Complete the tree diagram". After mark [2], diagram elements exist at y=222–508 → **Case A (explicit diagram)**. End at diagram bottom (508).
**Output:**
```json
[
  {"question": "6", "part": "a", "start_page": 8, "start_y": 63.4, "end_page": 8, "end_y": 508.0, "note": "Includes stem + explicit tree diagram (y=222-508)"},
  {"question": "6", "part": "b", "start_page": 8, "start_y": 662.8, "end_page": 8, "end_y": 675.8},
  {"question": "6", "part": "c", "start_page": 9, "start_y": 63.4, "end_page": 9, "end_y": 89.4},
  {"question": "6", "part": "d", "start_page": 9, "start_y": 414.4, "end_page": 9, "end_y": 453.4}
]
```

### Structured: Continuation Detection (9709/52, Pages 6–7)
```
Page 6:
y=63.4 x=49.6: 4                                    ← Q4 start (question_start_y = 63.4)
y=63.4 x=72.3: Suri has a bag...                    ← Stem
y=102.4 x=72.3: (a) Find the probability...
y=102.4 x=532.3: [1]                                 ← Part (a) END
y=349.4 x=72.3: (b) Find the probability...
y=349.4 x=532.3: [2]                                 ← Part (b) END

Page 7:
y=63.4 x=72.3: Tan has a bag...                     ← NO number at x=49.6! → Continuation of Q4
y=115.4 x=72.3: (c) Draw up the probability...
y=115.4 x=532.3: [3]                                 ← Part (c) END
y=414.4 x=72.3: (d) Find Var(X).
y=414.4 x=532.3: [3]                                 ← Part (d) END
```
**Output (CORRECT — part (a) starts at question_start_y=63.4, includes stem):**
```json
[
  {"question": "4", "part": "a", "start_page": 6, "start_y": 63.4, "end_page": 6, "end_y": 102.4},
  {"question": "4", "part": "b", "start_page": 6, "start_y": 349.4, "end_page": 6, "end_y": 349.4},
  {"question": "4", "part": "c", "start_page": 7, "start_y": 115.4, "end_page": 7, "end_y": 115.4},
  {"question": "4", "part": "d", "start_page": 7, "start_y": 414.4, "end_page": 7, "end_y": 414.4}
]
```

### MCQ: Questions 1–5 (9702/12, Page 3)
```
y=71.4 x=49.6: 1                                    ← Q1 start
y=71.4 x=70.8: What is the value of the ratio...
y=98.1 x=70.9: A                                    ← Choice A
y=98.1 x=92.2: 10?12                                ← A text
y=98.1 x=191.3: 10?6                                ← B text
y=98.1 x=290.5: 109                                 ← C text
y=98.1 x=389.8: 1012                                ← D text
y=99.4 x=70.9: D                                    ← D label (END of Q1)

y=137.4 x=49.6: 2                                   ← Q2 start
y=137.4 x=70.8: What could reduce systematic errors?
y=161.0 x=70.9: A
y=226.0 x=70.9: D                                   ← D label (END of Q2)
```
**Output:**
```json
[
  {"question": "1", "part": "", "start_page": 3, "start_y": 71.4, "end_page": 3, "end_y": 99.4},
  {"question": "2", "part": "", "start_page": 3, "start_y": 137.4, "end_page": 3, "end_y": 226.0},
  {"question": "3", "part": "", "start_page": 3, "start_y": 264.0, "end_page": 3, "end_y": 385.2},
  {"question": "4", "part": "", "start_page": 3, "start_y": 425.0, "end_page": 3, "end_y": 539.1},
  {"question": "5", "part": "", "start_page": 3, "start_y": 576.9, "end_page": 3, "end_y": 676.5}
]
```

---

## SAMPLE INPUT (Truncated)

### Structured Paper
```json
[
  {"page_number": 2, "lines": [
    {"text": "1", "x0": 49.6, "y0": 63.4, "x1": 55.6, "y1": 71.4},
    {"text": "The heights, H centimetres...", "x0": 72.3, "y0": 63.4, ...},
    {"text": "(a) Calculate unbiased estimates...", "x0": 72.3, "y0": 128.4, ...},
    {"text": "[3]", "x0": 532.3, "y0": 128.4, "x1": 538.3, "y1": 136.4},
    {"text": "....................................................................................", "x0": 95.0, "y0": 154.4, ...},
    ...
  ]}
]
```

### MCQ Paper
```json
[
  {"page_number": 3, "lines": [
    {"text": "1", "x0": 49.6, "y0": 71.4, "x1": 55.6, "y1": 79.4},
    {"text": "What is the value of the ratio", "x0": 70.8, "y0": 71.4, ...},
    {"text": "A", "x0": 70.9, "y0": 99.4, ...},
    {"text": "10?12", "x0": 92.2, "y0": 98.1, ...},
    {"text": "D", "x0": 70.9, "y0": 99.4, ...},
    {"text": "1012", "x0": 389.8, "y0": 98.1, ...},
    {"text": "2", "x0": 49.6, "y0": 137.4, ...},
    ...
  ]}
]
```

---

## SAMPLE OUTPUT

### Structured (9709/52)
```json
[
  {"question": "1", "part": "a", "start_page": 2, "start_y": 63.4, "end_page": 2, "end_y": 102.4},
  {"question": "1", "part": "b", "start_page": 2, "start_y": 453.4, "end_page": 2, "end_y": 466.4},
  {"question": "2", "part": "a", "start_page": 3, "start_y": 63.4, "end_page": 3, "end_y": 76.4},
  {"question": "2", "part": "b", "start_page": 3, "start_y": 427.4, "end_page": 3, "end_y": 440.4},
  {"question": "3", "part": "a", "start_page": 4, "start_y": 63.4, "end_page": 4, "end_y": 784.5, "note": "Includes stem + table; 'Draw graph' → blank graph space to footer"},
  {"question": "3", "part": "b", "start_page": 5, "start_y": 63.4, "end_page": 5, "end_y": 76.4},
  {"question": "3", "part": "c", "start_page": 5, "start_y": 323.4, "end_page": 5, "end_y": 349.4},
  {"question": "4", "part": "a", "start_page": 6, "start_y": 63.4, "end_page": 6, "end_y": 102.4},
  {"question": "4", "part": "b", "start_page": 6, "start_y": 349.4, "end_page": 6, "end_y": 349.4},
  {"question": "4", "part": "c", "start_page": 7, "start_y": 115.4, "end_page": 7, "end_y": 115.4},
  {"question": "4", "part": "d", "start_page": 7, "start_y": 414.4, "end_page": 7, "end_y": 414.4},
  {"question": "5", "part": "a", "start_page": 8, "start_y": 63.4, "end_page": 8, "end_y": 508.0, "note": "Includes stem + explicit tree diagram (y=222-508)"},
  {"question": "5", "part": "b", "start_page": 8, "start_y": 662.8, "end_page": 8, "end_y": 675.8},
  {"question": "5", "part": "c", "start_page": 9, "start_y": 63.4, "end_page": 9, "end_y": 89.4},
  {"question": "5", "part": "d", "start_page": 9, "start_y": 414.4, "end_page": 9, "end_y": 453.4}
]
```

### MCQ (9702/12)
```json
[
  {"question": "1", "part": "", "start_page": 3, "start_y": 71.4, "end_page": 3, "end_y": 99.4},
  {"question": "2", "part": "", "start_page": 3, "start_y": 137.4, "end_page": 3, "end_y": 226.0},
  {"question": "3", "part": "", "start_page": 3, "start_y": 264.0, "end_page": 3, "end_y": 385.2},
  {"question": "4", "part": "", "start_page": 3, "start_y": 425.0, "end_page": 3, "end_y": 539.1},
  {"question": "5", "part": "", "start_page": 3, "start_y": 576.9, "end_page": 3, "end_y": 676.5},
  {"question": "6", "part": "", "start_page": 4, "start_y": 62.5, "end_page": 4, "end_y": 295.3},
  {"question": "7", "part": "", "start_page": 4, "start_y": 333.2, "end_page": 4, "end_y": 558.1},
  {"question": "8", "part": "", "start_page": 5, "start_y": 62.5, "end_page": 5, "end_y": 386.2},
  {"question": "9", "part": "", "start_page": 5, "start_y": 424.2, "end_page": 5, "end_y": 550.9},
  {"question": "10", "part": "", "start_page": 6, "start_y": 62.5, "end_page": 6, "end_y": 363.8},
  {"question": "11", "part": "", "start_page": 6, "start_y": 410.1, "end_page": 6, "end_y": 609.0},
  {"question": "12", "part": "", "start_page": 7, "start_y": 61.1, "end_page": 7, "end_y": 265.3},
  {"question": "13", "part": "", "start_page": 7, "start_y": 303.2, "end_page": 7, "end_y": 589.4},
  {"question": "14", "part": "", "start_page": 8, "start_y": 62.5, "end_page": 8, "end_y": 463.9},
  {"question": "15", "part": "", "start_page": 8, "start_y": 501.8, "end_page": 8, "end_y": 626.3},
  {"question": "16", "part": "", "start_page": 9, "start_y": 62.5, "end_page": 9, "end_y": 287.4},
  {"question": "17", "part": "", "start_page": 9, "start_y": 325.3, "end_page": 9, "end_y": 566.7},
  {"question": "18", "part": "", "start_page": 9, "start_y": 604.8, "end_page": 9, "end_y": 683.8},
  {"question": "19", "part": "", "start_page": 10, "start_y": 61.1, "end_page": 10, "end_y": 136.6},
  {"question": "20", "part": "", "start_page": 10, "start_y": 174.7, "end_page": 10, "end_y": 390.8},
  {"question": "21", "part": "", "start_page": 10, "start_y": 437.1, "end_page": 10, "end_y": 567.2},
  {"question": "22", "part": "", "start_page": 10, "start_y": 607.3, "end_page": 10, "end_y": 684.4},
  {"question": "23", "part": "", "start_page": 11, "start_y": 62.5, "end_page": 11, "end_y": 458.0},
  {"question": "24", "part": "", "start_page": 11, "start_y": 495.4, "end_page": 11, "end_y": 610.6},
  {"question": "25", "part": "", "start_page": 12, "start_y": 62.5, "end_page": 12, "end_y": 319.5},
  {"question": "26", "part": "", "start_page": 12, "start_y": 357.6, "end_page": 12, "end_y": 446.1},
  {"question": "27", "part": "", "start_page": 13, "start_y": 62.1, "end_page": 13, "end_y": 364.8},
  {"question": "28", "part": "", "start_page": 13, "start_y": 402.7, "end_page": 13, "end_y": 705.5},
  {"question": "29", "part": "", "start_page": 14, "start_y": 62.5, "end_page": 14, "end_y": 303.6},
  {"question": "30", "part": "", "start_page": 14, "start_y": 435.3, "end_page": 14, "end_y": 561.9},
  {"question": "31", "part": "", "start_page": 14, "start_y": 599.8, "end_page": 14, "end_y": 700.2},
  {"question": "32", "part": "", "start_page": 15, "start_y": 62.1, "end_page": 15, "end_y": 197.1},
  {"question": "33", "part": "", "start_page": 15, "start_y": 453.4, "end_page": 15, "end_y": 542.0},
  {"question": "34", "part": "", "start_page": 16, "start_y": 62.5, "end_page": 16, "end_y": 342.4},
  {"question": "35", "part": "", "start_page": 16, "start_y": 390.9, "end_page": 16, "end_y": 558.9},
  {"question": "36", "part": "", "start_page": 17, "start_y": 62.5, "end_page": 17, "end_y": 287.4},
  {"question": "37", "part": "", "start_page": 17, "start_y": 325.3, "end_page": 17, "end_y": 557.6},
  {"question": "38", "part": "", "start_page": 17, "start_y": 595.4, "end_page": 17, "end_y": 762.6},
  {"question": "39", "part": "", "start_page": 18, "start_y": 62.5, "end_page": 18, "end_y": 230.4},
  {"question": "40", "part": "", "start_page": 18, "start_y": 273.3, "end_page": 18, "end_y": 417.0}
]
```

---

## QUICK CHECKLIST FOR THE AGENT

- [ ] Detect paper type: mark boxes at x≈532.3 → Structured; choices A-D at x≈70.9 → MCQ
- [ ] Skip page 2 for MCQ (Data/Formulae)
- [ ] Skip footer/copyright/blank pages
- [ ] **Structured**: Find question numbers at x≈49.6, record question_start_y
- [ ] **Structured**: FIRST part start_y = question_start_y (INCLUDES STEM) — CRITICAL
- [ ] **Structured**: Subsequent parts start_y = part label y0
- [ ] **Structured**: Graph/Diagram handling:
  - "Draw graph" + blank space after mark → Case B: end_y = page footer
  - Explicit diagram elements after mark → Case A: end_y = diagram bottom
- [ ] **Structured**: All parts end at mark [n] at x≈532.3 (before dotted lines)
- [ ] **Structured**: No question number at x≈49.6 on new page → continuation of previous question
- [ ] **SEQUENTIAL ORDER**: Questions must be 1,2,3... with NO gaps. If Q1 missing → ERROR with reason
- [ ] **MCQ**: Find question numbers at x≈49.6, end at D choice (x≈70.9 label, x≈389.8 text)
- [ ] **MCQ**: Multiple questions per page — process sequentially
- [ ] **VERIFY**: Every question's first part starts at the question number's y-coordinate
- [ ] **VERIFY**: Question numbers are sequential with no gaps
- [ ] Output JSON array only, no extra text