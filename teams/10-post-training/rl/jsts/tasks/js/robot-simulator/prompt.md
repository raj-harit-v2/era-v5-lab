Write a solution module for the exercise below. Reply with exactly one fenced javascript code block holding the complete contents of `robot-simulator.js`: keep the names and the export style of the starting file at the end of this message, and use no packages. Do not explain.

# Instructions

Write a robot simulator.

A robot factory's test facility needs a program to verify robot movements.

The robots have three possible movements:

- turn right
- turn left
- advance

Robots are placed on a hypothetical infinite grid, facing a particular direction (north, east, south, or west) at a set of {x,y} coordinates,
e.g., {3,8}, with coordinates increasing to the north and east.

The robot then receives a number of instructions, at which point the testing facility verifies the robot's new position, and in which direction it is pointing.

- The letter-string "RAALAL" means:
  - Turn right
  - Advance twice
  - Turn left
  - Advance once
  - Turn left yet again
- Say a robot starts at {7, 3} facing north.
  Then running this stream of instructions should leave it at {9, 4} facing west.

Starting file `robot-simulator.js`:

```javascript
//
// This is only a SKELETON file for the 'Robot Simulator' exercise. It's been provided as a
// convenience to get you started writing code faster.
//

export class InvalidInputError extends Error {
  constructor(message) {
    super();
    this.message = message || 'Invalid Input';
  }
}

export class Robot {
  get bearing() {
    throw new Error('Remove this line and implement the function');
  }

  get coordinates() {
    throw new Error('Remove this line and implement the function');
  }

  place({ x, y, direction }) {
    throw new Error('Remove this line and implement the function');
  }

  evaluate(instructions) {
    throw new Error('Remove this line and implement the function');
  }
}
```
