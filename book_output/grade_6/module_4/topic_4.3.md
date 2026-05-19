---
subject: Computational Thinking and Artificial Intelligence
grade: 6
module: 4 — Logical and Visual Reasoning
topic: 4.3 — Logical Thinking
---

# 4.3 Logical Thinking
Module: Logical and Visual Reasoning

---

## Introduction

During a cricket match, the fielding captain watches the batsman play three deliveries and notices that the batsman steps to the right before hitting the ball to the leg side every single time. Without a word, the captain quietly moves two fielders to the leg side. The next ball, the batsman steps to the right again — and hits it straight to a fielder. The captain did not guess. He did not get lucky. He observed a pattern, drew a conclusion, and acted on it with confidence. That chain of thinking — from observation to conclusion, step by careful step — is called logical thinking.

Logical thinking is not a mysterious talent possessed only by detectives and mathematicians. It is a structured mental habit that anyone can develop, and it is one of the most important tools in a computational thinker's collection. Every time a programmer decides what should happen when a condition is true or false, every time a database searches for records that match a set of criteria, every time an AI system decides between two possible answers — it is applying logic. Logic is the skeleton beneath all of computing.

In this topic, you will study three forms of logical thinking that come up constantly in computational thinking problems. The first is deductive reasoning, which is the skill of drawing certain conclusions from given facts. The second is constraint-based reasoning, which is the skill of working backwards from a set of restrictions to find the only possible answer. The third ties both of these together in the context of sequence and grid problems, where you will apply logical thinking to structured arrangements of numbers, letters, and conditions.

By the time you finish this topic, you will be thinking the way a computer thinks when it processes a rule: not with intuition or guesswork, but with clear, step-by-step reasoning that produces the right answer every time.

---

## Deductive Reasoning

The word deductive comes from the Latin word meaning to lead down — as in, to lead downward from a general rule to a specific conclusion. When you reason deductively, you start with facts or rules that you know to be true, and you apply them to a specific situation to reach a conclusion that must also be true.

The simplest form of deductive reasoning has three parts: a general rule, a specific observation, and a conclusion. This structure is called a syllogism. Here is an example that every Indian student will find familiar. Rule: All students who score above 90 in Mathematics get a gold star certificate. Observation: Preethi scored 95 in Mathematics. Conclusion: Preethi gets a gold star certificate. The conclusion follows with certainty from the rule and the observation — not because we know Preethi personally, but because the logic demands it. There is no other possible outcome.

This kind of thinking — where the conclusion is forced by the rules — is called a valid deductive argument. What makes deduction powerful is its certainty. Unlike a guess or an estimate, a valid deductive conclusion cannot be wrong as long as the starting facts are true. This is precisely why computers use logic at their core: a machine that always applies the rules correctly will always reach the correct conclusion, with no room for error or doubt.

### Deductive Chains

Real problems rarely involve just one rule and one observation. More often, you have a chain of deductions — where the conclusion of one step becomes the observation for the next step. Each link in the chain must follow necessarily from the one before it. If any link breaks — if any single deduction is wrong — the entire chain collapses.

Think of a chain of deductions like a row of dominoes. When the first one falls, it knocks over the second, which knocks over the third, and so on. But if one domino is placed too far from the next, the chain stops and the rest do not fall. In deductive reasoning, each step must be close enough to the last — that is, it must follow logically — for the chain to reach its conclusion.

Consider this sequence of clues from a school noticeboard: All students in the Science Club must attend the Saturday session. All students who attend the Saturday session must submit a project report. Vikram is in the Science Club. From this, can you conclude that Vikram must submit a project report? Let us trace the chain. Vikram is in the Science Club, so he must attend the Saturday session (first rule applied). He attends the Saturday session, so he must submit a project report (second rule applied). The conclusion — Vikram must submit a project report — follows with certainty from two successive deductive steps.

### Worked Example

Three students — Ananya, Bharat, and Chitra — each participate in exactly one of three school activities: the Drama Club, the Music Club, or the Robotics Club. You are given the following clues.

Clue 1: Ananya is not in the Drama Club.
Clue 2: Bharat is not in the Music Club.
Clue 3: Chitra is not in the Robotics Club.

Which activity does each student participate in?

Step 1: List the possibilities. Each student can be in Drama, Music, or Robotics. Since each activity has exactly one student, no two students share an activity.

Step 2: Apply Clue 1. Ananya is not in Drama. So Ananya is in Music or Robotics.

Step 3: Apply Clue 3. Chitra is not in Robotics. So Chitra is in Drama or Music.

