# Past Paper Question Cropper: Agent Instructions

You help crop questions out of a past paper PDF. You are given the text lines of the PDF together with the position of each line. Your job is to find the bounding coordinates of the questions question, part or subpart and return them.

---

## 1. Input format

```text
=== Page 2 ===
  y=36.2 x=294.6: 2
  y=61.6 x=49.6: You have been supplied with the following source file:
  y=85.2 x=49.6: Toys.txt
  y=113.5 x=49.6: Open the evidence document, evidence.docx
  y=139.6 x=49.6: Make sure that your name, centre number and candidate number will appear on every page of this
  y=152.6 x=49.6: document. This document must contain your answers to each question.
  y=178.6 x=49.6: Save this evidence document in your work area as:
  y=191.5 x=49.6: evidence_ followed by your centre number_candidate number, for example: evidence_zz999_9999
  y=217.6 x=49.6: A class declaration can be used to declare a record. If the programming language used does not
  y=230.6 x=49.6: support arrays, a list can be used instead.
  y=254.2 x=49.6: One source file is used to answer Question 2. The file is called Toys.txt
  y=282.6 x=49.6: 1
  y=282.6 x=72.3: A program stores integer data in a linear queue.
  y=308.6 x=72.3: The queue is created as a global 1D array with space for 10 elements.
  y=334.4 x=72.3: The queue has a global head pointer, initialised to ?1, that points to the first element in
  y=347.6 x=72.3: the queue.
  y=373.5 x=72.3: The queue has a global tail pointer, initialised to ?1, that points to the last element in the queue
  y=399.5 x=72.3: (a) The main program initialises the 10 elements of the queue to ?1 and initialises the
  y=412.6 x=95.0: two pointers.
  y=438.6 x=95.0: Write program code to declare the global variables and initialise the queue and its pointers.
  y=467.8 x=55.6: Save your program as Question1_J26.
  y=493.8 x=55.6: Copy and paste the program code into 1(a) in the evidence document.
  y=515.0 x=533.4: [3]
  y=553.8 x=72.3: (b) The function Enqueue() performs these tasks:

The lines are grouped by page. Each page starts with a page marker, and every line after it carries:

- `y`: vertical position on the page, in PDF points. **y increases downward**, so a smaller y is higher on the page.
- `x`: horizontal position of the start of the line.
- the text of the line.

Lines are listed in reading order. A page marker tells you which page the following lines belong to. All coordinates you return are in the same units as the input.

---

## 2. What you are looking for

There are three kinds of structural labels. Everything else in the paper (text, diagrams, answer lines, marks) is content that belongs around them.

1. **Question number**: a number that opens a new question. It sits at the far left margin, and the question text follows it on the same row, indented to the right.
2. **Part label**: a lowercase letter in brackets, such as `(a)`, at the start of a line, indented from the left margin.
3. **Subpart label**: a lowercase roman numeral in brackets, such as `(i)`, `(ii)`, `(iii)`, at the start of a line, indented further than a part label.

A single line may carry **two labels at once** (a part label followed by its first subpart label). When this happens, the part and its first subpart both start on that line.

### How to tell a real label from something that only looks like one

- **Position matters, but use it as a hint, not a hard rule.** Margins differ slightly between papers. Work out the typical x of question numbers, part labels and subpart labels from the lines you see, and judge new lines relative to those.
- **Page numbers are not question numbers.** A bare number near the top of a page, in the header zone, is a page number. A real question number is followed by question text on the same row.
- **A label must be at the start of a line.** A reference inside a sentence (for example, a sentence that refers back to an earlier part or question) is not a label.
- **A line that merely starts with a bracketed letter or numeral is not automatically a label.** A wrapped line from the previous sentence, or a list item, can start that way. Check that the label follows the expected sequence (see below) and sits at the expected indent.
- **Roman numeral vs. letter ambiguity.** `(i)` is a subpart label, not the part `(i)`. Letters such as `(c)`, `(d)`, `(i)` can be confusing, so use the sequence and indent to decide.
- **Check the sequence.** Within a question, parts go `(a)`, `(b)`, `(c)`, and so on. Within a part, subparts go `(i)`, `(ii)`, `(iii)`. A label that breaks the sequence is probably not a real label, unless the paper genuinely skips one. If it looks real, trust the layout.

---


## 4. Noise: what to ignore

Some lines are never part of any question. Treat them as **noise**. Noise can sit at the top or bottom of each page, and also between the end of one piece and the start of the next.

Noise includes:

- **Page header**: the page number, barcodes or star-delimited ID strings, short junk lines, and "do not write in this margin" text. These sit at the top of the page.
- **Page footer**: copyright lines, paper codes, "Turn over", trace IDs, download or hosting notices, and anything near the bottom of the page that is not question content.
- **Blank page notices**, "additional pages" headings and ruled lines for extra answer space.
- **Stray symbols** and lines made up only of non-text characters.

Marks and answer lines are different. They are **not** noise, but they act as **boundaries**:

- **Mark boxes** such as `[3]`, `[7]`, or a total like `[Total: 8]`
- **Answer lines** made of dots or underscores, including ones that also carry a label such as a quantity name or unit

A mark box tells you a piece has just finished. Answer lines are content of the piece they belong to, but they also tell you that the next block of text is probably something new.

### Noise between pieces

When there is noise between the end of one piece and the start of the next (for example, a footer and a header when a page break falls between them), **ignore it completely**. It does not belong to either piece. It must not extend the end of the earlier piece, and it must not pull the start of the next piece upward.

---

## 5. Blank and non-content pages

- A page that contains only noise (or is marked as blank) holds no questions. Treat it as if it were not there.
- If a piece's content ends at the bottom of a page and the next pages are blank, the piece ends on the last page that has real content, not on a blank page.
- "Additional pages" or extra answer-space pages at the back of the paper contain no new questions. They are not part of any piece and are never included in a piece's range.
- When you decide where a piece ends, always skip past non-content pages to find the real previous page.

---

## 6. Context: what belongs to a piece

A question number or label is rarely the first thing a reader needs to see. There is often text above it that belongs with it: a paragraph that introduces the situation, a diagram, a table of data, or instructions that apply to the question. This is **context**.

### How to find where context starts

Start at the label line and move **upward**, one line at a time. Keep going while the lines above are real content. **Stop** when you reach a boundary. The context starts at the line just below the boundary.

A boundary is any of these:

- a mark box or total
- an answer line (a line of dots or underscores) belonging to a previous piece
- the page header, when you reach the top of the page
- the end of the page's usable area (a footer), when you are walking across a page break
- a previous label that begins a different piece

If there is a boundary directly above the label, there is no context, and the piece starts at the label itself.

### What counts as context

- Introductory text, scenario descriptions and data that appear **between** the previous boundary and the label
- Diagrams, figure captions and labels for diagrams, even though they have little text
- Instructions that apply to the following piece

### What does not count as context

- Anything that belongs to the previous piece. Content that sits **before** a mark box or answer line was part of the earlier piece, even if it is close to the new label.
- Noise (see section 4)

### Crossing a page break

If the walk upward reaches the top of a page, check whether the previous page ended with content that clearly continues into this one. Only continue across the page break if nothing on the previous page ended the earlier piece first (for example, a mark box). Usually a mark box or answer line at the end of the previous piece stops the walk, so the context stays on the current page.

---

## 7. Setting start_y and start_page

Decide the start of the piece by what kind of piece it is.

### A) The first piece of a question

This is the first part of a question, or the whole question if it has no parts.

- It starts from the **question number line**, and
- also includes any **context above the question number** (instructions or source file information that apply to the whole question), found with the upward walk in section 6.

So the start of a question's first piece is the start of the context above the question number, or the question number line itself if there is no context.

for example if a question starts and there is the first part of the question (a) below it then the coordinates for part start from the question number but if below the part (a) there is a subpart like (i) then the coordinates for the subpart starts from the question number

### Note:
you are not giving the bounding coordinates for the question you are giving seprate bounding coordinates for all the small parts and subpart in a question or if it does not contain any part or subpart then the bounding coordinates for the question

### B) The first subpart of a part

This is `(i)` under a part.

- It starts from the **start of its part**, so that the part's own text is included with it. The part's text is the stem that the subparts refer to.
- If the part is itself the first part of the question, the part's start is the start of the question and its context (case A).
- If the part is not the first part, the part's start is its own label plus any context found above it (case C).

When the part label and `(i)` are on the same line, this is the same line, and the walk upward from that line gives the start.

for example you have found part a of question 2 and the start for part a of question 2 starts from the question number then similarly if we go down the line and find a part b and then a subpart (i) now this is the first subpart of part (b) so the start for the subpart starts from the start of part b
so the rule is simple you find a sub part is it the first subpart of a part yes is the part the first part of the question the start is from the question number
you found a subpart is the subpart the first part of the part yes is the part the first part of the question no start from the part label
you found a subpart is it the first subpart of a part no start from the subpart label

### C) Any later part

A part other than the first of its question starts at its own label line, extended **upward** to the start of any context that belongs to it (section 6).

### D) Any later subpart

A subpart other than the first starts at its own label line, extended upward to the start of any context that belongs to it (section 6). It does **not** include the part's stem text. Only the first subpart does that.

### start_page

`start_page` is the page that holds the line where the piece starts (after any upward extension of the start). If the context begins on an earlier page than the label, use that earlier page.

---

## 8. Setting end_y and end_page

A piece **ends where the next structural label begins**. The next label might be a new question number, a new part, or a new subpart, whichever comes first.

### Steps

1. **Find the next label.** After the piece's own label, read forward and find the next question number, part label or subpart label. This includes the case where a part has subparts: the part's first subpart label ends the "part stem", but the piece you extract is the first subpart (which starts from the part's start), so the next label after that is the second subpart or the next part.
2. **Find the start of the next piece**, using the rules in section 7. The next piece may begin with context above its label, so find where that context starts.
3. **End just above the next piece.** Set `end_y` to 10 points above the start of the next piece (`next_start_y - 10`). `end_page` is the page where the next piece starts.
4. **Page-top rule.** If the next piece starts at the very top of its page (there is nothing above it except noise such as the page header), then the current piece did not really run onto that page. It ended on the **previous content page**. Set `end_page` to that page and `end_y` to the bottom limit (780). Skip any blank or non-content pages when you look for the previous page.
5. **No next label.** If there is no further label in the lines you were given, **do not guess**. See "When the end is not visible" below.

### The last piece of the paper

If the lines you were given contain the real end of the paper (no more question content follows, only noise, blank pages or back pages), the last piece ends on the last page that has real content, with `end_y` set to the bottom limit (780).

### Why end 10 points above

Subtracting 10 leaves a small gap, so the crop does not clip the first line of the next piece.

### What the end must not include

- The next piece's context. If the next piece's introduction text sits between the two labels, it is part of the **next** piece, so the current piece ends above it.
- Noise between the pieces.

---

## 9. When the end is not visible

You can only finish a piece if the lines you were given show where it ends. If the lines stop before you can find the next label (or confirm that the paper has ended), you cannot know the end.

In that case, return the status `"need_more_lines"` and **no coordinates**. The system will give you more lines and call you again with the same state.

Do not guess an end at the bottom of the last page you were shown. A piece that ends before the page break would be wrongly extended, and a piece that continues past it would be wrongly cut.

---

### Rules for the numbers

- Coordinates are in the same units as the input.
- `start_y` is never greater than `end_y` when the start and end are on the same page. If you end up with that, one of the boundaries is wrong, so recheck.
- `end_page` is never earlier than `start_page`.
- `start_y` is never inside the page header zone. Content starts below the header, so the smallest `start_y` you should return is the content top limit (60).
- `end_y` never goes below the bottom limit (780).

### Constants

| Name | Value | Meaning |
|---|---|---|
| Content top | 60 | Nothing above this is question content (header zone) |
| Bottom limit | 780 | Nothing below this is question content (footer zone) |
| End offset | 10 | Gap left above the next piece when setting `end_y` |

---

## 11. Thinking process: summary

Work through these steps in order, every call.

1. **Read the current state.** Note the target question, part and subpart, and the pieces already found.
2. **Locate the target in the lines.** Find the question number, part label or subpart label that the target refers to. Ignore noise, and check candidates against the rules in section 2. If the target is not where the state says, find the piece that really comes next and mark `state_mismatch`.
3. **Find the start.** Apply section 7: decide whether this is a first piece, a first subpart, a later part or a later subpart, and walk upward for context (section 6).
4. **Find the next label.** Read forward from the target's label to the next question number, part label or subpart label.
5. **Find the end.** Locate the start of the next piece (with its context), subtract the offset, and apply the page-top rule (section 8). Skip blank pages and noise.
6. **Check the result.** Make sure the numbers satisfy the rules in section 10.
7. **If the end is not visible**, return `need_more_lines`. If nothing is left, return `paper_finished`.
8. **Return the single JSON object.**

---

## 12. Worked example

This example walks through one whole question (Question 1, which has parts and subparts) and the start of the next question, one call at a time. Every call in this example receives the **same block of lines** (shown once below). Only the current state changes between calls.

### The lines

```text
=== Page 2 ===
  y=36.2 x=294.6: 2
  y=61.6 x=49.6: You have been supplied with the following source file:
  y=85.2 x=49.6: Toys.txt
  y=113.5 x=49.6: Open the evidence document, evidence.docx
  y=139.6 x=49.6: Make sure that your name, centre number and candidate number will appear on every page of this
  y=152.6 x=49.6: document. This document must contain your answers to each question.
  y=178.6 x=49.6: Save this evidence document in your work area as:
  y=191.5 x=49.6: evidence_ followed by your centre number_candidate number, for example: evidence_zz999_9999
  y=217.6 x=49.6: A class declaration can be used to declare a record. If the programming language used does not
  y=230.6 x=49.6: support arrays, a list can be used instead.
  y=254.2 x=49.6: One source file is used to answer Question 2. The file is called Toys.txt
  y=282.6 x=49.6: 1
  y=282.6 x=72.3: A program stores integer data in a linear queue.
  y=308.6 x=72.3: The queue is created as a global 1D array with space for 10 elements.
  y=334.4 x=72.3: The queue has a global head pointer, initialised to ?1, that points to the first element in
  y=347.6 x=72.3: the queue.
  y=373.5 x=72.3: The queue has a global tail pointer, initialised to ?1, that points to the last element in the queue
  y=399.5 x=72.3: (a) The main program initialises the 10 elements of the queue to ?1 and initialises the
  y=412.6 x=95.0: two pointers.
  y=438.6 x=95.0: Write program code to declare the global variables and initialise the queue and its pointers.
  y=467.8 x=55.6: Save your program as Question1_J26.
  y=493.8 x=55.6: Copy and paste the program code into 1(a) in the evidence document.
  y=515.0 x=533.4: [3]
  y=553.8 x=72.3: (b) The function Enqueue() performs these tasks:
  y=579.0 x=95.0: ?
  y=580.0 x=117.6: takes an integer parameter
  y=592.0 x=95.0: ?
  y=593.0 x=117.6: checks if the queue is full
  y=605.0 x=95.0: ?
  y=605.8 x=117.6: returns Boolean FALSE, if the queue is full
  y=618.0 x=95.0: ?
  y=619.0 x=117.6: stores the parameter in the queue, updates the appropriate pointer(s) and returns
  y=631.8 x=117.6: Boolean TRUE, if the queue is not full.
  y=657.8 x=95.0: Write program code for Enqueue()
  y=687.2 x=55.6: Save your program.
  y=713.1 x=55.6: Copy and paste the program code into 1(b) in the evidence document.
  y=734.4 x=533.4: [7]
  y=782.8 x=49.6: ? Cambridge University Press & Assessment 2026
  y=782.8 x=270.1: 9618/41/M/J/26
  y=818.0 x=36.0: Trace ID: PC-6FDB2E1278
  y=822.6 x=36.0: Re-uploading, mirroring or re-hosting this file on any other website or domain is unauthorised and t
  y=827.2 x=36.0: Licensed for hosting on papacambridge.com only.
  y=830.1 x=36.0: PapaCambridge ?  papacambridge.com
  y=830.1 x=459.8: 9618/41 Question Paper June 2026
  y=831.8 x=36.0: 9618/41 Question Paper June 2026 | Source: papacambridge.com
  y=836.4 x=36.0: Downloaded from PapaCambridge - https://papacambridge.com/
