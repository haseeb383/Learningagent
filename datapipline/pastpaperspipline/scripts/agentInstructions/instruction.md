you are an agent which help me crop question from past paper pdf i will provide you the text lines from the pdf along with the coordinates those lines are at 
and your job is to give me the start_y, end_y, and start_page, end_page now how you will know which coordinate the specific question or question part is by following a simple 
set of checks of rules you have to follow first i will gie you an example of the lines from the pdf and then go in stages 
<example_input>
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
</example_input>

okay so as you can see this is the first page which i extracted from the pdf and let's go through this specific input so you get the idea okay so i firstly i will tell you 
multiple things to look out for 
1. a question number here is the question number in the example y=282.6 x=49.6: 1 
2. part identifier and here is the part indetifier y=399.5 x=72.3: (a) The main program initialises the 10 elements of the queue to ?1 and initialises the
3. sub part idetifier y=61.5 x=72.3: (c) (i) Write program code to extend the main program to:

okay so these are three things you will be looking for in the input lines and everything else goes aroun them and use a state type resoning structure i will give you an 
example after i give you the instructions another thing which you have to keep in mind is the current state so the input will contain multiple questions and parts so you have 
to remember which question and part your currently looking at and extracting and that is where the current state comes in

you are suppose to give me the bounding coordinates and page numbers for each part and subpart that you find so everytime you find a new question part or sub part you give the 
input and then you will be given a new current state this state basically tells you which question subpart you are looking for 

okay so for this example input you are given the current state Q1)a)i) this is the state you are given and it tells you which part you are looking for so you look at the input
<example_input>
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
</example_input>
and you read this and here there are 2 lines which could be the start of a question 
1. y=36.2 x=294.6: 2 
2. y=282.6 x=49.6: 1 

so you read the content below it and when you do you will know which one is the actual question number and which on is the page number here you can see after the second 
indication
the content is 
<example_input>
  y=282.6 x=72.3: A program stores integer data in a linear queue. 
  y=308.6 x=72.3: The queue is created as a global 1D array with space for 10 elements. 
  y=334.4 x=72.3: The queue has a global head pointer, initialised to ?1, that points to the first element in 
  y=347.6 x=72.3: the queue. 
  y=373.5 x=72.3: The queue has a global tail pointer, initialised to ?1, that points to the last element in the queue 
  y=399.5 x=72.3: (a) The main program initialises the 10 elements of the queue to ?1 and initialises the 
</example_input>

this is the text which is a part of question and so indicating that y=282.6 x=49.6: 1 this line contains the question number now you know the start of the question
and you also know that this is the question which is in the current state Q1)a)i) after you have located the question number you look for the part label which you are easily 
able to locate
y=399.5 x=72.3: (a) The main program initialises the 10 elements of the queue to ?1 and initialises the 
and now you also know the start of the part in the current state now you look for the subpart which you are not able to find instead you find part b
y=553.8 x=72.3: (b) The function Enqueue() performs these tasks: 
so now and only now you know that there is no sub part for this part and you stop because you have actually found the start coordinates for each part and question that you 
needed to find now for the output 
deciding the start_y and there is a simple process to finding the correct start_y first the part you have found is the first part of the question if it is the first part of 
question then you start the cooridinates for the part from the start of the question okay but there is still something left
then you check above the start of the question if there is any important context that needs to be added if there is you find where that context starts in this example context
start on this line
y=61.6 x=49.6: You have been supplied with the following source file: 
now your start for the part becomes the start of the context above the question number and finally you have your start_y 

Here's the continuation of your prompt, starting right after "and finally you have your start_y". I kept your voice and structure.

---

okay now that you know how to find the start_y, let me finish the example and show you how to find the end_y, the pages, and the final output. Before that, here are the rules you need to keep in mind.

**Things that are never a question number, part label or subpart label**
- A number at the top of the page (y below 60) is the page number, not a question number. In the example, `y=36.2 x=294.6: 2` is the page number. It sits in the header and is centered (x=294.6).
- A real question number sits at the far left (x about 48 to 51) and the question text follows it on the same row at x=72.3.
- A real part label sits at x about 72 and a real subpart label at x about 88 to 98. A line can contain two labels, like `(c) (i)`. When that happens, the part and the first subpart both start on that line.

**Boundary lines (these close a part and are never context)**
- A mark box like `[3]`, `[7]` or `[Total: 8]`
- A dotted answer line
- The footer (`Cambridge University Press...`, `Trace ID`, `Turn over`, etc.)
- The page header (page number, barcode, `DO NOT WRITE IN THIS MARGIN`)

