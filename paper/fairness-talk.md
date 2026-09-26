## Outline 📋

\tableofcontents

# Placement

## Why Global Placement Is Hard

- **Placement** assigns every module a grid site: NP-hard combinatorial optimization.
- It must respect **no-overlap**, grid boundaries, and reserved columns (DSP/SRAM).
- True routed delay cannot be optimized directly, so a **wire-length proxy** is used.
- Moving one module changes *all* of its nets: modules are coupled through the netlist and the occupancy grid.

## The HPWL Proxy and Its Blind Spot

$$\mathrm{HPWL}(e) = \Bigl(\max_{i\in e} x_i - \min_{i\in e} x_i\Bigr) + \Bigl(\max_{i\in e} y_i - \min_{i\in e} y_i\Bigr)$$

- Convex but **non-smooth**.
- **Underestimates** routing for multi-pin nets ($n > 3$).
- Minimizing the **sum** creates blind spots: a few long nets are sacrificed to improve the average.
- The long nets cause timing violations and routing congestion.

## Fairness, Not Scarcity

- Congestion is usually not a shortage of routing resources but an **uneven distribution** of demand.
- "We do not worry about scarcity, but about unfairness."
- Change the objective: minimize the **worst** connection, not the total.

```{=latex}
\begin{center}
\begin{tikzpicture}[node distance=10mm]
\node[nred, text width=42mm] (ms) {\textbf{Min-sum}\\ minimize $\sum \mathrm{WL}$\\[2pt] some nets very long\\$\Rightarrow$ congestion};
\node[ngreen, text width=42mm, right=16mm of ms] (mm) {\textbf{Min-max}\\ minimize $\max \mathrm{WL}$\\[2pt] balanced distribution\\$\Rightarrow$ fairness};
\draw[ar] (ms) -- node[above, font=\scriptsize]{reframe} (mm);
\end{tikzpicture}
\end{center}
```

# Objective

## Minimize the Worst Wire Length

$$\min_{\text{placement}}\ \max_{(u,v)\in E}\ \bigl(c_x\,|x_u-x_v| + c_y\,|y_u-y_v|\bigr)$$

- A **bottleneck** objective: it bounds *every* connection.
- Convex (a maximum of linear terms) yet **non-smooth**.
- The linear terms may be replaced by any **monotone** (even concave) cost $m(\cdot)$,
  matching the concave wire costs of real FPGA fabrics.

## One Axis at a Time

- Optimize $x$ with $y$ frozen, then $y$ with $x$ frozen (alternating directions).
- Let $q_v$ be the coordinate on the axis under optimization and $r$ a trial wire-length **radius**:

$$q_v - q_u \le \operatorname{cost}\bigl((u,v),\, r\bigr), \qquad \forall (u,v) \in E .$$

- These are **difference constraints**: feasible *iff* the constraint graph has **no negative cycle**.
- Increasing $r$ relaxes the constraints, so the smallest feasible $r$ is set by the tightest cycle.

## The Minimum Cycle Ratio

- A negative cycle of length $n$ with total cost $C$ forces $n\,r \ge C$, i.e. $r \ge C/n$.
- Hence the smallest feasible radius is the **minimum cycle ratio** (maximum cycle mean):

$$r^{*} = \max_{\text{cycles } \kappa}\ \frac{\sum_{(u,v)\in\kappa} c_{uv}}{\lvert \kappa \rvert}.$$

- Worst-wire-length placement reduces exactly to a **parametric minimum-cost-flow** problem. ✅

# Howard Algorithm

## Policy Iteration for the Minimum Cycle Ratio

```{=latex}
\begin{center}
\resizebox{\linewidth}{!}{%
\begin{tikzpicture}[node distance=7mm]
\node[nblue, text width=24mm] (a) {Relax\\potentials $q$};
\node[nblue, text width=24mm, right=9mm of a] (b) {Detect\\cycles};
\node[nyellow, text width=26mm, right=9mm of b] (c) {Raise $r$ to the\\zero-cancel ratio};
\node[ngreen, text width=22mm, right=9mm of c] (d) {Done:\\$r^{*}$};
\draw[ar] (a) -- (b);
\draw[ar] (b) -- (c);
\draw[ar] (c) -- (d);
\draw[ar] (c) to[out=115,in=65] node[above, font=\scriptsize]{no improvement} (a);
\end{tikzpicture}}
\end{center}
```

- Bellman-Ford-style relaxation, cycle detection in the policy graph, then raise $r$ to the critical cycle's zero-cancel ratio; alternate the search direction.

## The Parametric Formulation

- Tighten the constraints by the radius:

$$q_v - q_u \le \operatorname{cost}(u,v) - r\,\tau_{uv}.$$

- The **zero-cancel** ratio of a cycle $\kappa$ is $\sum c_{uv} / \lvert\kappa\rvert$: the $r$ that makes the cycle's total weight zero.
- As $r$ rises, negative cycles disappear; the final $r$ is the **worst wire-length budget** on that axis.

## Integer-Only Distance

With $r = n/d$ and an integer arc cost $c$:

$$\operatorname{dist}(e, r) = \left\lfloor \frac{n - c\, d}{\delta\, d} \right\rfloor.$$

- One integer floor-division per arc: the whole sweep avoids floating point.
- Exact rationals near integer boundaries, with a fast integer inner loop.
- Engine: `digraphx.MinParametricSolver` and the negative-cycle finder.

# Legalization and I/O

## Legalization by Bipartite Matching