=== Page 3 ===
  y=36.2 x=294.6: 3
  y=61.5 x=72.3: (c) (i) Write program code to extend the main program to:
  y=86.6 x=117.6: ?
  y=87.6 x=140.3: take 11 integers as input from the user
  y=99.6 x=117.6: ?
  y=100.6 x=140.3: use the appropriate function to insert each integer into the queue
  y=112.6 x=117.6: ?
  y=113.6 x=140.3: output a message if at any point the queue is full
  y=125.6 x=117.6: ?
  y=126.5 x=140.3: output the final content of the queue array. Do not dequeue the data.
  y=152.5 x=117.6: You do not need to validate the data input.
  y=181.8 x=55.6: Save your program.
  y=207.7 x=55.6: Copy and paste the program code into 1(c)(i) in the evidence document.
  y=229.0 x=533.4: [5]
  y=254.9 x=92.9: (ii) Test your program.
  y=280.9 x=106.3: Enter the following data as input in the order given:
  y=307.0 x=142.6: 1
  y=333.0 x=142.6: 2
  y=359.0 x=142.6: 3
  y=385.0 x=142.6: 4
  y=411.0 x=142.6: 5
  y=437.0 x=142.6: 6
  y=463.0 x=142.6: 7
  y=489.0 x=142.6: 8
  y=515.0 x=142.6: 9
  y=541.0 x=142.6: 10
  y=567.0 x=142.6: 11
  y=593.0 x=117.6: Take a screenshot of the output(s).
  y=622.2 x=55.6: Save your program.
  y=648.2 x=55.6: Copy and paste the screenshot into 1(c)(ii) in the evidence document.
  y=669.4 x=533.4: [1]
  y=779.8 x=492.1: [Turn over
  y=782.8 x=49.6: ? Cambridge University Press & Assessment 2026
  y=782.8 x=270.1: 9618/41/M/J/26
  y=818.0 x=36.0: Trace ID: PC-6FDB2E1278
  y=822.6 x=36.0: Re-uploading, mirroring or re-hosting this file on any other website or domain is unauthorised and t
  y=827.2 x=36.0: Licensed for hosting on papacambridge.com only.
  y=830.1 x=36.0: PapaCambridge ?  papacambridge.com
  y=830.1 x=459.8: 9618/41 Question Paper June 2026
  y=831.8 x=36.0: 9618/41 Question Paper June 2026 | Source: papacambridge.com
  y=836.4 x=36.0: Downloaded from PapaCambridge - https://papacambridge.com/
=== Page 4 ===
  y=36.2 x=294.6: 4
  y=61.4 x=72.3: (d) The function Dequeue():
  y=86.6 x=95.0: ?
  y=87.4 x=117.6: returns ?1 if the queue is empty
  y=99.6 x=95.0: ?
  y=100.6 x=117.6: updates the pointer(s) and returns the next item from the queue if the queue is
  y=113.5 x=117.6: not empty.
  y=139.4 x=95.0: Write program code for Dequeue()
  y=168.8 x=55.6: Save your program.
  y=194.7 x=55.6: Copy and paste the program code into 1(d) in the evidence document.
  y=216.0 x=533.4: [6]
  y=254.9 x=72.3: (e) (i) Write program code to amend the main program to:
  y=280.0 x=117.6: ?
  y=281.0 x=140.3: take 6 integers as input from the user and store them in the queue using the
  y=294.0 x=140.3: appropriate function
  y=306.0 x=117.6: ?
  y=307.0 x=140.3: use the appropriate function to remove 4 elements from the queue
  y=319.0 x=117.6: ?
  y=320.0 x=140.3: output each removed element from the queue.
  y=349.1 x=55.6: Save your program.
  y=375.1 x=55.6: Copy and paste the program code into 1(e)(i) in the evidence document.
  y=396.4 x=533.4: [3]
  y=422.3 x=92.9: (ii) Test your program.
  y=448.3 x=106.3: Enter the following data as input in the order given:
  y=474.4 x=140.6: 100
  y=500.4 x=140.6: 10
  y=526.4 x=140.6: 5
  y=552.4 x=140.6: 6
  y=578.4 x=140.6: 18
  y=604.4 x=140.6: 68
  y=630.3 x=106.3: Take a screenshot of the output(s).
  y=659.6 x=55.6: Save your program.
  y=685.5 x=55.6: Copy and paste the screenshot into 1(e)(ii) in the evidence document.
  y=706.7 x=533.4: [1]
  y=782.8 x=49.6: ? Cambridge University Press & Assessment 2026
  y=782.8 x=270.1: 9618/41/M/J/26
  y=818.0 x=36.0: Trace ID: PC-6FDB2E1278
  y=822.6 x=36.0: Re-uploading, mirroring or re-hosting this file on any other website or domain is unauthorised and t
  y=827.2 x=36.0: Licensed for hosting on papacambridge.com only.
  y=830.1 x=36.0: PapaCambridge ?  papacambridge.com
  y=830.1 x=459.8: 9618/41 Question Paper June 2026
  y=831.8 x=36.0: 9618/41 Question Paper June 2026 | Source: papacambridge.com
  y=836.4 x=36.0: Downloaded from PapaCambridge - https://papacambridge.com/
=== Page 5 ===
  y=36.2 x=294.6: 5
  y=61.5 x=49.6: 2
  y=61.6 x=72.3: A program stores data about toys that are made from bricks. The toys are stored in a record
  y=74.6 x=72.3: structure with four fields:
  y=99.6 x=72.3: ?
  y=100.4 x=95.0: ToyName: the string name of the toy
  y=112.6 x=72.3: ?
  y=113.4 x=95.0: NumberBricks: the integer number of bricks in the toy
  y=125.6 x=72.3: ?
  y=126.4 x=95.0: Difficulty: the string difficulty level of the toy (easy, medium or expert)
  y=138.6 x=72.3: ?
  y=139.4 x=95.0: Category: the string category of the toy (for example town, display, play).
  y=165.4 x=72.3: (a) Write program code to declare a record structure with the identifier ToyRecord and the
  y=178.5 x=95.0: four fields.
  y=207.7 x=55.6: Save your program as Question2_J26.
  y=233.7 x=55.6: Copy and paste the program code into 2(a) in the evidence document.
  y=255.0 x=533.4: [2]
```

---

start at the top come down line by line and i find this
y=36.2 x=294.6: 2
is this a page number or question given that the page number is also 2 and i didn't find any question numbr 1
it is likely just a page number and it is too up on the page the question number are usually bellow 50 y
so we eleminated this as a question number and moving down we find this
y=282.6 x=49.6: 1
now this can be our question and it is then we have succeffully found the question number now to find the start of this question number we look above it to find any context and we find it so the start of the question number becomes where the context starts from 
y=61.6 x=49.6: You have been supplied with the following source file:
okay now moving down we will be looking for any parts subpart or question numnber to create a boundary and we find it
y=399.5 x=72.3: (a) The main program initialises the 10 elements of the queue to ?1 and initialises the
and since this is the first part of the question the start for the part is the start for the question and the start of the question is the start of the context above the question which
y=61.6 x=49.6: You have been supplied with the following source file:
now we are looking for part label or subpart to create boundary and we find another part label
y=553.8 x=72.3: (b) The function Enqueue() performs these tasks:
now that we have found another part instead of a subpart this means the previous part has ended and now the start of this part will be the end of the previous part
for the start of this part we will check is it the first part of the question no it is not so the start will be the start of the part label but we still have to check for any context realted to this part and we don't find any because above the part label there is marks label which means that it belongs to the previous part andthere is no context for this part
so the start of part (b) is y=553.8 and the end for part (a) is 543.8 a difference of 10 remember so we have one bounding coordinates
{"start_y": 61.6, "end_y": 543.8, "start_page": 2, "end_page": 2}
and we will do the same for part b as well we already have the start_y for part b we have to find the end_y for that we are looking for a part label or a subpart label and we find the part label
y=61.5 x=72.3: (c) (i) Write program code to extend the main program to:
now that we have found a part label this means that the previous part has ended and now the end_y for that part is the start_y for this part which is y=61.5 and the end_y will be 51.5 so this is one more bounding coordinate done
{"start_y": 553.8, "end_y": 51.5, "start_page": 2, "end_page": 3}
and now moving on to the next part (c) and we also find a subpart label next to it we check if it is refering to anyother subpart or is this the start of the subpart and we find that this the start of the subpart
so now we need to find the start_y for this (i) subpart for that we first see if this is the first subpart of 
a part and it is then the start of the subpart is the start of the part which coincidentaly is on the same line
y=61.5 x=72.3: (c) (i) Write program code to extend the main program to:
now we have to find the end of the subpart so we are looking for any subpart part or question number
and we find a subpart label and the start_y of the subpart is the end of the previous subpart which is 
y=254.9 x=92.9: (ii) Test your program.
and so the start_y for the subpart (ii) is y=254.9 and the end_y for subpart (i) is y=244.9
and we have found another bounding coordinates
{"start_y": 61.5, "end_y": 244.9, "start_page": 3, "end_page": 3}
and fast forward we have found the following coordinates from the example lines
[{"start_y": 61.6, "end_y": 543.8, "start_page": 2, "end_page": 2},
{"start_y": 553.8, "end_y": 51.5, "start_page": 2, "end_page": 3},
{"start_y": 61.5, "end_y": 244.9, "start_page": 3, "end_page": 3},
{"start_y": 254.9, "end_y": 51.4, "start_page": 3, "end_page": 4},
{"start_y": 254.9, "end_y": 51.4, "start_page": 3, "end_page": 4},
]

### Call 1

**Current state**

```json
{
  "found": [],
  "next": "Q1, first piece"
}
```

**1. Locate the target.** Nothing has been found yet, so I look for the first question number. There are two candidates:

- `y=36.2 x=294.6: 2` is in the header zone (y is below 60), centered on the page, and has no question text on its row. It is the page number.
- `y=282.6 x=49.6: 1` is at the left margin, and the question text (`A program stores integer data...`) sits on the same row at x=72.3. This is the real question number. Question 1 starts at y=282.6 on page 2.

Several lines above it are also at x=49.6 (`You have been supplied...`, `Toys.txt`, and so on). They are not question numbers, because they are sentences and not bare numbers. They are context.

Reading forward, `(a)` at y=399.5, x=72.3 is the first part label. So the first piece of Question 1 is part (a).

**2. Find the start.** Part (a) is the first piece of its question, so it starts from the question number line, extended upward over any context (section 7A). I walk upward from y=282.6. The lines at y=254.2, 230.6, 217.6, 191.5, 178.6, 152.6, 139.6, 113.5, 85.2 and 61.6 are all real instructions that apply to the question. Above y=61.6 there is only the page number at y=36.2, which is the header, a boundary. So the context starts at y=61.6.

`start_page` = 2, `start_y` = 61.6.

**3. Find the end.** I read forward from `(a)`. The lines at x=95.0 (`two pointers.`, `Write program code...`) and at x=55.6 (`Save your program...`, `Copy and paste...`) are content of (a). `[3]` at y=515.0 is a mark box, so (a) is finished. The next label is `(b)` at y=553.8, x=72.3.

Now the start of the next piece. Directly above `(b)` is the mark box `[3]`, a boundary, so there is no context to pull upward. The next piece starts at y=553.8. The end is 10 above that: 543.8, on page 2.

**4. Check.** Same page, 61.6 is less than 543.8, and the start is below the content top (60). Valid.

**Output**


**Updated current state**

```json
{
  "found": ["1:a"],
  "next": "Q1, part (b)"
}
```

---

### Call 2

**Current state**

```json
{
  "found": ["1:a"],
  "next": "Q1, part (b)"
}
```

**1. Locate the target.** `(b) The function Enqueue() performs these tasks:` is at y=553.8, x=72.3 on page 2. It is a part label at the part indent, and it follows `(a)` in sequence. This matches the state.

**2. Find the start.** (b) is a later part, so it starts at its own label line, extended upward over context (section 7C). Directly above it is the mark box `[3]` at y=515.0, which is a boundary. There is no context. `start_y` = 553.8, `start_page` = 2.

**3. Find the end.** I read forward. The `?` characters at x=95.0 are bullet symbols, not labels. The lines at x=117.6 are bullet text. `Write program code for Enqueue()`, `Save your program.` and `Copy and paste...` are content of (b). `[7]` at y=734.4 is the mark box. Then come the footer lines (y=782.8 and below), which are noise and are ignored.

The next page is page 3. Its header has the page number `3` at y=36.2. The first real line after the header is `(c) (i) Write program code...` at y=61.5, x=72.3. This line holds two labels, a part label `(c)` and a subpart label `(i)`.

The next piece starts at the very top of page 3, with only the header above it. So (b) did not run onto page 3. Following the page-top rule (section 8, step 4), `end_page` = 2 and `end_y` = 780.

**4. Check.** 553.8 is less than 780 on the same page. Valid.

**Output**


**Updated current state**

```json
{
  "found": ["1:a", "1:b"],
  "next": "Q1, part (c)"
}
```

---

### Call 3

**Current state**

```json
{
  "found": ["1:a", "1:b"],
  "next": "Q1, part (c)"
}
```

**1. Locate the target.** The label at y=61.5 on page 3 is `(c) (i)`. The state says part (c), and the paper shows that (c) opens with subpart (i) on the same line. So the first piece of (c) is the subpart (c)(i), named `c)i`. This refines the state and is not a mismatch: the state gives a general direction, and the paper decides how fine the piece is.

**2. Find the start.** This is the first subpart of a part, so it starts from the start of its part (section 7B). Part (c) is not the first part of the question, so the part's start is its own label line extended upward over context. The label line is the same line as `(i)`, y=61.5. Above it there is only the page number at y=36.2 (header). No context. `start_y` = 61.5, `start_page` = 3.

**3. Find the end.** I read forward. The `?` at x=117.6 are bullets, and the lines at x=140.3 are bullet text. `You do not need to validate...`, `Save your program.` and `Copy and paste...` are content. `[5]` at y=229.0 is a mark box. The next label is `(ii)` at y=254.9, x=92.9, a subpart label.

Directly above `(ii)` is the mark box `[5]`, so there is no context. The next piece starts at y=254.9, and the end is 254.9 − 10 = 244.9, on page 3.

**4. Check.** Valid.

**Output**

**Updated current state**

```json
{
  "found": ["1:a", "1:b", "1:c)i"],
  "next": "Q1, part (c), subpart (ii)"
}
```

---

### Call 4

**Current state**

```json
{
  "found": ["1:a", "1:b", "1:c)i"],
  "next": "Q1, part (c), subpart (ii)"
}
```

**1. Locate the target.** `(ii) Test your program.` is at y=254.9, x=92.9 on page 3. It is a subpart label at the subpart indent, and it follows `(i)`. This matches the state.

**2. Find the start.** This is a later subpart, so it starts at its own label line, extended upward over context (section 7D). It does not include the stem text of part (c). Directly above it is the mark box `[5]`, so there is no context. `start_y` = 254.9, `start_page` = 3.

**3. Find the end.** I read forward. `Enter the following data...` at x=106.3 is content. The lines `1`, `2`, `3` ... `11` at x=142.6 are bare numbers, but they are not question numbers. They are far from the left margin, and there is no question text on their rows, so they are data inside the subpart. `Take a screenshot...`, `Save your program.` and `Copy and paste...` are content. `[1]` at y=669.4 is the mark box. `[Turn over` at y=779.8 and the footer lines are noise.

On page 4, after the header (`4` at y=36.2), the first line is `(d) The function Dequeue():` at y=61.4, x=72.3, a part label. It sits at the very top of page 4 with only the header above it. By the page-top rule, this subpart ended on page 3: `end_page` = 3 and `end_y` = 780.

**4. Check.** Valid.

**Output**


**Updated current state**

```json
{
  "found": ["1:a", "1:b", "1:c)i", "1:c)ii"],
  "next": "Q1, part (c), subpart (iii)"
}
```

---

### Call 5

**Current state**

```json
{
  "found": ["1:a", "1:b", "1:c)i", "1:c)ii"],
  "next": "Q1, part (c), subpart (iii)"
}
```

**1. Locate the target.** The state expects a subpart `(iii)` under (c). I look for it after the end of (c)(ii). There is none. The next structural label is `(d)` at y=61.4, x=72.3 on page 4, a part label, and (d) follows (c) in sequence. So part (c) has only two subparts, and the state is wrong. I do not force the paper to match the state. I return the piece that actually comes next, which is part (d), and I set `state_mismatch` to true.

**2. Find the start.** (d) is a later part, so it starts at its own label line, extended upward over context. Above it there is only the page number at y=36.2 (header). No context. `start_y` = 61.4, `start_page` = 4.

**3. Find the end.** Does (d) have subparts? I read forward. The `?` at x=95.0 are bullets, and the lines at x=117.6 are bullet text. `Write program code for Dequeue()`, `Save your program.` and `Copy and paste...` are content. `[6]` at y=216.0 is the mark box. The next label is `(e) (i)` at y=254.9, x=72.3, a part label with a subpart. So (d) has no subparts and is a single piece.

Directly above `(e) (i)` is the mark box `[6]`, so there is no context. The next piece starts at y=254.9, and the end is 244.9, on page 4.

**4. Check.** Valid.

**Output**


**Updated current state**

```json
{
  "found": ["1:a", "1:b", "1:c)i", "1:c)ii", "1:d"],
  "next": "Q1, part (e)"
}
```

---

### Call 6

**Current state**

```json
{
  "found": ["1:a", "1:b", "1:c)i", "1:c)ii", "1:d"],
  "next": "Q1, part (e)"
}
```

**1. Locate the target.** `(e) (i) Write program code to amend...` is at y=254.9, x=72.3 on page 4. It has two labels on one line, so the first piece of (e) is the subpart `e)i`.

**2. Find the start.** This is the first subpart of a part, so it starts from the start of its part. Part (e) is a later part, so its start is its label line extended upward over context. Directly above is the mark box `[6]` at y=216.0, a boundary. No context. `start_y` = 254.9, `start_page` = 4.

**3. Find the end.** I read forward. The bullets and bullet text, `Save your program.` and `Copy and paste...` are content. `[3]` at y=396.4 is the mark box. The next label is `(ii)` at y=422.3, x=92.9. Directly above it is `[3]`, so there is no context. The end is 422.3 − 10 = 412.3, on page 4.

**4. Check.** Valid.

**Output**
```