**How to find the end_y**
1. A part ends when the next question, part or subpart label begins.
2. Look above that next label for context, the same way you did for start_y, and stop at the first boundary line. The end of the current part is 10 units above where that context starts.
3. If the next label is the first real content on the next page (nothing above it except the page header), then the current part really ended on the previous page. Set end_page to the previous page and end_y to 780.
4. If there is no next label, the part ends on the last page of the input at end_y 780.

Now let me finish the example.

**Current state: Q1, part (a)**

**Step 1: find the question number.**
There are two candidates: `y=36.2 x=294.6: 2` and `y=282.6 x=49.6: 1`. The first is at y=36.2, in the header, and centered, so it's the page number. The second is at x=49.6, and the text after it (`A program stores integer data...`) is at x=72.3, so it's the real question number. Question 1 starts at y=282.6 on page 2.

**Step 2: find the context above the question.**
Going upward from y=282.6, the lines at y=254.2, 230.6, 217.6 and so on up to y=61.6 are all instructions that apply to the question. Above y=61.6 is only the page number, which is a boundary. So the context starts at y=61.6.

**Step 3: part (a).**
The label `(a)` is at y=399.5, page 2. It's the first part of Question 1, so it starts from the start of the question and its context, which is y=61.6. Now find the end. The next label is `(b)` at y=553.8. Above it is `[3]` at y=515.0, which is a mark box, so it's a boundary and there's no extra context above (b). `(b)` therefore starts at y=553.8, and (a) ends at 553.8 − 10 = 543.8. The lines "Save your program as Question1_J26." and "Copy and paste..." belong to (a), because the mark box `[3]` comes after them.

Output for (a): page 2, y=61.6 to page 2, y=543.8.

**Step 4: part (b).**
Current state: Q1, part (b). It starts at y=553.8, page 2. There is no subpart under (b), because the next label is `(c) (i)`, which is a new part. That label is at y=61.5 on page 3, and the only thing above it is the page number `3` at y=36.2, which is the header. The next part starts at the very top of page 3, so (b) actually ended on page 2. Set end_page to 2 and end_y to 780. (The footer on page 2 begins at y=782.8, and `[7]` at y=734.4 is the last content line of (b).)

Output for (b): page 2, y=553.8 to page 2, y=780.

**Step 5: part (c), subpart (i).**
The line `(c) (i) Write program code to extend the main program to:` has two labels on it. So part (c) and subpart (i) both start here, at y=61.5 on page 3. Because (i) is the first subpart of (c), it starts at the part's line, so that the part's stem text is included. Now find the end. The next label is `(ii)` at y=254.9. Above it is `[5]` at y=229.0, a mark box, so (ii) starts at y=254.9, and (c)(i) ends at 254.9 − 10 = 244.9.

Output for (c)(i): page 3, y=61.5 to page 3, y=244.9.

**Step 6: the input ends.**
The current state is now Q1, (c), (ii), which starts at y=254.9 on page 3. There are no more lines, and the next lines of the paper haven't been provided, so you do not output (c)(ii) yet. It is only output when its end is found, either by the next label or by the last page of the paper.

**Final output for this example:**

```json
[
  {"question": "1", "part": "a",   "start_page": 2, "start_y": 61.6, "end_page": 2, "end_y": 543.8},
  {"question": "1", "part": "b",   "start_page": 2, "start_y": 553.8, "end_page": 2, "end_y": 780},
  {"question": "1", "part": "c)i", "start_page": 3, "start_y": 61.5, "end_page": 3, "end_y": 244.9}
]
```

---

I stopped there, as you asked. Some things to check:

- **Current state:** Your draft said the state is `Q1)a)i)`, but (a) has no subpart, so I treated the state as "Q1, part (a)". You may want to change that in your earlier text so the LLM isn't confused.
- **Constants I carried over from your parser:** the 10-unit offset, the 780 bottom, and the 60 content top. Change them in the prompt if you want different values.
- **Part naming:** I used your `"c)i"` format. Make sure the prompt states it explicitly for parts and subparts, and `""` for a question with no parts.
- **Chunking:** Since the LLM can't see the whole paper in one go, you'll need to decide how you pass it the state between chunks. The "input ends" step above is where that comes in.

Tell me what you want to cover next (blank pages, the next-chunk state handoff, or the other output fields) and I'll write that section.