Step 4: Apply Clue 2. Bharat is not in Music. So Bharat is in Drama or Robotics.

Step 5: Now reason through the combinations. If Ananya is in Music, can the rest work? Chitra cannot be in Robotics (Clue 3), so if Ananya takes Music, Chitra must be in Drama. That leaves Robotics for Bharat — which does not violate Clue 2, since Bharat is only forbidden from Music. This assignment works: Ananya → Music, Chitra → Drama, Bharat → Robotics.

Step 6: Check whether the other possibility — Ananya in Robotics — also leads to a valid assignment. If Ananya is in Robotics, Chitra cannot be in Robotics either (Clue 3), so Chitra is in Drama or Music. Bharat cannot be in Music (Clue 2), so Bharat would be in Drama. That leaves Music for Chitra. This also appears to work: Ananya → Robotics, Bharat → Drama, Chitra → Music. However, this gives two valid solutions, which means we have not used all the constraints fully. Revisiting: with only three clues each eliminating one option per student, both assignments satisfy all constraints. In a well-formed puzzle, this would mean a fourth clue is needed. For this problem, accept the solution found in Step 5 as the primary answer and note that the puzzle as stated has two valid solutions — itself a valuable insight in logical thinking.

The habit of checking your solution against every clue before accepting it is one of the most important practices in deductive reasoning.

Key Terms
---------
Deductive reasoning: The process of reaching a certain conclusion by applying general rules to specific observations.
Syllogism: A three-part logical argument consisting of a general rule, a specific observation, and a conclusion.
Valid argument: A deductive argument in which the conclusion must be true if the starting facts are true.
Deductive chain: A sequence of deductive steps where each conclusion becomes the starting observation for the next step.

Think & Reflect
---------------
In the worked example, two valid solutions existed because there were not enough clues to pin down a unique answer. Can you write one additional clue that would make only one solution possible? What does this tell you about the relationship between the number of constraints and the uniqueness of a solution?

---

## Constraint-Based Puzzles

Every problem you have studied so far — from decomposition in Topic 3.1 to grid navigation in Topic 4.2 — has involved constraints. A constraint is a rule or condition that limits the possible answers. In this subtopic, you will meet a family of problems where constraints are not just a background detail but are the entire mechanism of the puzzle. Your job is to use the constraints to eliminate possibilities one by one until only one answer remains.

### The Logic of Elimination

The central strategy in constraint-based reasoning is elimination. You begin with the full set of all possible answers. You apply each constraint in turn. Every constraint rules out some possibilities. When enough constraints have been applied, only one possibility is left — and that is the answer.

This strategy is powerful precisely because it does not require intuition or lucky guesses. You do not need to know the answer in advance. You only need to apply the constraints faithfully, one at a time, until the answer reveals itself. This is exactly how a Sudoku solver works, how a logical database query works, and how certain AI search algorithms work — they eliminate invalid possibilities systematically until only the valid one remains.

### Seating and Ordering Puzzles

One of the most common types of constraint-based puzzle involves arranging people or objects in a specific order according to a set of given rules. These puzzles appear in school olympiads and competitive examinations across India, and they are excellent training for systematic thinking.

Imagine five students — Farida, Ganesh, Hema, Imran, and Jyoti — sitting in a row of five chairs numbered 1 to 5 from left to right. You are given the following constraints.

Constraint 1: Farida sits in chair 2.
Constraint 2: Ganesh sits somewhere to the right of Farida.
Constraint 3: Hema and Imran are not sitting next to each other.
Constraint 4: Jyoti sits in the rightmost chair.

From Constraint 4, Jyoti is in chair 5. From Constraint 1, Farida is in chair 2. That leaves chairs 1, 3, and 4 for Ganesh, Hema, and Imran. From Constraint 2, Ganesh must be to the right of chair 2, so Ganesh is in chair 3 or chair 4. From Constraint 3, Hema and Imran cannot be in adjacent chairs. If Hema is in chair 1 and Imran is in chair 3, they are not adjacent (chairs 1 and 3 have chair 2 between them), so that is allowed. If Ganesh is in chair 4, the remaining chairs 1 and 3 go to Hema and Imran. Chairs 1 and 3 are not adjacent, so Constraint 3 is satisfied regardless of which of the two occupies which. If Ganesh is in chair 3, the remaining chairs 1 and 4 go to Hema and Imran. Chairs 1 and 4 are also not adjacent, so Constraint 3 is again satisfied. Both arrangements are valid — and, as in the worked example for deductive reasoning, noticing that multiple arrangements satisfy all constraints is itself a correct and important observation.

