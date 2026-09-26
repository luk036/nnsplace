---
title: Fairness-centric Global Placement in VLSI Physical Design
author:
  - Wai-Shing Luk
documentclass: IEEEtran
classoption:
  - 10pt
keywords:
  - VLSI physical design
  - global placement
  - routing congestion
  - max-min fairness
figPrefix: "Fig."
abstract: |
  Routing congestion has become the dominant concern in modern VLSI physical
  design, yet traditional global placement objectives such as total wirelength
  or net-cut minimization do not guarantee a uniform distribution of routing
  demand and can leave locally congested regions. This paper argues for
  fairness-centric global placement: rather than minimizing an aggregate cost,
  the placer should minimize the worst-case congestion and equalize routing
  demand across the chip. We review the limitations of wirelength-driven
  placement, define congestion and its overflow metric, introduce the max-min
  fairness principle from network resource allocation, and outline objective
  functions and algorithmic techniques that realize it. We then discuss the
  interplay with wirelength, timing, and power objectives and identify open
  challenges in complexity, congestion estimation, mixed-size placement,
  multi-layer routing, and benchmarking. We then describe an open-source
  implementation that realizes the objective with Howard's parametric
  minimum-cost-flow algorithm and bipartite-matching legalization, and we
  report placement and congestion-map results on a standard benchmark.
---

```{=latex}
\begin{IEEEkeywords}
VLSI physical design, global placement, routing congestion, max-min fairness.
\end{IEEEkeywords}
```

## Introduction

The automated placement of circuit components, or cells, onto a silicon die is a critical step in the design of Very Large Scale Integrated (VLSI) circuits. The quality of the placement significantly impacts various aspects of the final integrated circuit, including its area utilization, power consumption, timing performance, and, crucially, its routability. Traditional objectives in global placement have often centered around minimizing total wirelength or net-cut cost, aiming to reduce interconnect delays and area. However, with the increasing complexity and density of modern VLSI designs, the problem of routing congestion has emerged as a paramount concern.

Routing congestion arises when the demand for routing resources in certain regions of the chip exceeds the available supply, leading to routing detours, increased wirelength, potential timing violations, and even unroutable designs. While minimizing total wirelength aims to reduce the overall wiring demand, it does not guarantee a uniform distribution of this demand across the chip. In fact, a placement with globally minimized wirelength can still exhibit highly congested local regions, as the algorithm may prioritize shortening some nets at the expense of others, leading to an uneven distribution of routing resources.

This inherent limitation of traditional placement objectives has motivated the exploration of congestion minimization as a primary goal during placement. Among various approaches to tackle congestion, the concept of **fairness** in the allocation of routing resources has gained increasing attention. This paper argues for a shift towards **fairness-centric global placement** in VLSI physical design. We will explore the limitations of solely focusing on global minimization objectives like wirelength, the motivation behind adopting a fairness perspective, the principles of fair resource allocation, potential approaches to implement fairness-centric placement, and the challenges and future directions in this domain. By drawing parallels with resource management in other fields and analyzing existing techniques, this paper aims to provide a comprehensive understanding of the importance and potential of fairness-centric methodologies in achieving routable and high-quality VLSI designs.

Beyond surveying the motivation and principles, this paper grounds the discussion in a working system. Following the survey, we present a concrete fairness-centric placer, the "No-Nonsense" (NNS) algorithm; show how its min-max objective reduces to a parametric minimum-cost-flow problem solved by Howard's algorithm; examine the congestion maps it induces; evaluate it on a standard benchmark; and sketch how the resulting placement flows into global routing.

## Background

### VLSI Physical Design Flow and Placement

The physical design of a VLSI circuit is a complex process that transforms a circuit netlist into a geometric layout ready for fabrication. This process is typically broken down into several stages, including floorplanning, placement, routing, and physical verification. **Placement** is the stage where physical locations are determined for all the components (standard cells, macros, IP blocks) of the circuit within the defined core area of the chip. The quality of the placement lays the foundation for the subsequent routing stage and significantly influences the overall performance and manufacturability of the final chip.

Placement is often performed in two phases: **global placement** and **detailed placement**. Global placement aims to find approximate locations for all cells, optimizing a given objective function (e.g., wirelength, congestion) while considering overall chip dimensions and potential placement blockages. During this phase, cells may overlap. **Detailed placement** then refines the global placement by removing cell overlaps and assigning cells to legal locations on the placement grid, often involving further optimization steps like cell swapping or shifting.

### Traditional Global Placement Objectives and Limitations

Historically, global placement has primarily focused on minimizing **total wirelength**, which is often estimated using metrics like half-perimeter wirelength (HPWL). The rationale behind this objective is that shorter wires generally lead to lower interconnect delay, reduced power consumption, and potentially smaller chip area. Various analytical and combinatorial techniques have been developed for wirelength-driven global placement, including quadratic programming, simulated annealing, and partitioning-based methods.

Another traditional objective is minimizing **net-cut**, particularly in partitioning-based placement algorithms. Net-cut refers to the number of signal nets that cross the boundaries of partitions during the placement process. Minimizing net-cut aims to reduce the number of long interconnections and improve locality.

