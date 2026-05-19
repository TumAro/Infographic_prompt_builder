---
subject: Computational Thinking and Artificial Intelligence
grade: 6
module: 4 — Logical and Visual Reasoning
topic: 4.1 — Visual Reasoning
---

# 4.1 Visual Reasoning
Module: Logical and Visual Reasoning

---

## Introduction

Imagine you are helping your younger cousin put together a jigsaw puzzle of the Indian flag. You pick up a piece, hold it, and in a fraction of a second your brain tells you: "This is upside down. Turn it ninety degrees to the right and it will fit." You did not measure anything. You did not use a ruler or a calculator. Your brain simply looked at the piece, imagined it moving through space, and gave you a confident answer. That effortless ability — to look at a shape, imagine what it would look like after it has been moved, turned, or flipped, and match it to something else — is called visual reasoning.

Visual reasoning is not a special talent. Every time you recognise that a door seen from a different room is the same door, every time you notice that a photograph has been taken upside down, every time you figure out which way a key needs to turn to open a lock, you are using visual reasoning. It is one of the most useful mental tools a person can develop, and it is directly connected to computational thinking. In fact, many problems that computers are taught to solve — recognising faces, reading handwriting, detecting whether an object in a photograph has been rotated — are problems of visual reasoning at their core.

In this topic, you will train your visual reasoning in three directions. First, you will explore how two-dimensional and three-dimensional shapes change when they are transformed — slid, turned, or flipped. Second, you will study rotations and reflections closely, learning to predict exactly what a shape will look like after each operation. Third, you will practise finding hidden patterns — patterns embedded inside figures that only reveal themselves when you learn to look carefully.

---

## 2D and 3D Transformations

Think about a stamp. When you press a rubber stamp onto paper, the ink leaves a mark. If you press it normally, the picture looks correct. But if someone hands you the stamp upside down and you press it anyway, the picture comes out inverted. And if you pick the stamp up and turn it to face a mirror, the picture in the mirror appears flipped left-to-right. The stamp itself did not change — only its position, angle, or orientation changed. That is precisely what a transformation is: a change in the position or orientation of a shape, without any change to the shape itself.

In computational thinking and in mathematics, we work with three fundamental types of transformations. A translation means sliding a shape from one place to another without rotating or flipping it — like pushing a carrom striker across the board. A rotation means turning a shape around a fixed point, the way a clock hand turns around the centre of a clock. A reflection means creating a mirror image of a shape, the way your face appears when you look into a still pond.

When we talk about two-dimensional shapes — flat shapes like squares, triangles, letters, and arrows — these three transformations are entirely sufficient to describe any change in position or orientation. A two-dimensional shape lives on a flat surface, like a sheet of paper, and can only move within that surface.

Three-dimensional objects, however, have one more dimension to navigate. Think of a cube — a box-shaped object with six flat square faces. You can rotate a cube around a vertical axis, the way you turn a globe to find a country. You can also rotate it around a horizontal axis, the way you turn a steering wheel. Or you can rotate it around an axis pointing straight towards you, the way a revolving door spins. Because a 3D object exists in space and not just on a flat surface, it can be turned in far more ways than a 2D shape. This is why thinking about 3D transformations requires you to build a clear picture in your mind — to mentally hold the object, rotate it, and see all of its faces in your imagination.

A very useful way to understand 3D objects is through their nets. A net is what a 3D shape looks like when you unfold it completely and lay it flat. Imagine cutting along some edges of a cardboard box and unfolding it until it lies entirely flat on the floor — that flat shape is the net of a cube. If you were to fold it back up, it would form the cube again. Thinking about nets is a form of 3D visual reasoning: you have to mentally fold the flat shape and predict what the three-dimensional object will look like.

[IMAGE]
Description: Two rows. The top row shows a cube with its six faces labelled with letters A to F. The bottom row shows the unfolded net of the same cube, with the same letters on each face in their correct unfolded positions.
Caption: When a cube is unfolded into its net, each face maintains its relative position. Folding the net back up in your mind is a fundamental 3D visual reasoning exercise.