The act of working through these possibilities in an organised way — not randomly guessing, but systematically testing each option against every constraint — is the essence of constraint-based reasoning.

### Worked Example

A teacher arranges four coloured boxes — Red, Blue, Green, and Yellow — on a shelf from left to right. The following constraints apply.

Constraint 1: The Red box is not at either end of the shelf.
Constraint 2: The Blue box is immediately to the left of the Green box.
Constraint 3: The Yellow box is at one of the ends.

Find all possible arrangements.

Step 1: The shelf has four positions: 1, 2, 3, 4 (left to right).

Step 2: Apply Constraint 3. Yellow is at position 1 or position 4.

Step 3: Apply Constraint 1. Red is not at position 1 or position 4. So Red is at position 2 or position 3.

Step 4: Apply Constraint 2. Blue is immediately to the left of Green. The only pairs of adjacent positions are (1,2), (2,3), and (3,4). So Blue-Green occupies one of these pairs.

Step 5: Try Yellow at position 1. The remaining positions 2, 3, 4 are for Red, Blue, and Green. Red must be at position 2 or 3. Blue-Green must be an adjacent pair from {2,3,4}. The possible Blue-Green pairs from positions 2, 3, 4 are (2,3) or (3,4). If Blue is at 2 and Green is at 3, Red must be at 4 — but Constraint 1 says Red cannot be at position 4. This does not work. If Blue is at 3 and Green is at 4, Red must be at 2 — which is allowed by Constraint 1. This works. First valid arrangement: Yellow(1), Red(2), Blue(3), Green(4).

Step 6: Try Yellow at position 4. The remaining positions 1, 2, 3 are for Red, Blue, and Green. Red must be at position 2 or 3. Blue-Green must be an adjacent pair from {1,2,3}. The possible Blue-Green pairs are (1,2) or (2,3). If Blue is at 1 and Green is at 2, Red must be at 3 — which is allowed. This works. Second valid arrangement: Blue(1), Green(2), Red(3), Yellow(4). If Blue is at 2 and Green is at 3, Red must be at 1 — but Constraint 1 says Red cannot be at position 1. This does not work.

Step 7: Two valid arrangements exist: Yellow–Red–Blue–Green and Blue–Green–Red–Yellow.

Practice Problems
-----------------
1. Three friends — Lakshmi, Mohan, and Nisha — each own exactly one pet from the following three: a dog, a cat, and a parrot. Lakshmi does not own the dog. Nisha does not own the cat. Mohan owns the parrot. Who owns which pet?
2. Five books are stacked in a pile from top to bottom. The Maths book is above the Science book. The English book is at the very top. The Hindi book is directly below the Maths book. The Social Science book is at the very bottom. Write the complete order of the books from top to bottom.
3. A row of three switches — Switch A, Switch B, and Switch C — each controls exactly one light: the red light, the blue light, or the green light. Switch A does not control the blue light. Switch C controls the green light. Which switch controls the red light?

---

## Sequence and Grid Problems

The final subtopic of this module brings together everything you have built across Module 3 and Module 4 — pattern recognition, decomposition, algorithmic thinking, spatial thinking, and logical reasoning — into one unified type of problem. Sequence and grid problems present information in a structured arrangement and ask you to use the rules of that arrangement to find missing values, spot inconsistencies, or determine what comes next.

### Number and Letter Sequences with Logical Rules

You encountered number sequences in Topic 3.2, where the rule was arithmetic — add a fixed number, multiply by a fixed number, or follow a two-step alternating rule. In logical sequences, the rule can be more complex: it may involve conditions, it may apply differently to alternate terms, or it may combine two or more separate patterns that run simultaneously.

Consider the sequence: A1, B3, C5, D7, ?, ?

There are two things changing in this sequence at the same time. The letter advances by one step through the alphabet with each term: A, B, C, D, and so the next letter should be E. The number increases by 2 with each term: 1, 3, 5, 7, and so the next number should be 9. The fifth term is E9, and the sixth term is F11. This is a mixed pattern combining letters and numbers with two independent rules running in parallel — a type you have not seen before in this book, and an important step up from the purely numerical sequences of Topic 3.2.

The key insight is the same one from Topic 3.3 on abstraction: decompose the sequence into its parts, find the rule for each part independently, and then recombine to get the complete answer.

### Grid-Based Logic Problems

A grid-based logic problem presents information in the cells of a table and asks you to fill in missing cells or determine what value belongs in a particular position. These problems require you to read across rows, down columns, and sometimes diagonally, using constraints to narrow down the possible values until only one fits.