However, as VLSI design complexity has escalated, the limitations of solely relying on wirelength or net-cut minimization have become increasingly apparent, especially concerning **routing congestion**. While reducing global wirelength can help minimize the total wiring demand on the chip, it does not guarantee a uniform distribution of this demand. An algorithm optimizing for total wirelength might cluster highly interconnected cells together in a small region, leading to a high density of routing demand in that area, even if the overall wirelength is minimized. Conversely, other regions might have abundant routing resources that remain underutilized.

As highlighted in the sources, "**minimizing wirelength may (and in general, will) create locally congested regions**". It is entirely possible for a minimum wirelength solution to require more routing resources through a particular region than are physically available. This excessive congestion can severely hinder the subsequent routing stage, potentially leading to a larger final routed wirelength due to detours around congested areas, increased routing complexity, longer design cycle times due to iterations between placement and routing, and even unroutable designs in fixed-die regimes.

### Defining and Measuring Congestion

**Congestion** in VLSI layout intuitively refers to a situation where too many nets need to be routed in localized areas, leading to a shortage of routing resources. To quantify and manage congestion during placement, the concept of a **global bin grid** is commonly employed. The chip area is divided into a grid of rectangular regions called global bins, and the boundaries between these bins are referred to as global bin edges.

The **routing demand** ($d_e$) on a global edge ($e$) is defined as the number of routed nets that cross that edge. This demand is estimated based on the cell placement using a global router or even a simpler model like a bounding box router. The **routing supply** ($s_e$) of a global edge is the physical routing capacity available across that edge, which is determined by the length of the edge and the technology parameters (e.g., number of routing layers, wire pitch).

A global edge is considered **congested** if the routing demand exceeds the routing supply ($d_e > s_e$). The **overflow** ($overflow_e$) of a congested edge is the amount by which the demand exceeds the supply: $overflow_e = d_e - s_e$ if $d_e > s_e$, and $0$ otherwise. The **total overflow** of a placement is the summation of the overflows across all global edges and serves as a global measure of congestion. A placement with a lower total overflow is generally considered less congested. Industry experience suggests that total overflow is a good indicator of overall routability. Congestion maps generated by CAD vendors often visualize this overflow information, highlighting congested regions.

### Relationship Between Wirelength and Congestion

Intuitively, a placement with optimized wirelength is expected to have fewer nets traversing the same region, thus potentially leading to lower congestion. As stated in one source, "**a layout with optimized wirelength will have less nets going through the same region, thus the congestion cost of the layout is also expected to be minimized**".

Furthermore, there is a fundamental relationship between the total wirelength and the total routing demand in a global placement context. If cells are assumed to be placed at the centers of global bins and the wirelength is measured in units of global bin dimensions, then "**the total wirelength of a global placement is equal to the total routing demand on all global edges**". This is because each unit of wirelength in this discretized space corresponds to a crossing of a global bin edge, contributing one unit to the routing demand.

This observation highlights that minimizing wirelength does indeed minimize the total amount of routing demand on the chip, and thus the average routing demand on each global edge. Given a fixed routing supply, reducing the average demand increases the likelihood of achieving a low-congestion layout globally. Based on this, it can be concluded that "**minimizing congestion is globally consistent with minimizing wirelength**".

However, this global consistency does not necessarily translate to local consistency. As demonstrated by an example in one source, a placement optimized for congestion (even distribution of nets) can have a higher total wirelength than a placement optimized for wirelength (clustering connected cells), which in turn exhibits local congestion. This illustrates that while wirelength minimization helps reduce the overall routing pressure, it does not prevent the formation of local hotspots where the routing demand exceeds the available supply. Therefore, traditional placement schemes based primarily on wirelength minimization "**cannot adequately account for congestion**".

## The Problem of Congestion in VLSI Placement

### Local Congestion Despite Global Wirelength Minimization

As previously discussed, the primary limitation of wirelength-driven placement is its inability to directly address the uniform distribution of routing resources. Algorithms focused on minimizing the sum of wirelengths across all nets may inadvertently create areas with a high density of interconnected cells and their corresponding routing demands. This clustering effect, while beneficial for reducing the overall wirelength, can lead to local congestion where the number of nets attempting to pass through a particular region exceeds the routing capacity of that region.

One source provides a compelling example of this dichotomy. A circuit with eight cells and four circularly connected nets is considered. A congestion-optimal placement evenly distributes the nets across the chip, resulting in zero overflow (a routable solution), but potentially a longer total wirelength. Conversely, a wirelength-optimized placement groups the interconnected cells closely together, leading to a shorter total wirelength but causing an overflow on a global edge due to the concentrated routing demand. This simple example effectively illustrates that "**minimizing congestion is not equivalent to minimizing wirelength**".

This trend is not limited to small examples but has also been observed in the placement of large industrial circuits. Congestion maps of wirelength-optimal placements often reveal significant localized congestion. This uneven distribution of routing demand can create bottlenecks for the subsequent routing algorithms.

### Detrimental Effects of Congestion

Excessive routing congestion has several detrimental effects on the VLSI design process and the quality of the final product:

*   **Routability Issues:** The most direct consequence of congestion is the difficulty in completing the routing of all the nets. When the routing demand exceeds the supply in certain areas, the router may be forced to take long detours around these congested regions to find available routing tracks. In severe cases, congestion can lead to an **unroutable placement** in fixed-die scenarios where the chip area is fixed.
*   **Increased Wirelength:** Routing detours caused by congestion inevitably lead to an increase in the final routed wirelength, even if the initial placement had a relatively short estimated wirelength. This increased wirelength can negatively impact circuit performance due to increased interconnect delay and power consumption.
*   **Performance Degradation:** Longer interconnects resulting from routing detours contribute to increased propagation delays, potentially leading to timing violations and a reduction in the overall performance of the circuit.
*   **Increased Chip Area:** In cases where a fixed-die size is not a strict constraint, severe congestion might necessitate an increase in the chip area to provide more routing resources, leading to higher manufacturing costs.
*   **Manufacturing Yield Issues:** Highly congested designs can also be more susceptible to manufacturing defects due to the increased density of wires and vias.
*   **Longer Design Cycle Times:** Iterations between the placement and routing stages become more frequent and time-consuming when significant congestion is present. The router's inability to complete the routing might necessitate revisiting the placement and performing adjustments, prolonging the overall design cycle.
*   **Global Router Performance Degradation:** Congested areas can also negatively impact the performance and efficiency of global routers, making it harder for them to find optimal routing paths.

### Increasing Importance in Advanced Technology Nodes

The problem of routing congestion has become increasingly critical with the advancement of VLSI technology and the shrinking feature sizes. As technology nodes decrease, the number of transistors that can be integrated onto a single chip increases dramatically, leading to more complex designs with a higher density of cells and interconnections. Simultaneously, the routing resources (number of routing layers, wire pitch) may not scale at the same rate, leading to a tighter constraint on the available routing capacity.

Furthermore, in modern designs, especially Field-Programmable Gate Arrays (FPGAs) with fixed routing resources, timing and congestion concerns often outweigh total wirelength. The fixed routing architecture of FPGAs makes them particularly sensitive to congestion, as routing detours can severely impact performance and may lead to designs that cannot be implemented within the available resources.

Therefore, addressing and mitigating routing congestion during the placement phase has become an indispensable aspect of modern VLSI physical design to ensure successful routing, achieve desired performance targets, and optimize overall design quality.

## Fairness-Centric Global Placement: Motivation and Principles

### The Need for Fair Resource Allocation

The limitations of traditional global placement objectives in adequately addressing routing congestion stem from their focus on global minimization (e.g., total wirelength) without explicitly considering the **fairness** in the distribution of the resulting routing demand across the available resources. Just as urban planners need to manage city development by not only minimizing the total distance between amenities but also ensuring that resources are reasonably accessible to all residents, placement engineers need to organize components in a way that avoids creating localized resource scarcity (congestion) even if the overall resource consumption (total wirelength) is low.

One source aptly captures this challenge by citing a Chinese proverb: "**we do not worry about scarcity, but about unfairness**". In the context of VLSI routing, this implies that the primary issue is not necessarily an overall lack of routing resources, but rather their unequal distribution, leading to congestion in some areas while others remain underutilized. This "unfair" allocation of routing demand can lead to the problems discussed in the previous section.

### Max-Min Fairness Principle

To address this issue of unequal resource distribution, the principle of **max-min fairness** offers a promising paradigm for global placement. This principle, originating from the field of communication networks and network traffic management, aims to **maximize the minimum resources allocated to each agent**, ensuring a baseline level of service while allowing for flexible allocation beyond that minimum. In the context of bandwidth allocation in networks, max-min fairness ensures that no flow can have its rate increased without decreasing the rate of another flow that has an equal or smaller rate. This concept provides a perfect parallel to the problem of routing resource allocation in chip design.

### Application to Placement

In the context of global placement, applying the max-min fairness principle translates to minimizing the worst-case routing congestion (or overflow) across all regions of the chip. Instead of solely focusing on minimizing the total overflow, a fairness-centric approach prioritizes ensuring that no single region experiences excessively high congestion, even if this might lead to a slightly higher total wirelength compared to a purely wirelength-optimized placement. The goal is to achieve a more balanced distribution of the routing demand, making it easier for the subsequent routing algorithms to find feasible paths for all nets without resorting to significant detours or encountering unroutable situations.

This shift in optimization objective, from global minimization to prioritizing fairness by minimizing the maximum congestion, fundamentally changes the approach to global placement. It acknowledges that in modern VLSI designs with tight routing resource constraints, especially in FPGAs, achieving a certain level of local routability across the entire chip is often more critical than achieving the absolute minimum total wirelength.

### Contrasting with Traditional Objectives

Traditional global placement objectives, like minimizing total wirelength, are essentially global minimization problems. While they aim for an optimal solution across the entire chip, they do not inherently prevent localized problems like high congestion. An algorithm aggressively minimizing total wirelength might make placement decisions that significantly increase the routing demand in certain already crowded areas, sacrificing the "fairness" of resource distribution for a better global cost.

