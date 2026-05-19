---
subject: Computational Thinking and Artificial Intelligence
grade: 6
module: 4 — Logical and Visual Reasoning
topic: 4.2 — Spatial Thinking
---

# 4.2 Spatial Thinking
Module: Logical and Visual Reasoning

---

## Introduction

Imagine your uncle calls you from the railway station and says he has never visited your home before. He needs directions. You know the route perfectly — you walk it every day — but now you must describe it entirely in words, without pointing, without walking alongside him, and without showing him a map. You have to say things like: "Come out of the main gate, turn left, walk straight until you see the big peepal tree, then take the right lane, go past the medical shop, and our building is the third one on your left." If you do this well, your uncle will arrive at your door without a single wrong turn.

What you just did — converting your personal sense of space into a precise, communicable set of directions — is a form of spatial thinking. Spatial thinking is the ability to understand, reason about, and describe the positions of objects in space and the relationships between them. It involves knowing where things are, how they relate to each other, how to move from one place to another, and how to represent all of this clearly so that someone else can follow your reasoning.

This skill is far more important to computational thinking than it might first appear. Every robot that moves through a factory, every GPS navigation system in a car, every game character that walks through a virtual city, and every delivery drone that finds its way to a rooftop — all of them depend on the same ideas you will study in this topic: direction, movement, and precise positioning on a grid. By the end of this topic, you will be able to read a grid, describe positions accurately, trace paths step by step, and solve navigation problems the way a computer would.

---

## Direction and Navigation

You have known the four cardinal directions — North, South, East, and West — since primary school. But there is a difference between knowing the names of directions and being able to use them as a precise thinking tool. In this subtopic, you will move from simply knowing the directions to actively reasoning with them.

### The Four Cardinal Directions and Their Relationships

The four cardinal directions are arranged so that North and South are always opposites, and East and West are always opposites. North is always directly opposite South — if you face North and turn around completely, you are facing South. East is always directly opposite West. Together, these four directions divide the space around any point into four equal sectors.

Between any two adjacent cardinal directions, there is an intermediate direction. Between North and East lies North-East. Between East and South lies South-East. Between South and West lies South-West. Between West and North lies North-West. These eight directions together — four cardinal and four intermediate — are all the directions you need to describe movement precisely in most spatial reasoning problems.

There is one more directional language you need to be fluent in: left and right relative to the direction you are currently facing. This is called relative direction, and it is different from the cardinal directions because it depends on which way you are looking. If you are facing North and you turn left, you are now facing West. If you are facing North and you turn right, you are now facing East. If you face East and turn left, you face North. This idea — that turning left or right changes your facing direction in a predictable way — is at the heart of many direction and navigation problems.

The rule is straightforward. When you turn left, you rotate 90 degrees anticlockwise. When you turn right, you rotate 90 degrees clockwise. If you make a U-turn, you rotate 180 degrees and face the exact opposite direction. You can chain these turns together: if you start facing South, turn right (now facing West), turn right again (now facing North), you have turned around through 180 degrees and are now facing the direction opposite your starting direction.

[IMAGE]
Description: A compass rose showing all eight directions — N, NE, E, SE, S, SW, W, NW — with a figure standing at the centre facing North. Two curved arrows show what happens when the figure turns left (facing West) and when it turns right (facing East).
Caption: Turning left rotates you 90 degrees anticlockwise; turning right rotates you 90 degrees clockwise. Your new facing direction depends entirely on the direction you started from.

### Giving and Following Navigation Instructions

A well-formed navigation instruction has three components: a starting position or direction, a movement (how far and in which direction), and an end position. When a series of such instructions is chained together, you get a route — a complete path from one point to another.

Consider Aarav, a Class 6 student who is helping plan the route for his school's treasure hunt. The treasure hunt begins at the school gate and ends at the library, and Aarav must write the instructions so clearly that any student, even one who has never done the route before, can follow them without getting lost.

The school campus is laid out as follows: the school gate faces South. Directly North of the gate is the main corridor. The library is at the North-East corner of the campus. The science lab is at the North-West corner. The playground is to the East of the corridor.

Aarav writes these instructions: "Enter through the school gate facing North. Walk straight along the main corridor. When you reach the end of the corridor, turn right. Walk past the playground on your left. The library is the building at the end of this path on your right."

Notice what Aarav did carefully. He told the student which direction to face at the start. He used landmarks to confirm the path ("walk past the playground on your left"). He described the destination relative to the path ("on your right"). This is precisely how a robot navigation algorithm works: every instruction specifies a direction, a distance or landmark, and often a confirmation signal to verify the path is correct.