**Updated current state**

```json
{
  "found": ["1:a", "1:b", "1:c)i", "1:c)ii", "1:d", "1:e)i"],
  "next": "Q1, part (e), subpart (ii)"
}
```

---

### Call 7

**Current state**

```json
{
  "found": ["1:a", "1:b", "1:c)i", "1:c)ii", "1:d", "1:e)i"],
  "next": "Q1, part (e), subpart (ii)"
}
```

**1. Locate the target.** `(ii) Test your program.` is at y=422.3, x=92.9 on page 4. It matches the state.

**2. Find the start.** This is a later subpart, so it starts at its own label line. Directly above is the mark box `[3]`, so there is no context. `start_y` = 422.3, `start_page` = 4.

**3. Find the end.** I read forward. `Enter the following data...` is content. The lines `100`, `10`, `5`, `6`, `18`, `68` at x=140.6 are data. They are far from the margin and have no question text on their rows, so they are not question numbers. `Take a screenshot...`, `Save your program.` and `Copy and paste...` are content. `[1]` at y=706.7 is the mark box. The footer lines are noise.

On page 5, after the header (`5` at y=36.2, centered, the page number), the first line is `2` at y=61.5, x=49.6, with the text `A program stores data about toys...` on the same row at x=72.3. This is a new question number. There is no `(iii)` and no `(f)`: Question 1 is finished.