In contrast, a fairness-centric approach directly addresses the uneven distribution of routing demand by focusing on the regions with the highest congestion. By attempting to reduce the peak congestion levels, these methods aim to improve the overall routability and quality of the final layout, potentially leading to better performance and manufacturability even if the total wirelength is slightly higher than what a purely wirelength-driven placer might achieve. The focus shifts from achieving the absolute best global metric to ensuring a more balanced and manageable routing landscape across the chip.

## Approaches to Fairness-Centric Global Placement

Implementing a fairness-centric approach to global placement requires modifying the objective function and/or the algorithmic techniques used during the placement optimization process. Several potential strategies can be explored:

### Modifying the Objective Function

The objective function in global placement guides the optimization process. To incorporate fairness, the objective can be modified to:

*   **Minimize the Maximum Congestion:** Instead of minimizing the total overflow, the objective can be to minimize the maximum overflow observed on any global bin edge. This directly targets the "worst-case" congestion scenario and encourages a more even distribution of routing demand.
*   **Weighted Congestion Minimization:** The congestion cost for each global bin edge can be weighted based on its current congestion level. Edges with higher congestion would have a larger weight, making the optimization algorithm more sensitive to reducing congestion in these critical areas.
*   **Hybrid Objectives with Fairness Terms:** The traditional wirelength objective can be combined with a term that quantifies the "unfairness" in congestion distribution. This term could, for example, be the variance of the congestion levels across all global bin edges. The optimization would then aim to minimize a weighted sum of wirelength and this unfairness metric, allowing for a trade-off between global wirelength and local congestion balance. However, as noted earlier, simple hybrid length plus congestion objectives have not always proven very effective, suggesting that the formulation of such hybrid objectives for fairness might require careful consideration.

### Algorithmic Techniques for Achieving Fairness

Various algorithmic techniques can be adapted or developed to achieve fairness in global placement:

*   **Iterative Refinement with Congestion Feedback:** Global placement can be performed in iterations, with congestion analysis performed after each iteration. Highly congested regions can be identified, and subsequent iterations can focus on moving cells out of these areas and into less congested regions. This requires effective mechanisms for identifying and alleviating congestion hotspots. **Post-processing techniques** specifically designed for congestion minimization after an initial placement, such as **net-centric approaches** that try to reroute congested nets by moving connected cells, have also shown promise.
*   **Network Flow Based Methods:** Network flow formulations can model the routing demand and capacity constraints in the global bin grid. By incorporating cost functions that penalize exceeding the capacity of edges (congestion), these methods can implicitly encourage a fairer distribution of flow (routing demand). Furthermore, max-flow min-cut theorem and related concepts might offer insights into identifying and resolving congestion bottlenecks.
*   **Mathematical Programming with Fairness Constraints:** Linear programming (LP) or integer programming (IP) formulations of the global placement problem can include constraints that directly limit the congestion on each global bin edge or minimize the maximum congestion. While these methods can be computationally expensive for very large designs, they offer the potential for directly optimizing fairness metrics.
*   **Legalization-Assisted Placement:** Integrating legalization constraints earlier in the placement process can help prevent severe overlaps and potentially reduce the likelihood of high congestion in later stages. By maintaining a more spread-out placement throughout the optimization, this approach can indirectly contribute to a fairer distribution of routing demand.
*   **Cell Shifting and Spreading Techniques:** Techniques like cell shifting, where cells are moved based on bin utilization to reduce overlap, and spreading forces, which prevent cells from collapsing back into dense regions, can contribute to a more even cell distribution, which in turn can lead to a fairer distribution of routing demand.

### Empirical Evidence and Existing Approaches

While the explicit term "fairness-centric" might not be universally used, several existing congestion-driven placement techniques implicitly aim for a fairer distribution of routing resources:

*   **Congestion-Driven Placement Based on Multi-Partitioning:** These methods use actual congestion cost calculated from pre-computed Steiner trees to minimize congestion, aiming to distribute nets more evenly across partitions.
*   **Congestion-Driven Quadratic Placement:** These approaches incorporate congestion metrics into the quadratic objective function, penalizing placements that lead to high congestion.
*   **Algorithms Using Congestion Maps to Guide Optimization:** Many modern placers use congestion maps, generated through static, probabilistic, or constructive route estimation, to identify congested regions and guide cell movement or swapping decisions to alleviate these hotspots. Techniques like cell bloating (increasing cell dimensions in congested areas during global placement) and whitespace injection (adding empty space in congested regions) are used to reduce cell density and indirectly alleviate routing pressure.
*   **Post-Placement Congestion Minimization:** As mentioned before, net-centric post-processing techniques that focus on rerouting nets in congested areas by making small placement changes are explicitly designed to improve the fairness of routing demand distribution after the main placement phase.

The experimental results presented in some sources indicate that a two-step approach, involving initial wirelength minimization followed by a post-processing stage for congestion minimization (often using net-centric techniques), can be very effective in producing placements with significantly reduced congestion. This suggests that while global wirelength optimization provides a good starting point for overall routing demand reduction, a subsequent focus on local congestion hotspots and achieving a fairer distribution of routing resources is crucial for achieving high-quality, routable designs.

## A Fairness-Centric Placer: The NNS Approach

