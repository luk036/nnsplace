48 x 45
40

```html
<svg viewBox="0 0 2000 1880" xmlns="http://www.w3.org/2000/svg">
  <!-- (48+2) * 40, (45+2) * 40 -->

  <style type="text/css">
    @import "mysvg.css";
  </style>

  <!-- Create mask that we'll use to define a slight gradient -->
  <mask maskUnits="userSpaceOnUse" id="fade">
    <!-- Here's that slight gradient -->
    <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="100%">
      <stop offset="0" style="stop-color: #FFFFFF" />
      <stop offset="1" style="stop-color: #000000" />
    </linearGradient>
    <!-- The canvas for our mask -->
    <rect fill="url(#gradient)" width="100%" height="100%" />
  </mask>

  <!-- Let's define the pattern -->
  <!-- The width and height should be double the circle radius we plan to use -->
  <pattern
    id="pattern-circles"
    x="0"
    y="0"
    width="40"
    height="40"
    patternUnits="userSpaceOnUse"
  >
    <!-- Now let's draw the circle -->
    <!-- We're going to define the `fill` in the CSS for flexible use -->
    <circle class="cell" opacity="0.2" cx="20" cy="20" r="15" />
  </pattern>

  <!-- Let's define the pattern -->
  <!-- The width and height should be double the circle radius we plan to use -->
  <pattern
    id="pattern-io"
    x="0"
    y="0"
    width="40"
    height="40"
    patternUnits="userSpaceOnUse"
  >
    <!-- Now let's draw the circle -->
    <!-- We're going to define the `fill` in the CSS for flexible use -->
    <circle class="iopad" opacity="0.2" cx="20" cy="20" r="15" />
  </pattern>

  <!-- The canvas with our applied pattern -->
  <rect x="40" y="40" width="1920" height="1800" fill="url(#pattern-circles)" />
  <!-- 40, 40, 48 * 40, 45 * 40 -->

  <rect x="40" y="0" width="1920" height="40" fill="url(#pattern-io)" />
  <!-- 40, 0, 48 * 40, 40 -->

  <rect x="40" y="1840" width="1920" height="40" fill="url(#pattern-io)" />
  <!-- 40, (45+1) * 40, 48 * 40, 40 -->

  <rect x="0" y="40" width="40" height="1800" fill="url(#pattern-io)" />
  <!-- 0, 40, 40, 45 * 40 -->

  <rect x="1960" y="40" width="40" height="1800" fill="url(#pattern-io)" />
  <!-- (48+1)*40, 40, 40, 45 * 40 -->

  <defs>
    <!-- A circle of radius 200 -->
    <circle
      id="s1"
      cx="200"
      cy="200"
      r="200"
      fill="yellow"
      stroke="black"
      stroke-width="3"
    />
    <!-- An ellipse (rx=200,ry=150) -->
    <ellipse
      id="s2"
      cx="200"
      cy="150"
      rx="200"
      ry="150"
      fill="salmon"
      stroke="black"
      stroke-width="3"
    />
    <rect
      id="r1"
      width="35"
      height="35"
      fill="#FF00A7"
      opacity="0.2"
      stroke="black"
      stroke-width="3"
    />
    <rect
      id="io"
      width="35"
      height="35"
      fill="#00E7FF"
      opacity="0.2"
      stroke="black"
      stroke-width="3"
    />
  </defs>
</svg>
```