A common and instructive type of grid problem is a number grid with row and column rules. Imagine a 3×3 grid where each row must add up to a given total, and each column must also add up to a given total. Some cells are filled in, and your task is to determine the values in the remaining cells.

Here is a small example. A 3×3 grid has the following rule: each row must add up to 15, and each column must also add up to 15. The filled cells are: Row 1 contains 2, ?, 6. Row 2 contains ?, 5, ?. Row 3 contains 6, ?, 2.

From Row 1: 2 + ? + 6 = 15, so the missing cell in Row 1 is 7. Row 1 is now: 2, 7, 6.
From Row 3: 6 + ? + 2 = 15, so the missing cell in Row 3 is 7. Row 3 is now: 6, 7, 2.
From Column 1: 2 + ? + 6 = 15, so the missing cell in Column 1, Row 2 is 7.
From Column 3: 6 + ? + 2 = 15, so the missing cell in Column 3, Row 2 is 7.
But Row 2 now reads: 7, 5, 7. Check: 7 + 5 + 7 = 19, not 15.

This is a contradiction — the grid as stated has no valid solution. Noticing this and stating it clearly is itself a correct and important answer. A computational thinker does not force an answer when the constraints produce a contradiction; she reports the contradiction and traces it back to find where the problem lies.

This is exactly what a program does when it encounters inconsistent inputs: it does not crash or produce a random answer. A well-written program detects the inconsistency and reports it so the user can correct the input.

### Worked Example

A 3×3 number grid must satisfy the following rules: each row sums to 12, and each column sums to 12. The grid is partially filled as shown.

```
| 4 | ? | 3 |
| ? | 6 | ? |
| 2 | ? | 5 |
```

Find all missing values.

Step 1: Apply the row rule to Row 1. 4 + ? + 3 = 12. The missing value is 5. Row 1: 4, 5, 3.

Step 2: Apply the row rule to Row 3. 2 + ? + 5 = 12. The missing value is 5. Row 3: 2, 5, 5.

Step 3: Apply the column rule to Column 1. 4 + ? + 2 = 12. The missing value in Row 2, Column 1 is 6. 

Step 4: Apply the column rule to Column 3. 3 + ? + 5 = 12. The missing value in Row 2, Column 3 is 4.

Step 5: Row 2 is now 6, 6, 4. Check the row sum: 6 + 6 + 4 = 16, not 12. Contradiction.

Step 6: Check Column 2. 5 + 6 + 5 = 16, not 12. Also a contradiction.

The grid as given has no valid solution — the constraints are inconsistent with the pre-filled values. This is the correct answer: state the contradiction clearly and identify which row or column reveals it first.

Key Terms
---------
Constraint: A rule or condition that limits the set of possible answers in a problem.
Elimination: The strategy of ruling out impossible answers by applying constraints one at a time until only one possibility remains.
Mixed sequence: A sequence in which two or more attributes change simultaneously according to independent rules.
Contradiction: A situation in which two or more constraints cannot all be satisfied at the same time.

Think & Reflect
---------------
In the worked example, the grid's constraints were inconsistent. In a computer program, what do you think would be the best way to handle a situation where the input data is contradictory — should the program produce a guess, stop running, or do something else? What might go wrong if a program just guessed instead of reporting the problem?

Practice Problems
-----------------
1. Complete the following sequence and explain the rule: 2, Z, 4, Y, 6, X, ?, ?
2. A 3×3 grid must have each row and each column sum to 9. The filled cells are: Row 1 contains 1, 5, ?. Row 2 contains ?, 2, ?. Row 3 contains 4, ?, 1. Find all missing values and verify that your solution is consistent.
3. In a mixed sequence, the odd-positioned terms (1st, 3rd, 5th, ...) follow the rule "add 3" and the even-positioned terms (2nd, 4th, 6th, ...) follow the rule "multiply by 2." The sequence begins: 1, 2, 4, 4, 7, 8, ?, ?. Find the 7th and 8th terms.

Did You Know?
-------------
The type of constraint-based reasoning you practised in this topic — applying rules to eliminate possibilities until one answer remains — is the foundation of a branch of computer science called constraint satisfaction. Constraint satisfaction algorithms are used to solve some of the hardest scheduling problems in the world: timetabling exams for lakhs of students, scheduling flights and crew for airlines, designing circuit boards, and even generating the puzzle you see in your newspaper's Sudoku grid. When a Sudoku puzzle is being generated or solved by a computer, it is running a constraint satisfaction algorithm at very high speed — doing in milliseconds exactly what you did by hand in this topic.