The preceding sections argued that global placement should optimize the *worst* connection rather than the total, and that doing so is a fairness property. This section shows that the principle is realizable in a compact, exact algorithm, following the open-source *No-Nonsense* (NNS) placer [9]. NNS deliberately avoids the smooth convex approximations that dominate analytical placement: it keeps a linear, non-smooth wire-length cost and solves the resulting min-max problem exactly with a parametric minimum-cost-flow engine. The resulting optimizer needs no floating-point arithmetic when a linear cost model is assumed, and it accommodates monotone (in particular concave) cost models that better match fixed FPGA fabrics.

### Objective: Minimize the Worst Wire Length

Let the netlist connect modules by two-terminal arcs $E$. A placement assigns coordinates $(x_v, y_v)$ to every module $v$. Whereas a traditional placer minimizes a sum, NNS minimizes the maximum:

$$\min_{\text{placement}}\ \max_{(u,v)\in E}\ \bigl(c_x\,|x_u-x_v| + c_y\,|y_u-y_v|\bigr),$$

where $c_x$ and $c_y$ scale the per-axis wire costs. This is a min-max (bottleneck) objective: it bounds *every* connection, so no single net can be sacrificed for the average -- exactly the fairness requirement argued above. Because it is a maximum of linear terms the objective remains convex, but it is non-smooth. More generally, the linear terms may be replaced by any monotone per-axis cost function $m(\cdot)$, which is how the placer targets the concave wire costs of real FPGA routing.

### Per-Axis Optimization and Difference Constraints

NNS optimizes one axis at a time while the other axis is frozen, an alternating-direction scheme [3, 7]. Let $q_v$ denote the coordinate of $v$ on the axis under optimization, and treat the perpendicular coordinates as constants. For a trial *radius* $r$, the wire-length budget allowed on this axis, the placement is feasible on this axis if and only if every arc meets its budget:

$$q_v - q_u \le \operatorname{cost}\bigl((u,v), r\bigr), \qquad \forall (u,v) \in E .$$

These are difference constraints; the system is feasible exactly when its constraint graph contains no negative cycle. Increasing $r$ relaxes the constraints, so the smallest feasible radius is governed by the tightest cycle. Writing $c_{uv}$ for the (integer) cost of arc $(u,v)$, the minimum feasible radius is the *minimum cycle ratio*

$$r^{*} = \max_{\text{cycles } \kappa}\ \frac{\sum_{(u,v)\in\kappa} c_{uv}}{\lvert \kappa \rvert},$$

which is the maximum cycle mean of the graph. The worst-wire-length bottleneck therefore reduces exactly to a minimum-cycle-ratio / parametric minimum-cost-flow problem.

### Howard's Algorithm and the Minimum Cycle Ratio

NNS solves the parametric problem by Howard's policy-iteration method [4, 6], as provided by the `digraphx` library [8]. In its parametric form the constraints become

$$q_v - q_u \le \operatorname{cost}(u,v) - r\,\tau_{uv},$$

where $\tau_{uv}$ is a per-arc "time" factor. The solver (i) relaxes the potentials $q$ in a Bellman-Ford manner, (ii) inspects the predecessor/successor policy for cycles, (iii) raises $r$ to the *zero-cancel* ratio of the critical cycle, and (iv) alternates the search direction until no further improvement is possible. Each axis pass returns the exact worst-wire-length budget $r^{*}$ on that axis.

Keeping the distance domain integral is what makes the method both exact and fast: with $r = n/d$, the per-arc distance collapses to a single integer floor-division,

$$\operatorname{dist}(e, r) = \left\lfloor \frac{n - c\, d}{\delta\, d} \right\rfloor,$$

so an entire Howard sweep is executed with integer arithmetic while the ratio itself stays an exact rational.

### Legalization by Minimum-Weight Bipartite Matching

Optimization alone lets several modules drift to the same coordinate. Legalization restores a one-module-per-site placement, line by line. Modules that share a coordinate on the perpendicular axis are collected into a bucket; a bipartite graph is built between the bucket's modules and the candidate sites within a growing window; and the edge weight is the *change in worst wire length* if a module is moved to that site. A minimum-weight full matching then assigns every module a distinct site:

$$\min_{\mu}\ \sum_{v} \Delta \operatorname{worst}\bigl(v \to \mu(v)\bigr).$$

If no full matching exists within the local window, the window grows; a global fallback offers every free site on the line, so legalization fails only when the grid genuinely lacks capacity. The matching is solved directly with a linear-assignment routine (Hungarian method) [8], preserving the reference tie-breaking order so the placer's trajectory, and therefore its result, is deterministic.

### I/O Pad Ring Assignment

I/O pads must lie on the border ring around the core. For each pad, NNS chooses the side and coordinate nearest its connected modules, respecting a per-side capacity, and then legalizes the pads along each edge with the same matching machinery used for cells. Pads and cells share the per-line capacity, so a cap on the core must be applied consistently to the I/O ring as well.

### The Outer Optimization Loop

One round of NNS runs Howard's algorithm on $x$, legalizes on $y$, and snaps the pads, then runs Howard on $y$, legalizes on $x$, and snaps the pads again. The worst wire length is recomputed; a round that does not improve it is rejected and the placement is rolled back to the previous snapshot, which also terminates the loop. This monotone acceptance guarantees that the output is never worse than its input and supplies a natural convergence criterion.