### Worked Example

Meena leaves her house facing East. She walks 3 steps forward, turns left, walks 2 steps forward, turns left again, and walks 1 step forward. Which direction is she now facing, and is she to the east or west of where she started?

Step 1: Meena starts facing East.

Step 2: She walks 3 steps forward (East). Her position is now 3 steps East of her house. She is still facing East.

Step 3: She turns left. A left turn from East is a 90-degree anticlockwise rotation. East → North. She is now facing North.

Step 4: She walks 2 steps forward (North). Her position is now 3 steps East and 2 steps North of her house. She is still facing North.

Step 5: She turns left again. A left turn from North is a 90-degree anticlockwise rotation. North → West. She is now facing West.

Step 6: She walks 1 step forward (West). Her position is now 2 steps East and 2 steps North of her house (she moved 1 step back from 3 steps East, so she is 2 steps East). She is still facing West.

Final answer: Meena is now facing West, and she is 2 steps to the East of where she started.

Key Terms
---------
Cardinal directions: The four primary directions — North, South, East, and West.
Intermediate directions: The four directions between the cardinal ones — North-East, South-East, South-West, and North-West.
Relative direction: The direction left or right of the direction you are currently facing.
Route: A sequence of movement instructions that describes a complete path from one place to another.

Think & Reflect
---------------
If Meena continued from where she stopped in the worked example — still facing West — and turned left twice more, which direction would she be facing? Can you predict the direction she would face after any number of left turns from West?

Practice Problems
-----------------
1. Rajan starts facing North. He turns right, then turns right again, then turns left. Which direction is he now facing?
2. A robot starts at position A facing East. It moves 4 steps forward, turns left, moves 3 steps forward, turns left, moves 4 steps forward, and turns left one final time. Without moving forward again, which direction is it now facing, and how far is it from its starting position?
3. Write a set of navigation instructions to get from your classroom to the school canteen. Include at least two turns and two landmarks.

---

## Grids and Positioning

Navigation instructions in words are useful, but they become clumsy when the space is complex or when precision matters greatly. Imagine trying to describe the position of a single square on a chessboard using only words — "it is the square on the right side, somewhat near the top, diagonally above the tall piece" — and you can immediately see the problem. What is needed is a system that can describe any position in a space exactly and unambiguously, using as few words as possible. That system is the grid.

### Understanding the Grid

A grid is a two-dimensional arrangement of rows and columns, where each individual cell can be identified by specifying exactly which row and which column it belongs to. You have already encountered grids many times — a chessboard is a grid, a seating chart is a grid, the squares of a crossword puzzle form a grid, and the arrangement of houses in many modern Indian residential colonies follows a grid pattern.

To use a grid for precise positioning, we need a coordinate system. In the most common version used in computational thinking, each cell is identified by two numbers: a column number (which tells you how far across the grid the cell is) and a row number (which tells you how far up or down the cell is). Taken together, these two numbers form a coordinate pair, written as (column, row). The column is always written first and the row is always written second — and remembering this order is important, because swapping them would take you to an entirely different cell.

The point from which all column and row numbers are counted is called the origin. In most problems at this level, the origin is placed at the bottom-left corner of the grid, with columns numbered from left to right and rows numbered from bottom to top. So the cell at coordinate (1, 1) is the bottom-left cell of the grid, (2, 1) is the next cell to the right in the bottom row, and (1, 2) is the cell directly above the bottom-left cell.

[IMAGE]
Description: A 5×5 grid with column numbers 1 to 5 labelled along the bottom (left to right) and row numbers 1 to 5 labelled along the left side (bottom to top). Three cells are highlighted and labelled with their coordinates: (1,1) at the bottom-left, (3,3) at the centre, and (5,4) in the upper-right area.
Caption: In a coordinate grid, the column number is written first and the row number second. The origin (1,1) is always at the bottom-left corner.

### Movement on a Grid

Once you understand the coordinate system, you can describe any movement on a grid as a change in coordinates. Moving one step to the right increases the column number by 1. Moving one step to the left decreases the column number by 1. Moving one step upward increases the row number by 1. Moving one step downward decreases the row number by 1.

This means you can convert any navigation instruction into a pair of coordinate changes. "Move 3 steps East" becomes "increase the column number by 3." "Move 2 steps North" becomes "increase the row number by 2." And a sequence of movements can be tracked by updating the coordinates at each step, producing a precise record of the entire path.