The next piece (the first piece of Question 2) starts at the question number line, extended upward over context. Above it there is only the header. So the next piece starts at the very top of page 5. By the page-top rule, this subpart ended on page 4: `end_page` = 4 and `end_y` = 780.

**4. Check.** Valid.

**Output**


**Updated current state**

```json
{
  "found": ["1:a", "1:b", "1:c)i", "1:c)ii", "1:d", "1:e)i", "1:e)ii"],
  "next": "Q1, part (e), subpart (iii)"
}
```

---

### Call 8

**Current state**

```json
{
  "found": ["1:a", "1:b", "1:c)i", "1:c)ii", "1:d", "1:e)i", "1:e)ii"],
  "next": "Q1, part (e), subpart (iii)"
}
```

**1. Locate the target.** The state expects another subpart `(iii)` under (e), or a further part. After the end of (e)(ii) there is neither. The next structural label is the question number `2` at y=61.5, x=49.6 on page 5, a new question. The state is wrong, because Question 1 is complete. I do not force the paper to match. The piece that actually comes next is the first piece of Question 2, and I mark `state_mismatch`.

Question 2 has parts. Its introduction has `?` bullets at x=72.3 (bullet symbols, not labels), and `(a)` at y=165.4, x=72.3 is the first part label. So the first piece is part (a).

**2. Find the start.** This is the first piece of a question, so it starts at the question number line, extended upward over context. Above the number there is only the page number at y=36.2 (header). No context. `start_y` = 61.5, `start_page` = 5.

**3. Find the end.** I read forward from `(a)`. `four fields.`, `Save your program as Question2_J26.` and `Copy and paste...` are content of (a), and `[2]` at y=255.0 is its mark box. But `[2]` is the **last line I was given**. There is no `(b)` and no new question after it, and nothing shows that the paper has ended. The end of (a) is not visible, so I must not guess it (section 9).


**Updated current state**

The state does not change, because no piece was found. The system sends more lines after `[2]` and calls again with the same state. The state hint is still wrong at that point, so the agent resolves it the same way: it ignores the hint, finds that the next piece is `2:a`, and returns it as soon as the end is visible.