![Final legal placement produced by NNS for the benchmark netlist `p1` on a 32x32 grid (752 cells, 81 I/O pads; worst wire length 1480). Blue squares are core cells, red squares are pads on the border ring, and green lines are the pad-to-module connections.](figures/placement-32x32.pdf){#fig:placement width=100%}

### Implementation

NNS is implemented as a thin Python library on top of the sibling packages `digraphx` (parametric flow and negative-cycle detection), `netlistx` (netlist I/O), `physdes` (rectilinear geometry and routing), and `mywheel` [8, 9]. Its structure is organized around a few classic design patterns: a *Strategy* for the legalizer, a *Memento* for snapshot and rollback, an *Adapter* bridging the graph cost model to the solver, and a *Facade* for the top-level run. Treating bit-identical output on a fixed seed-grid matrix as a regression oracle allowed later refactorings to remove roughly 2,400 lines of duplicated infrastructure without changing a single placement.

## Visualizing Fairness with Congestion Maps

To judge whether a placement is *fair*, it is not enough to look at the wire-length objective; the routing demand it induces must be inspected. For every net, a global router builds an orthogonal routing tree, and each tree branch increments a counter for every horizontal or vertical grid-cut segment it crosses between adjacent lattice points. Per core cell, the x-direction congestion is the busiest horizontal cut immediately to its left or right, and the y-direction congestion is defined symmetrically; the combined map is their element-wise maximum. Each map is normalized so that its own busiest cut becomes 100 percent, and rendered with a green (0 percent) to yellow (50 percent) to red (100 percent) palette.

Splitting the map by direction exposes the two alternating sub-problems that NNS solves. @fig:congx and @fig:congy show the x- and y-direction maps for the 32x32 placement; their element-wise maximum is the combined map of @fig:congcombined, which is the quantity the min-max objective actually bounds.

![Congestion in the x-direction for the 32x32 placement, normalized to the busiest horizontal cut.](figures/congestion-32x32-x.pdf){#fig:congx width=100%}

![Congestion in the y-direction for the same placement, normalized to the busiest vertical cut.](figures/congestion-32x32-y.pdf){#fig:congy width=100%}

![Combined congestion map (element-wise maximum of the x- and y-direction maps) for the 32x32 placement.](figures/congestion-32x32-combined.pdf){#fig:congcombined width=100%}

These maps make the fairness argument concrete. A wirelength-optimal placement concentrates demand into a few bright, congested cuts, whereas a fairness-centric placement spreads demand more evenly, lowering the peak. Minimizing the worst wire length does not by itself guarantee a perfectly uniform map, but it removes the systematic blind spot of aggregate minimization: the worst connection can no longer be sacrificed for a better average.

## Empirical Evaluation

To show that the fairness objective is not only principled but affordable, the NNS implementation was exercised on the `p1` benchmark: 752 core cells plus 81 I/O pads (833 modules), connected by 902 nets, of which 107 touch an I/O pad. Placements were computed on grids from 30x30 to 100x100 with a fixed random seed. Column 27 is reserved for DSP/SRAM, so a 30-wide grid offers only 29 usable cell columns. All reported placements are legal: no overlaps, no off-grid cells, and all pads on the border ring.

### Convergence Across Grid Sizes

Table I summarizes the runs. Cell density is the number of cells divided by the usable core slots. The result illustrates the central tension of global placement: the *densest* grid (30x30, 86 percent) constrains the optimizer the most, so it cannot spread modules enough to shorten the longest nets and ends with the worst objective among the compact grids (1640). Roomier grids, by contrast, are not capacity-limited, and there the *search*, not the grid, limits quality.

```{=latex}
\begin{table}[t]
\centering
\caption{Convergence of NNS on the \texttt{p1} benchmark (833 modules, 902 nets, fixed seed). ``Rounds'' is the number of accepted alternating x/y optimization rounds.}
\label{tbl:convergence}
\begin{tabular}{lrrrr}
\hline
Grid & Usable slots & Cell density & Rounds & Worst \\
\hline
30x30   & 870  & 86\% & 2 & 1640 \\
30x40   & 1160 & 65\% & 2 & 1440 \\
32x32   & 992  & 76\% & 1 & 1480 \\
40x30   & 1170 & 64\% & 2 & 1480 \\
50x50   & 2450 & 31\% & 3 & 1600 \\
100x100 & 9900 & 8\%  & 2 & 2120 \\
\hline
\end{tabular}
\end{table}
```

### Congestion Evenness Versus Density

@fig:congdense and @fig:congsparse contrast the combined congestion maps of the tight 30x30 grid with the roomy 50x50 grid. On the dense grid the congestion is high and uneven because the placer has little slack to redistribute cells; on the roomy grid the demand is lower and smoother. This is exactly the regime the fairness objective targets: rather than shrinking the total demand further, it caps the peak so that no region becomes a routing bottleneck.

![Combined congestion map on the tight 30x30 grid (86 percent cell density).](figures/congestion-30x30-combined.pdf){#fig:congdense width=100%}

![Combined congestion map on the roomy 50x50 grid (31 percent cell density).](figures/congestion-50x50-combined.pdf){#fig:congsparse width=100%}

### Computational Cost

The min-max objective and the exact rational arithmetic come at a cost, but a modest one. Profiling attributed most of the runtime to the Howard cost model and to legalization, and targeted, behavior-preserving optimizations reduced the total CPU time over a 30-scenario seed-grid matrix by a factor of roughly 4.6 without changing a single placement. Table II lists the headline figures; the same optimization was subsequently ported to C++ with further speed-ups.

```{=latex}
\begin{table}[t]
\centering
\caption{Runtime of the fairness-centric placer before and after behavior-preserving optimization. Every change was validated against a bit-identical placement oracle.}
\label{tbl:speedup}
\begin{tabular}{lrl}
\hline
Optimization & Effect & Result unchanged \\
\hline
Integer floor-division in the cost model & 1.85x on hot callback & yes \\
Direct linear-assignment solver (no graph) & 2.6x per legalization & yes \\
Gating infeasible assignment calls & 7x per matching & yes \\
Whole seed-grid matrix & 4.57x total CPU & yes \\
\hline
\end{tabular}
\end{table}
```

## From Placement to Global Routing

Placement optimizes a proxy; routing decides the actual wires. To close the loop, each net of the final placement is passed to a rectilinear global router [8] that builds one tree per net, rooted at the net's driver pin, and connects each sink within an allowed wire-length budget, inserting Steiner points to share trunks and save wire. @fig:routed shows the routed version of the 50x50 placement: the straight proxy lines of @fig:placement are replaced by orthogonal routing trees, and the cut crossings of those trees are precisely what the congestion maps of the previous section count.

![Routed placement on the 50x50 grid: orthogonal routing trees replace the straight proxy connections.](figures/routed-50x50.pdf){#fig:routed width=100%}

This two-stage view reinforces the paper's thesis. The placer bounds the worst per-net wire length, the router materializes it, and the resulting congestion map reveals whether the demand is fairly distributed. When it is not, the placement objective -- not just the total wire length -- is the knob to turn.

## Relationship with Other Placement Objectives

Adopting a fairness-centric approach to global placement has implications for other important placement objectives, such as wirelength minimization, timing optimization, and power reduction. Understanding these relationships and potential trade-offs is crucial for developing effective placement methodologies.

### Interaction with Wirelength Minimization

As discussed earlier, minimizing total wirelength and minimizing local congestion are not always mutually exclusive. While a purely wirelength-driven approach can lead to congestion, a placement with a more balanced routing demand distribution might have a slightly higher total wirelength. Therefore, a fairness-centric approach might involve accepting a small increase in total wirelength in exchange for a significant reduction in peak congestion levels, ultimately leading to better routability and potentially better final routed wirelength due to fewer detours. The goal is to find a balance where the routing demand is sufficiently low overall (thanks to wirelength minimization) and also distributed reasonably evenly across the chip (thanks to the fairness objective).

### Implications for Timing-Driven Placement

Timing-driven placement aims to optimize circuit performance by minimizing critical path delays. This is often achieved by assigning weights to critical nets and encouraging the placer to shorten these nets. Incorporating fairness into timing-driven placement requires careful consideration. An aggressive focus on reducing congestion might inadvertently increase the length of critical paths, leading to timing violations. Conversely, solely focusing on timing might create or exacerbate congestion issues. Therefore, a successful approach might involve a multi-objective optimization that considers both timing criticality and congestion (or fairness in routing demand). This could involve assigning higher congestion penalties in regions containing critical nets or using timing-aware congestion estimation.

### Impact on Power-Driven Placement

Power-driven placement aims to minimize power consumption, often by reducing wirelength (to decrease dynamic power) or by strategically placing cells with different power characteristics (e.g., in multi-voltage designs). A fairer distribution of cells achieved through a fairness-centric placement could potentially benefit power consumption by avoiding highly dense regions, which might lead to increased temperature and leakage power. Furthermore, shorter routed wirelengths (due to better routability) can also contribute to lower dynamic power consumption. In multi-voltage designs, the interaction between fairness in cell distribution and the placement of cells near their respective voltage sources would need to be carefully managed.

Overall, integrating fairness into global placement requires a holistic approach that considers its interplay with other crucial design objectives. The optimal balance between fairness and other metrics might depend on the specific characteristics and requirements of the target design.

## Challenges and Future Directions

While fairness-centric global placement offers a promising direction for addressing the critical issue of routing congestion in VLSI design, several challenges remain, and further research is needed to realize its full potential.

### Computational Complexity

Directly optimizing for fairness metrics, such as minimizing the maximum congestion, can be computationally more complex than minimizing the sum of costs like total wirelength. Algorithms need to efficiently estimate congestion, identify the most congested regions, and make placement decisions that effectively reduce peak congestion without significantly degrading other objectives. Developing scalable and efficient algorithms for fairness-centric global placement, especially for very large-scale designs, is a significant challenge.

### Accurate and Efficient Congestion Estimation

The effectiveness of any congestion-driven (or fairness-centric) placement approach heavily relies on the accuracy and efficiency of the congestion estimation model used during the placement process. As noted, simpler models like bounding box routing provide a quick estimate but might lack accuracy, while more sophisticated global routing-based estimation can be more accurate but also more computationally expensive. Finding a good balance between accuracy and efficiency in congestion estimation during global placement remains an ongoing challenge.

### Integration with Mixed-Size Placement

Modern VLSI designs often include a mix of standard cells and larger blocks (macros, IP cores). Integrating fairness-centric principles into mixed-size placement adds another layer of complexity. The placement of large, fixed-size macros significantly influences the available area for standard cell placement and the overall routing landscape. Developing fairness-aware placement algorithms that effectively handle both the placement of macros and the surrounding standard cells is an important area for future research.

### Handling Multi-Layer Routing Resources

Modern ICs utilize multiple routing layers with varying characteristics. Congestion can occur on specific layers or across multiple layers. Fairness-centric placement needs to consider the availability and capacity of these multi-layer routing resources during congestion estimation and optimization. Developing sophisticated congestion models that accurately reflect the multi-layer routing environment is crucial.

### Robust Benchmarks and Evaluation Metrics

To effectively evaluate and compare different fairness-centric global placement algorithms, the availability of robust benchmark circuits with known routing challenges and well-defined evaluation metrics is essential. Metrics should go beyond just total overflow and potentially consider the distribution of congestion, the impact on routed wirelength, and the overall routability of the final placement.

### Future Research Directions

Future research in fairness-centric global placement can explore several promising directions:

* Development of novel and efficient algorithms that can directly optimize for fairness metrics like minimizing maximum congestion.
* Investigation of advanced machine learning techniques to predict congestion during early stages of placement and guide fairness-aware optimization.
* Exploration of tighter integration between global placement and early routing estimation to obtain more accurate congestion feedback for fairness optimization.
* Development of unified placement frameworks that can simultaneously address fairness, wirelength, timing, and power objectives in a balanced manner.
* Creation of new benchmark suites specifically designed to challenge and evaluate the effectiveness of congestion-driven and fairness-centric placement algorithms.
* Research into extending fairness principles to other stages of physical design, such as detailed placement and routing.

## Conclusion

The increasing complexity and density of modern VLSI circuits have elevated routing congestion to a critical concern in physical design. Traditional global placement objectives, primarily focused on minimizing total wirelength, often fail to adequately address the issue of localized congestion, leading to routability problems and performance degradation. This paper has argued for a shift towards **fairness-centric global placement**, where the goal is to achieve a more balanced distribution of routing demand across the chip by prioritizing the minimization of peak congestion levels.

The principle of **max-min fairness**, borrowed from network resource allocation, provides a compelling motivation for this approach, emphasizing the importance of ensuring a baseline level of routability across all regions of the design. While challenges remain in developing computationally efficient and accurate fairness-centric algorithms and integrating them with other placement objectives, the potential benefits in terms of improved routability, reduced design cycle times, and higher quality final layouts make this a crucial area for future research and development in VLSI physical design. By recognizing the inherent limitations of solely focusing on global minimization and embracing the concept of fairness in resource allocation, the VLSI design community can pave the way for more robust and scalable placement methodologies capable of handling the ever-increasing complexity of integrated circuits.

Beyond the principles, this paper reported a concrete realization: the open-source NNS placer, which reduces the worst-wire-length objective to a parametric minimum-cost-flow problem solved by Howard's algorithm and legalizes with minimum-weight bipartite matching. Its placements yield congestion maps in which the fairness/routability trade-off is directly visible, and behavior-preserving optimizations keep the exact min-max objective affordable. We hope that the open implementation lowers the barrier to experimenting with fairness-centric objectives on real designs.

## References {.unnumbered}

1. N. Sherwani, *Algorithms for VLSI Physical Design Automation*, 3rd ed. Springer, 1999.
2. A. B. Kahng, J. Lienig, I. L. Markov, and J. Hu, *VLSI Physical Design: From Graph Partitioning to Timing Closure*. Springer, 2011.
3. A. B. Kahng, S. Mantik, and I. L. Markov, "Min-max placement for large-scale timing optimization," in *Proc. Int. Symp. Physical Design (ISPD)*, 2003.
4. R. A. Howard, *Dynamic Programming and Markov Processes*. MIT Press, 1960.
5. C. M. Fiduccia and R. M. Mattheyses, "A linear-time heuristic for improving network partitions," in *Proc. Design Automation Conf. (DAC)*, 1982.
6. A. Dasdan, "Experimental analysis of the fastest optimum cycle ratio algorithms," *ACM Trans. Design Automation of Electronic Systems*, vol. 9, no. 4, 2004.
7. J. Cong, A. B. Kahng, G. Robins, M. Sarrafzadeh, and C. K. Wong, "Provably good performance-driven global routing," *IEEE Trans. Computer-Aided Design*, vol. 11, no. 6, 1992.
8. W.-S. Luk, *digraphx*, *netlistx*, and *physdes* software libraries. [Online]. Available: https://github.com/luk036
9. W.-S. Luk, *nnsplace: an affordable fairness-centric placement library*. [Online]. Available: https://github.com/luk036/nnsplace