This connection between direction and coordinate change is fundamental to how computers navigate. A robot, a game character, or an autonomous vehicle does not think in terms of vague directions like "go towards the library." It thinks in terms of coordinate updates: at this moment my position is (x, y), my next instruction adds (Δx, Δy) to my position, so my new position is (x + Δx, y + Δy). The geometry of space has been converted into arithmetic, and arithmetic is something a computer can perform very quickly and very reliably.

### Reading and Using a Grid Map

A grid map is a grid in which certain cells have been marked to represent specific features of an area — buildings, obstacles, open paths, or destinations. Reading a grid map is a skill that combines your understanding of coordinates with your ability to plan a route.

Consider a simplified map of a neighbourhood represented on a 6×6 grid. Each cell is either open (can be walked through) or blocked (contains a building or obstacle). A person starts at position (1, 1) and wants to reach position (6, 6). They can only move horizontally or vertically — not diagonally — and they cannot enter a blocked cell. Finding a valid path from start to destination on such a map is a problem that every navigation app on every mobile phone in India solves dozens of times per second.

The strategy for solving such problems is systematic. You do not need to find the shortest path immediately — first, find any valid path. Start at (1, 1). Identify the cells you can move to. Choose one. Update your position. Repeat. If you reach a dead end (all adjacent cells are blocked), backtrack to the last position where you had an alternative choice and try a different direction. This backtracking strategy — trying one path, and if it fails, returning to the last decision point and trying another — is called the algorithmic technique of backtracking, and it is one of the fundamental strategies in computer science.

### Worked Example

A robot is placed on a 5×5 grid at position (1, 1), facing East. The grid has the following blocked cells: (3, 1), (3, 2), (3, 3). The robot must reach position (5, 3). Trace a valid path for the robot, giving each position it visits in order.

Step 1: The robot starts at (1, 1) facing East.

Step 2: It moves East to (2, 1), then tries to move to (3, 1) — but (3, 1) is blocked. The robot cannot proceed East from (2, 1).

Step 3: The robot turns to face North and moves to (2, 2), then (2, 3), then (2, 4). It is now at (2, 4).

Step 4: From (2, 4), the robot can move East: (3, 4), then (4, 4), then (5, 4). The column 3 cells in rows 1, 2, and 3 were blocked, but (3, 4) is open. The robot is now at (5, 4).

Step 5: From (5, 4), the robot turns South and moves to (5, 3). This is the destination.

Path taken: (1,1) → (2,1) → (2,2) → (2,3) → (2,4) → (3,4) → (4,4) → (5,4) → (5,3).

The robot successfully navigated around the obstacle by finding an alternative path when the direct Eastern route was blocked.

Key Terms
---------
Grid: A two-dimensional arrangement of rows and columns used to organise and locate cells precisely.
Coordinate pair: Two numbers written as (column, row) that identify the exact position of a cell in a grid.
Origin: The reference point from which all coordinates are measured, typically the bottom-left cell of a grid.
Backtracking: The technique of returning to a previous decision point and trying a different path when the current path is blocked.

Think & Reflect
---------------
A robot following a fixed path on a grid is like a person following a pre-written algorithm. If the grid changes — say, a new obstacle appears — the robot's original instructions may no longer work. How is this similar to the idea of a bug in an algorithm that you studied in Topic 3.4?

Practice Problems
-----------------
1. On a 4×4 grid with the origin at the bottom-left, mark the cells at coordinates (2, 3), (4, 1), and (1, 4). Which of these is closest to the top-left corner of the grid?
2. A robot starts at (1, 1) on a 5×5 grid. It moves 2 steps East, then 3 steps North, then 1 step West. What are its final coordinates?
3. A grid map shows the following blocked cells on a 4×4 grid: (2, 1), (2, 2), (2, 3). A player starts at (1, 2) and needs to reach (4, 2). Describe a valid path using coordinates.

Did You Know?
-------------
The coordinate system you are using in this topic — two numbers that identify any point in a flat space — was formally developed by the French mathematician and philosopher René Descartes in the seventeenth century. It is called the Cartesian coordinate system in his honour. Today, every digital map on every smartphone — including the apps used by crores of Indians every day to navigate traffic in Mumbai, Delhi, and Bengaluru — is built entirely on this system. When you plot (column, row) on a grid in this topic, you are using the same mathematical idea that powers satellite navigation worldwide.