### Worked Example

A cube has the letter **T** on its top face and the letter **F** on its front face. The cube is rotated 90 degrees to the right around its vertical axis (as if you were spinning it like a lazy susan). Which face is now the front face?

Step 1: Start by picturing the cube. The top is T, the front is F. Label the other faces in your mind: the face opposite the front is the back, the face to the right is the right face, and the face to the left is the left face.

Step 2: A 90-degree rotation to the right around the vertical axis means the cube turns like a person spinning on their heels to the right. The top stays on top and the bottom stays at the bottom — only the four side faces move.

Step 3: When you rotate to the right, the face that was on the right side swings around to become the new front face.

Step 4: Therefore, the right face of the cube is now the front face after the rotation.

This kind of reasoning — tracking what happens to each face as the object rotates — is exactly the type of thinking that computer vision systems perform when they try to identify a three-dimensional object from a photograph taken at an unusual angle.

Key Terms
---------
Transformation: A change in the position or orientation of a shape, without changing the shape itself.
Translation: Sliding a shape from one position to another without rotating or flipping it.
Rotation: Turning a shape around a fixed point by a certain angle.
Reflection: Producing the mirror image of a shape across a line.
Net: The flat, unfolded version of a three-dimensional shape.

Think & Reflect
---------------
When you look at the letter **b** in a mirror, it looks like the letter **d**. When you look at the letter **p** in a mirror, it looks like the letter **q**. Can you think of a letter that looks exactly the same in a mirror?

---

## Rotations and Reflections

Of all the transformations you will study, rotations and reflections are the two that come up most often in visual reasoning problems — in competitive examinations, in computer science, and in everyday life. It is worth spending careful time on each of them.

### Rotations

A rotation has three things that define it completely: the centre of rotation, the angle of rotation, and the direction of rotation.

The centre of rotation is the fixed point around which the shape turns. Think of a ceiling fan — the centre of the fan, where it is attached to the rod, is the centre of rotation. Every blade of the fan rotates around that single fixed point, and the point itself never moves.

The angle of rotation tells you how far the shape has turned. The most common angles you will encounter are 90 degrees (a quarter turn), 180 degrees (a half turn), and 270 degrees (a three-quarter turn). A full turn of 360 degrees brings any shape back to exactly where it started.

The direction of rotation tells you which way the shape has turned. In India, we use the terms clockwise — the same direction as the hands of a clock move — and anticlockwise, which is the opposite direction. It is important to always specify the direction, because a 90-degree clockwise rotation produces a completely different result from a 90-degree anticlockwise rotation.

Let us anchor this with a concrete example. Imagine the capital letter **L** sitting on a sheet of paper in its normal position, with the long vertical stroke going upward and the short horizontal stroke at the bottom going to the right. Now rotate this letter 90 degrees clockwise around its bottom-left corner. The vertical stroke, which was pointing up, will now point to the right, and the short horizontal stroke, which was pointing right, will now point downward. The letter now looks like an upside-down T, or more precisely, like the letter **⌐** (a reversed and rotated L). Performing the same rotation again — another 90 degrees clockwise — will take the letter to 180 degrees total, making it look like an upside-down L. One more 90-degree clockwise rotation brings it to 270 degrees, and a final 90 degrees brings it back to the original position at 360 degrees. Four quarter-turns always complete one full revolution.

[IMAGE]
Description: Four drawings of the capital letter L arranged in a clockwise circle, labelled 0°, 90°, 180°, and 270°, with curved arrows between each pair showing the direction of rotation.
Caption: The letter L at four stages of a clockwise rotation. After four quarter-turns, the letter is back in its original position.

### Reflections

A reflection produces the mirror image of a shape. The line you reflect across is called the mirror line or axis of reflection. Every point in the shape is flipped to the opposite side of this line, at exactly the same distance from the line.

In everyday life, you encounter reflections constantly. When you look at your reflection in a full-length mirror, your right hand appears on the left side of the image and your left hand appears on the right. The distance from your face to the mirror is exactly the same as the distance from your mirror image's face to the mirror. This is the defining rule of reflection: the image is at the same distance from the mirror line as the original, but on the opposite side.