```{=latex}
\begin{center}
\begin{tikzpicture}[node distance=5mm]
\node[ngreen] (m1){module a};
\node[ngreen, below=of m1] (m2){module b};
\node[ngreen, below=of m2] (m3){module c};
\node[nblue, right=28mm of m1] (s1){slot 1};
\node[nblue, below=of s1] (s2){slot 2};
\node[nblue, below=of s2] (s3){slot 3};
\draw[ar] (m1)--(s1); \draw[ar] (m1)--(s2);
\draw[ar] (m2)--(s2); \draw[ar] (m2)--(s3);
\draw[ar] (m3)--(s1); \draw[ar] (m3)--(s3);
\end{tikzpicture}
\end{center}
```

- Bucket modules that share a coordinate; candidates are the reachable sites in a growing window.
- The edge weight is the **change in worst wire length** if the module moves there:

$$\min_{\mu}\ \sum_{v} \Delta \operatorname{worst}\bigl(v \to \mu(v)\bigr).$$

- A local window is tried first; a **global fallback** offers every free site on the line.

## I/O Pad Ring Assignment

- Pads must lie on the **border ring** around the core.
- Pick the side and coordinate nearest the pad's connected modules, respecting per-side capacity.
- Spread pads along each edge with the same matching machinery used for cells.
- Pads and cells **share the per-line capacity**, so any cap must be applied consistently.

# The Placer

## The Outer Optimization Loop

```{=latex}
\begin{center}
\resizebox{\linewidth}{!}{%
\begin{tikzpicture}[node distance=6mm]
\node[nyellow, text width=22mm] (init){Initial\\placement};
\node[nblue, text width=26mm, right=10mm of init] (x){Howard($x$)\\$\to$ legalize($y$)};
\node[nblue, text width=26mm, below=of x] (y){Howard($y$)\\$\to$ legalize($x$)};
\node[ngreen, text width=24mm, right=10mm of y] (io){I/O pads,\\snapshot};
\draw[ar] (init) -- (x);
\draw[ar] (x) -- (y);
\draw[ar] (y) -- (io);
\draw[ar] (io) to[out=0,in=0] node[right, font=\scriptsize]{improved?} (x);
\end{tikzpicture}}
\end{center}
```

- A round is accepted only if the worst wire length **improves**; otherwise the placement is rolled back and the loop stops.
- Monotone acceptance guarantees the output is never worse than the input.

## Design Patterns and Dependencies

- A thin library over the sibling packages `digraphx`, `netlistx`, `physdes`, and `mywheel`.
- **Strategy** for the legalizer, **Memento** for snapshot and rollback, **Adapter** for the solver cost model, **Facade** for the top-level run.
- Bit-identical output on a fixed seed-grid matrix is the **regression oracle**.
- The refactor removed ~2,400 lines of duplicated infrastructure with **zero** result changes. ✅

# Congestion and Results

## Visualizing Fairness

![](figures/congestion-32x32-combined.pdf){width=76%}

Combined congestion for the 32x32 placement; the busiest cut is normalized to 100 percent.

## x, y and Combined Maps

:::: {.columns}

::: {.column width="32%"}
![](figures/congestion-32x32-x.pdf){width=\linewidth}
:::

::: {.column width="32%"}
![](figures/congestion-32x32-y.pdf){width=\linewidth}
:::

::: {.column width="32%"}
![](figures/congestion-32x32-combined.pdf){width=\linewidth}
:::

::::

x-direction, y-direction, and their element-wise maximum.

## The Placement

![](figures/placement-32x32.pdf){width=64%}

Final legal placement on the 32x32 grid: 752 cells, 81 pads, worst wire length 1480.

## Convergence Across Grid Sizes

| Grid | Slots | Density | Rounds | Worst |
|:-----|------:|--------:|-------:|------:|
| 30x30 | 870 | 86% | 2 | 1640 |
| 30x40 | 1160 | 65% | 2 | 1440 |
| 32x32 | 992 | 76% | 1 | 1480 |
| 50x50 | 2450 | 31% | 3 | 1600 |
| 100x100 | 9900 | 8% | 2 | 2120 |

- Dense grids constrain the optimizer; roomy grids are **search**-limited, not capacity-limited.

## Density vs Congestion

:::: {.columns}

::: {.column width="50%"}
![](figures/congestion-30x30-combined.pdf){width=\linewidth}
Tight 30x30 (86 percent)
:::

::: {.column width="50%"}
![](figures/congestion-50x50-combined.pdf){width=\linewidth}
Roomy 50x50 (31 percent)
:::

::::

## Computational Cost

| Optimization | Effect |
|:-------------|:-------|
| Integer floor-division in the cost model | 1.85x on the hot callback |
| Direct linear-assignment solver | 2.6x per legalization |
| Gating infeasible matching calls | 7x per matching |
| Whole seed-grid matrix | 4.57x total CPU |

- Every change was validated against a **bit-identical** placement oracle.

# Routing and Conclusion

## Routed Placement

![](figures/routed-50x50.pdf){width=70%}

A global router builds one Steiner tree per net, rooted at the driver pin.

## Summary

- Optimize the **worst** connection, not the total: fairness over aggregation.
- NNS solves it exactly with **Howard's** parametric min-cost flow.
- **Bipartite matching** legalizes; the outer loop is monotone.
- Congestion maps make the fairness/routability trade-off **visible**.
- The exact objective is affordable. ✅

## Thank You

- Code: https://github.com/luk036/nnsplace
- Libraries: `digraphx`, `netlistx`, `physdes`

## Questions?

🎤 Discussion