There are three mirror line orientations you will most commonly work with. A vertical mirror line creates a left-right flip — the shape is reflected horizontally. A horizontal mirror line creates an up-down flip — the shape is reflected vertically. A diagonal mirror line creates an oblique reflection, which is a combination of both. In competitions and examinations, vertical and horizontal mirror lines are most common, and it is worth practising each until the result feels automatic.

One important and often tested idea is the difference between a rotation and a reflection. These two transformations can sometimes produce results that look similar — but they are fundamentally different. A rotation preserves the original orientation of the shape in the sense that the shape can be physically turned to match the original. A reflection cannot be undone by any rotation; it produces a shape that is the mirror image of the original but can never be made to coincide with the original by turning alone. This is why a left shoe and a right shoe, though identical in shape, can never be made to fit the same foot — one is the reflection of the other.

### Worked Example

The letter **R** is reflected across a vertical mirror line. What does the result look like?

Step 1: Picture the letter R standing normally — the vertical stroke on the left, the curved bump on the upper right, and the diagonal leg going down to the right.

Step 2: A vertical mirror line flips the shape left-to-right. Every part that was on the right side moves to the left side, and every part that was on the left side moves to the right side.

Step 3: After reflection, the vertical stroke is now on the right side of the letter. The curved bump is now on the upper left. The diagonal leg goes down to the left.

Step 4: The result looks like a mirror R — a backwards R. This is the Cyrillic letter Ya (Я), and it is also the shape that appears when you see the letter R in a mirror.

Key Terms
---------
Centre of rotation: The fixed point around which a shape rotates.
Angle of rotation: The amount by which a shape is turned, measured in degrees.
Clockwise: The direction of rotation that follows the movement of clock hands.
Anticlockwise: The direction of rotation opposite to the movement of clock hands.
Axis of reflection (mirror line): The line across which a shape is reflected to produce its mirror image.

Practice Problems
-----------------
1. A square has the number 6 written on it in normal orientation. The square is rotated 180 degrees. Does the number now look like a 9? Explain why.
2. Draw the capital letter **A** and reflect it across a vertical mirror line. Does the result look the same as the original? Which other capital letters have this property?
3. The capital letter **N** is rotated 90 degrees clockwise. Describe what the result looks like.

---

## Hidden Patterns

There is a particular kind of visual reasoning problem that rewards patience more than speed. In these problems, a shape or figure appears straightforward at first glance — and then, when you look more carefully, something hidden reveals itself. A pattern was there all along; you simply had to train your eye to find it.

Hidden patterns appear in two main forms: hidden symmetry within a figure, and hidden structure across a sequence of figures.

### Symmetry and Hidden Structure

A shape has symmetry when it can be divided into two or more parts that are mirror images of each other, or when it can be rotated by less than 360 degrees and still look exactly the same as it did before. The line that divides a symmetrical shape into two mirror-image halves is called its line of symmetry or axis of symmetry.

Some shapes have a single line of symmetry — an isoceles triangle, for example, can be divided down the middle into two equal halves, but that is the only way to divide it symmetrically. Other shapes have multiple lines of symmetry. A square has four lines of symmetry: one vertical, one horizontal, and two diagonal. A circle has infinitely many — any line that passes through the centre is a line of symmetry.

Here is what makes symmetry a tool for hidden pattern detection: when you look at a complex figure and cannot immediately understand its structure, drawing or imagining its lines of symmetry often reveals the underlying logic of the shape instantly. The figure that seemed cluttered and chaotic suddenly becomes organised and clear. Symmetry acts like a key that unlocks a figure's hidden order.

In Indian art and architecture, this principle has been used for thousands of years. The geometric patterns in Rangoli designs, the star-shaped motifs on temple ceilings, the lattice windows of Mughal buildings — all of them are constructed using deep and layered symmetry. An artist designing a Rangoli does not draw each petal individually; she draws one petal and then uses rotational symmetry to place identical petals at equal intervals around a centre point. The hidden structure is the rotation rule.

[IMAGE]
Description: A traditional eight-petal Rangoli design shown in two stages — first as a single petal drawn from the centre, then as the complete eight-petal design created by rotating that petal seven times at 45-degree intervals.
Caption: One petal, rotated eight times at 45 degrees each, produces the complete Rangoli design. The entire figure is built on a single hidden rule.

### Hidden Patterns in Sequences

The second type of hidden pattern involves a series of figures — usually three or four in a row — where each figure changes according to a rule that is not immediately obvious. Your task is to find the rule and either complete the series or identify which figure comes next.

The key to solving these problems lies in a systematic approach. Rather than staring at the whole figure and hoping the answer appears, you break the figure down into its separate parts — its shape, its size, its shading, the number of sides, the position of each element — and you ask, one part at a time: what is changing here?

Consider a sequence where the first figure is a large circle containing a small triangle, the second figure is a large circle containing a small square, and the third figure is a large circle containing a small pentagon. The outer shape (the large circle) stays the same. The inner shape changes: triangle has 3 sides, square has 4 sides, pentagon has 5 sides. The pattern is that the inner shape gains one side with each step. Therefore, the fourth figure should be a large circle containing a small hexagon, which has 6 sides.

This is decomposition applied to visual reasoning. You broke the figure into parts, found the changing part, identified the rule, and applied it to generate the next term. Everything you learned about decomposition and pattern recognition in Module 3 is being put to work here — just with shapes instead of numbers.

### Worked Example

A sequence of three figures is described below. Identify the hidden rule and determine the fourth figure.

Figure 1: A square with one dot in the top-left corner.
Figure 2: A square with one dot in the top-right corner.
Figure 3: A square with one dot in the bottom-right corner.
Figure 4: ?

Step 1: Break the figure into parts. There are two parts: the outer shape (the square) and the position of the dot.

Step 2: The outer shape does not change. The square remains a square in all three figures.

Step 3: The dot's position changes. In Figure 1 it is in the top-left, in Figure 2 it is in the top-right, in Figure 3 it is in the bottom-right.

Step 4: Find the movement rule. Top-left → top-right → bottom-right. The dot is moving clockwise around the corners of the square, one corner at a time.

Step 5: The next position in a clockwise direction from the bottom-right corner is the bottom-left corner.

Step 6: Figure 4 is a square with one dot in the bottom-left corner.

The hidden pattern was a clockwise rotation of position. Once named, the rule is obvious — but it required decomposing the figure to find it.

Key Terms
---------
Symmetry: The property of a figure that can be divided into parts that are mirror images of each other.
Line of symmetry (axis of symmetry): A line that divides a shape into two mirror-image halves.
Rotational symmetry: The property of a figure that looks identical after being rotated by less than 360 degrees.

Think & Reflect
---------------
A wheel has eight spokes arranged at equal angles. If you rotate the wheel by 45 degrees, it looks exactly the same. How many times can you rotate the wheel by 45 degrees before it returns to its original position? What does this tell you about its rotational symmetry?

Practice Problems
-----------------
1. How many lines of symmetry does the capital letter **H** have? Draw them.
2. A sequence of figures shows a triangle with one shaded side, then a triangle with two shaded sides, then a triangle with three shaded sides. All three sides of the fourth triangle are shaded. What happens in the fifth figure, based on a cyclic pattern rule?
3. A figure shows a large diamond shape with a smaller diamond inside it. The smaller diamond is rotated 45 degrees relative to the outer one, so its corners point towards the flat sides of the outer diamond. How many lines of symmetry does the whole figure have?

Did You Know?
-------------
Computer vision — the technology that allows a computer to understand and interpret images — relies heavily on the same operations you have studied in this topic. When a computer identifies a face, it must recognise that the same face looks different when tilted, turned, or viewed from a different angle. To do this, computers apply mathematical versions of rotation and reflection to the image data. Training yourself to mentally rotate and reflect shapes is, in a very real sense, training your mind to think the way a vision computer thinks.
